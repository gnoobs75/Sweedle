"""Generation API router."""

import logging
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.queue import JobPriority, get_queue
from src.core.websocket_manager import get_websocket_manager
from src.database import get_session
from src.generation.models import GenerationType, JobStatus
from src.generation.schemas import (
    GenerationMode,
    GenerationParameters,
    GenerationResponse,
    JobStatusResponse,
    OutputFormat,
    QueueStatusResponse,
)
from src.generation.service import GenerationService
from src.generation.image_analyzer import analyze_image
from PIL import Image
import io

logger = logging.getLogger(__name__)

router = APIRouter()


def get_service(db: AsyncSession = Depends(get_session)) -> GenerationService:
    """Dependency to get generation service."""
    return GenerationService(db)


@router.post("/image-to-3d", response_model=GenerationResponse)
async def generate_from_image(
    request: Request,
    file: UploadFile = File(..., description="Source image file (PNG, JPG, WEBP)"),
    name: Optional[str] = Form(None, description="Asset name"),
    inference_steps: int = Form(30, ge=5, le=100),
    guidance_scale: float = Form(5.5, ge=1.0, le=15.0),
    octree_resolution: int = Form(256),
    seed: Optional[int] = Form(None),
    generate_texture: bool = Form(True),
    face_count: Optional[int] = Form(None),
    output_format: str = Form("glb"),
    mode: str = Form("standard"),
    priority: str = Form("normal", description="Job priority: low, normal, high"),
    project_id: Optional[str] = Form(None),
    tags: Optional[str] = Form(None, description="Comma-separated tags"),
    service: GenerationService = Depends(get_service),
):
    """Submit an image for 3D generation.

    The job is added to the queue and processed by the background worker.
    Use the WebSocket endpoint (/ws/progress) or poll the job status endpoint
    to track progress.

    Returns a job ID that can be used to track progress.
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "File must be an image (PNG, JPG, WEBP)")

    # Save uploaded file
    upload_path = await service.save_upload(file)

    # Parse parameters
    params = GenerationParameters(
        inference_steps=inference_steps,
        guidance_scale=guidance_scale,
        octree_resolution=octree_resolution,
        seed=seed,
        generate_texture=generate_texture,
        face_count=face_count,
        output_format=OutputFormat(output_format),
        mode=GenerationMode(mode),
    )

    # Create asset record
    asset_name = name or (Path(file.filename).stem if file.filename else "Untitled")
    asset = await service.create_asset(
        name=asset_name,
        source_type=GenerationType.IMAGE_TO_3D,
        source_image_path=upload_path,
        parameters=params.model_dump(),
    )

    # Create job in database
    job = await service.create_job(
        asset_id=asset.id,
        job_type="image_to_3d",
        payload={
            "image_path": str(upload_path),
            "asset_id": asset.id,
            "name": asset_name,
            "parameters": params.model_dump(),
            "project_id": project_id,
            "tags": [t.strip() for t in tags.split(",")] if tags else [],
        },
    )

    # Get queue and WebSocket manager
    queue = get_queue()
    ws_manager = get_websocket_manager()

    # Parse priority
    priority_map = {
        "low": JobPriority.LOW,
        "normal": JobPriority.NORMAL,
        "high": JobPriority.HIGH,
    }
    job_priority = priority_map.get(priority.lower(), JobPriority.NORMAL)

    # Add to queue
    await queue.enqueue(
        job_id=job.id,
        job_type="image_to_3d",
        payload={
            "image_path": str(upload_path),
            "asset_id": asset.id,
            "name": asset_name,
            "parameters": params.model_dump(),
            "project_id": project_id,
            "tags": [t.strip() for t in tags.split(",")] if tags else [],
        },
        priority=job_priority,
    )

    # Get queue position
    queue_status = queue.get_status()

    # Send WebSocket notification
    await ws_manager.send_job_created(
        job_id=job.id,
        asset_id=asset.id,
        job_type="image_to_3d",
        position=queue_status["queue_size"],
    )

    return GenerationResponse(
        job_id=job.id,
        asset_id=asset.id,
        status=JobStatus.PENDING,
        message="Job queued for processing",
        queue_position=queue_status["queue_size"],
    )


@router.post("/text-to-3d", response_model=GenerationResponse)
async def generate_from_text(
    prompt: str = Form(..., min_length=3, max_length=500),
    name: Optional[str] = Form(None),
    inference_steps: int = Form(30, ge=5, le=100),
    guidance_scale: float = Form(5.5, ge=1.0, le=15.0),
    octree_resolution: int = Form(256),
    seed: Optional[int] = Form(None),
    generate_texture: bool = Form(True),
    face_count: Optional[int] = Form(None),
    output_format: str = Form("glb"),
    mode: str = Form("standard"),
    priority: str = Form("normal"),
    project_id: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    service: GenerationService = Depends(get_service),
):
    """Submit a text prompt for 3D generation.

    Note: Text-to-3D requires a text-to-image step first.
    This endpoint is a placeholder for future implementation.
    """
    raise HTTPException(
        501,
        "Text-to-3D is not yet implemented. Please use image-to-3D with a generated image."
    )


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    service: GenerationService = Depends(get_service),
):
    """Get the status of a generation job."""
    # First check in-memory queue
    queue = get_queue()
    queue_job = queue.get_job(job_id)

    if queue_job:
        return JobStatusResponse(
            job_id=queue_job.id,
            asset_id=queue_job.payload.get("asset_id"),
            status=queue_job.status,
            progress=queue_job.progress,
            stage=queue_job.stage,
            message=queue_job.stage,
            error=queue_job.error,
            created_at=queue_job.created_at,
            started_at=queue_job.started_at,
            completed_at=queue_job.completed_at,
        )

    # Fall back to database
    job = await service.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    return JobStatusResponse(
        job_id=job.id,
        asset_id=job.asset_id,
        status=job.status,
        progress=job.progress,
        stage=job.stage or "unknown",
        message=job.stage,
        error=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


@router.delete("/jobs/{job_id}")
async def cancel_job(
    job_id: str,
    service: GenerationService = Depends(get_service),
):
    """Cancel a pending job.

    Note: Jobs that are already processing cannot be cancelled.
    """
    queue = get_queue()

    # Try to cancel in queue
    if await queue.cancel(job_id):
        await service.update_job_status(job_id, JobStatus.CANCELLED)
        return {"message": "Job cancelled", "job_id": job_id}

    # Check if job exists
    job = await service.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    if job.status != JobStatus.PENDING:
        raise HTTPException(400, f"Cannot cancel job with status: {job.status.value}")

    await service.update_job_status(job_id, JobStatus.CANCELLED)
    return {"message": "Job cancelled", "job_id": job_id}


@router.get("/queue/status", response_model=QueueStatusResponse)
async def get_queue_status():
    """Get current queue status."""
    queue = get_queue()
    status = queue.get_status()

    return QueueStatusResponse(
        queue_size=status["queue_size"],
        current_job_id=status["current_job_id"],
        pending_count=status["pending_count"],
        processing_count=status["processing_count"],
        completed_count=status["completed_count"],
    )


@router.get("/queue/jobs")
async def get_queue_jobs(
    limit: int = 20,
    include_completed: bool = False,
):
    """Get jobs in the queue.

    Args:
        limit: Maximum number of jobs to return
        include_completed: Include completed/failed jobs
    """
    queue = get_queue()

    if include_completed:
        jobs = queue.get_recent_jobs(limit)
    else:
        jobs = queue.get_pending_jobs()[:limit]

    return {
        "jobs": [
            {
                "job_id": job.id,
                "job_type": job.job_type,
                "status": job.status.value,
                "progress": job.progress,
                "stage": job.stage,
                "priority": job.priority.name,
                "created_at": job.created_at.isoformat(),
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            }
            for job in jobs
        ],
        "total": len(jobs),
    }


@router.post("/analyze-image")
async def analyze_image_quality(
    file: UploadFile = File(..., description="Image to analyze for 3D generation suitability"),
):
    """
    Analyze an image for 3D generation suitability.

    Returns quality scores and feedback on:
    - Resolution (optimal: 1024x1024)
    - Aspect ratio (optimal: square)
    - Background (optimal: transparent)
    - Subject centering
    - Image sharpness
    - Subject coverage
    - Contrast/lighting

    Use this before submitting for generation to get feedback on image quality.
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "File must be an image (PNG, JPG, WEBP)")

    try:
        # Read image
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))

        # Analyze
        result = analyze_image(image)

        return {
            "success": True,
            "analysis": result.to_dict(),
        }

    except Exception as e:
        logger.exception(f"Image analysis failed: {e}")
        raise HTTPException(500, f"Image analysis failed: {str(e)}")


