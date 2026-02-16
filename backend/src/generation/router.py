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
    TextToImageResponse,
    StylePresetResponse,
    MultiViewAngle,
    MultiViewGenerationResponse,
)
from src.generation.service import GenerationService
from src.generation.image_analyzer import analyze_image
from src.inference.text_to_image import SDXLPipeline, TextToImageConfig, get_sdxl_pipeline
from src.inference.style_presets import get_all_presets, get_preset
from src.config import settings
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


@router.get("/text-to-image/presets", response_model=list[StylePresetResponse])
async def get_style_presets():
    """Get available style presets for text-to-image generation."""
    if not settings.ENABLE_TEXT_TO_IMAGE:
        raise HTTPException(503, "Text-to-image feature is disabled")

    return get_all_presets()


@router.post("/text-to-image", response_model=TextToImageResponse)
async def generate_image_from_text(
    request: Request,
    prompt: str = Form(..., min_length=3, max_length=500, description="Text description"),
    style_preset: str = Form("game_asset", description="Style preset ID"),
    negative_prompt: Optional[str] = Form(None, description="Things to avoid"),
    seed: Optional[int] = Form(None, description="Random seed"),
    num_inference_steps: int = Form(30, ge=10, le=50, description="Diffusion steps"),
    guidance_scale: float = Form(7.5, ge=1.0, le=20.0, description="Guidance scale"),
    service: GenerationService = Depends(get_service),
):
    """Generate an image from a text prompt using Stable Diffusion XL.

    The generated image can then be used with the image-to-3D endpoint.

    This endpoint:
    1. Loads SDXL if not already loaded (~7GB VRAM)
    2. Generates image from prompt with style preset
    3. Saves image and returns URL
    4. Unloads SDXL from GPU to free VRAM for Hunyuan3D

    Style presets optimize prompts for 3D-friendly images:
    - game_asset: General 3D asset with clean background
    - character: Full-body character for rigging
    - prop: Game prop/inventory item
    - creature: Fantasy creature
    - vehicle: Vehicle/transportation
    - weapon: Weapon/tool
    """
    if not settings.ENABLE_TEXT_TO_IMAGE:
        raise HTTPException(503, "Text-to-image feature is disabled")

    # Generate unique ID for this image
    image_id = str(uuid.uuid4())

    # Create output path
    output_dir = settings.UPLOAD_DIR / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{image_id}.png"

    # Get WebSocket manager for progress updates
    ws_manager = get_websocket_manager()

    # Create config
    config = TextToImageConfig(
        prompt=prompt,
        style_preset=style_preset,
        negative_prompt=negative_prompt,
        seed=seed,
        num_inference_steps=num_inference_steps,
        guidance_scale=guidance_scale,
        width=settings.SDXL_DEFAULT_WIDTH,
        height=settings.SDXL_DEFAULT_HEIGHT,
    )

    # Progress callback
    async def progress_callback(progress: float, stage: str):
        await ws_manager.broadcast({
            "type": "text_to_image_progress",
            "image_id": image_id,
            "progress": progress,
            "stage": stage,
        })

    # Synchronous wrapper for async callback
    import asyncio
    loop = asyncio.get_running_loop()

    def sync_progress(progress: float, stage: str):
        asyncio.run_coroutine_threadsafe(progress_callback(progress, stage), loop)

    try:
        # Get pipeline and generate
        pipeline = get_sdxl_pipeline()
        result = await pipeline.generate_and_unload(
            config=config,
            output_path=output_path,
            progress_callback=sync_progress,
        )

        if not result.success:
            raise HTTPException(500, f"Image generation failed: {result.error}")

        # Build image URL (served via /storage mount)
        image_url = f"/storage/uploads/generated/{image_id}.png"

        return TextToImageResponse(
            success=True,
            image_id=image_id,
            image_url=image_url,
            seed_used=result.seed_used,
            prompt_used=result.prompt_used,
            generation_time=result.generation_time,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Text-to-image generation failed: {e}")
        raise HTTPException(500, f"Image generation failed: {str(e)}")


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


@router.post("/multi-view-to-3d", response_model=MultiViewGenerationResponse)
async def generate_from_multi_view(
    request: Request,
    files: list[UploadFile] = File(..., description="Multiple view images (2-6 images)"),
    angles: str = Form(..., description="Comma-separated view angles (front,back,left,right,etc)"),
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
    """Submit multiple view images for enhanced 3D generation.

    Multi-view input provides more information about the object, resulting in:
    - Better geometry accuracy
    - More consistent textures
    - Fewer artifacts on unseen sides

    Recommended views:
    - Minimum: front + back (2 views)
    - Good: front + back + left + right (4 views)
    - Best: front + back + left + right + top + bottom (6 views)

    Each image should show the same object from its labeled angle.
    Images should have consistent lighting and a clean background.
    """
    # Validate file count
    if len(files) < 2:
        raise HTTPException(400, "Multi-view requires at least 2 images")
    if len(files) > 6:
        raise HTTPException(400, "Multi-view supports maximum 6 images")

    # Parse angles
    angle_list = [a.strip().lower() for a in angles.split(",")]
    if len(angle_list) != len(files):
        raise HTTPException(400, f"Number of angles ({len(angle_list)}) must match number of files ({len(files)})")

    # Validate angles
    valid_angles = {a.value for a in MultiViewAngle}
    for angle in angle_list:
        if angle not in valid_angles:
            raise HTTPException(400, f"Invalid angle: {angle}. Valid angles: {', '.join(valid_angles)}")

    # Validate file types
    for file in files:
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(400, f"File {file.filename} must be an image (PNG, JPG, WEBP)")

    # Save all uploaded files
    upload_paths = []
    view_data = []
    for file, angle in zip(files, angle_list):
        upload_path = await service.save_upload(file)
        upload_paths.append(str(upload_path))
        view_data.append({
            "path": str(upload_path),
            "angle": angle,
            "weight": 1.0,
        })

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
    asset_name = name or "Multi-View Asset"
    asset = await service.create_asset(
        name=asset_name,
        source_type=GenerationType.IMAGE_TO_3D,
        source_image_path=upload_paths[0],  # Primary image (usually front)
        parameters={
            **params.model_dump(),
            "multi_view": True,
            "view_count": len(files),
            "views": view_data,
        },
    )

    # Create job in database
    job = await service.create_job(
        asset_id=asset.id,
        job_type="multi_view_to_3d",
        payload={
            "views": view_data,
            "primary_image_path": upload_paths[0],
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
        job_type="multi_view_to_3d",
        payload={
            "views": view_data,
            "primary_image_path": upload_paths[0],
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
        job_type="multi_view_to_3d",
        position=queue_status["queue_size"],
    )

    logger.info(f"Multi-view generation queued: {len(files)} views for asset {asset.id}")

    return MultiViewGenerationResponse(
        job_id=job.id,
        asset_id=asset.id,
        status="pending",
        message=f"Multi-view generation queued with {len(files)} views",
        view_count=len(files),
        queue_position=queue_status["queue_size"],
    )