@router.post("/add-texture/{asset_id}", response_model=GenerationResponse)
async def add_texture_to_asset(
    request: Request,
    asset_id: str,
    priority: str = Form("normal", description="Job priority: low, normal, high"),
    service: GenerationService = Depends(get_service),
):
    """
    Add texture to an existing untextured 3D asset.

    This is for assets generated with texture disabled (shape-only mode).
    The original source image is used for texture generation.

    Flow:
    1. Shape-only generation (fast, ~30s)
    2. Preview the mesh
    3. If good, call this endpoint to add texture (~90s)
    """
    # Get the asset
    asset = await service.get_asset(asset_id)
    if not asset:
        raise HTTPException(404, "Asset not found")

    # Check if asset already has texture
    if asset.has_texture:
        raise HTTPException(400, "Asset already has texture")

    # Check if we have the source image
    if not asset.source_image_path:
        raise HTTPException(400, "No source image available for texture generation")

    # Create job for texture generation
    job = await service.create_job(
        asset_id=asset.id,
        job_type="add_texture",
        payload={
            "asset_id": asset.id,
            "mesh_path": asset.file_path,
            "source_image_path": asset.source_image_path,
            "name": asset.name,
        },
    )

    # Get queue and WebSocket manager
    queue = get_queue()
    ws_manager = get_websocket_manager()

    # Parse priority
    priority_map = {
        "low": JobPriority.LOW,
        "normal": JobPriority.NORMAL,
        "high": JobPriority.HIGH,
    }
    job_priority = priority_map.get(priority.lower(), JobPriority.NORMAL)

    # Add to queue
    await queue.enqueue(
        job_id=job.id,
        job_type="add_texture",
        payload={
            "asset_id": asset.id,
            "mesh_path": asset.file_path,
            "source_image_path": asset.source_image_path,
            "name": asset.name,
        },
        priority=job_priority,
    )

    # Get queue position
    queue_status = queue.get_status()

    # Send WebSocket notification
    await ws_manager.send_job_created(
        job_id=job.id,
        asset_id=asset.id,
        job_type="add_texture",
        position=queue_status["queue_size"],
    )

    return GenerationResponse(
        job_id=job.id,
        asset_id=asset.id,
        status=JobStatus.PENDING,
        message="Texture generation queued",
        queue_position=queue_status["queue_size"],
    )
