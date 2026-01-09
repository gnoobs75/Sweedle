"""
Rigging API router.

Provides endpoints for auto-rigging, skeleton management, and rigging job control.
"""

import logging
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..config import settings
from ..database import get_session
from ..core.queue import get_queue, JobPriority as QueuePriority
from ..core.websocket_manager import get_websocket_manager
from ..generation.models import Asset, GenerationJob

from .schemas import (
    CharacterType,
    RiggingProcessor,
    JobPriority,
    AutoRigResponse,
    RiggingJobStatus,
    RiggingStatus,
    DetectTypeRequest,
    DetectTypeResponse,
    SkeletonResponse,
    TemplateListResponse,
    SkeletonTemplateInfo,
)
from .service import get_rigging_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rigging", tags=["rigging"])


@router.post("/auto-rig", response_model=AutoRigResponse)
async def auto_rig_asset(
    asset_id: str = Form(...),
    character_type: CharacterType = Form(default=CharacterType.AUTO),
    processor: RiggingProcessor = Form(default=RiggingProcessor.AUTO),
    priority: JobPriority = Form(default=JobPriority.NORMAL),
    db: AsyncSession = Depends(get_session),
):
    """
    Submit an asset for auto-rigging.

    Creates a rigging job that will be processed by the background worker.
    Progress updates are sent via WebSocket.
    """
    # Verify asset exists
    result = await db.execute(select(Asset).where(Asset.id == asset_id))
    asset = result.scalar_one_or_none()

    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset not found: {asset_id}",
        )

    if asset.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Asset is not ready for rigging (status: {asset.status})",
        )

    if asset.is_rigged:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Asset is already rigged",
        )

    # Check if there's an existing rigging job for this asset
    existing_job = await db.execute(
        select(GenerationJob).where(
            GenerationJob.asset_id == asset_id,
            GenerationJob.job_type == "rig_asset",
            GenerationJob.status.in_(["pending", "processing"]),
        )
    )
    if existing_job.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A rigging job is already in progress for this asset",
        )

    # Create job
    job_id = str(uuid4())

    job = GenerationJob(
        id=job_id,
        asset_id=asset_id,
        job_type="rig_asset",
        priority={"low": 2, "normal": 1, "high": 0}.get(priority.value, 1),
        status="pending",
        progress=0.0,
        stage="Queued",
        payload={
            "asset_id": asset_id,
            "character_type": character_type.value,
            "processor": processor.value,
            "mesh_path": asset.file_path,
        },
    )
    db.add(job)
    await db.commit()

    # Add to queue
    queue = get_queue()
    queue_priority = {
        "low": QueuePriority.LOW,
        "normal": QueuePriority.NORMAL,
        "high": QueuePriority.HIGH,
    }.get(priority.value, QueuePriority.NORMAL)

    await queue.enqueue(
        job_id=job_id,
        job_type="rig_asset",
        payload=job.payload,
        priority=queue_priority,
    )

    # Broadcast job created
    ws_manager = get_websocket_manager()
    await ws_manager.send_job_created(
        job_id=job_id,
        asset_id=asset_id,
        job_type="rig_asset",
        position=await queue.get_position(job_id) or 0,
    )

    logger.info(f"Created rigging job {job_id} for asset {asset_id}")

    return AutoRigResponse(
        job_id=job_id,
        asset_id=asset_id,
        status="pending",
        message="Rigging job queued successfully",
        queue_position=await queue.get_position(job_id),
    )


@router.get("/jobs/{job_id}", response_model=RiggingJobStatus)
async def get_rigging_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Get the status of a rigging job."""
    # Check in-memory queue first
    queue = get_queue()
    queue_job = await queue.get_job(job_id)

    if queue_job:
        return RiggingJobStatus(
            job_id=job_id,
            asset_id=queue_job.payload.get("asset_id", ""),
            status=RiggingStatus(queue_job.status.value),
            progress=queue_job.progress,
            stage=queue_job.stage,
            detected_type=CharacterType(queue_job.payload.get("detected_type")) if queue_job.payload.get("detected_type") else None,
            error=queue_job.error,
            created_at=queue_job.created_at,
            started_at=queue_job.started_at,
            completed_at=queue_job.completed_at,
        )

    # Fall back to database
    result = await db.execute(
        select(GenerationJob).where(GenerationJob.id == job_id)
    )
    job = result.scalar_one_or_none()

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {job_id}",
        )

    return RiggingJobStatus(
        job_id=job.id,
        asset_id=job.asset_id,
        status=RiggingStatus(job.status),
        progress=job.progress or 0.0,
        stage=job.stage or "",
        detected_type=CharacterType(job.payload.get("detected_type")) if job.payload and job.payload.get("detected_type") else None,
        error=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


@router.delete("/jobs/{job_id}")
async def cancel_rigging_job(
    job_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Cancel a pending rigging job."""
    queue = get_queue()

    # Try to cancel in queue
    cancelled = await queue.cancel(job_id)

    if cancelled:
        # Update database
        result = await db.execute(
            select(GenerationJob).where(GenerationJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        if job:
            job.status = "cancelled"
            await db.commit()

        return {"message": "Job cancelled", "job_id": job_id}

    # Check if job exists in database
    result = await db.execute(
        select(GenerationJob).where(GenerationJob.id == job_id)
    )
    job = result.scalar_one_or_none()

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {job_id}",
        )

    if job.status == "processing":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel job that is already processing",
        )

    if job.status in ["completed", "failed", "cancelled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is already {job.status}",
        )

    return {"message": "Job cancelled", "job_id": job_id}


@router.get("/skeleton/{asset_id}", response_model=SkeletonResponse)
async def get_skeleton(
    asset_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Get skeleton data for a rigged asset."""
    result = await db.execute(select(Asset).where(Asset.id == asset_id))
    asset = result.scalar_one_or_none()

    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset not found: {asset_id}",
        )

    if not asset.is_rigged:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset is not rigged",
        )

    if not asset.rigging_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No skeleton data available",
        )

    from .schemas import SkeletonData

    skeleton = SkeletonData(**asset.rigging_data)

    return SkeletonResponse(
        asset_id=asset_id,
        skeleton=skeleton,
        rigged_mesh_path=asset.rigged_mesh_path or asset.file_path,
        processor_used=RiggingProcessor(asset.rigging_processor) if asset.rigging_processor else RiggingProcessor.AUTO,
        created_at=asset.updated_at,
    )


@router.post("/detect-type", response_model=DetectTypeResponse)
async def detect_character_type(
    request: DetectTypeRequest,
    db: AsyncSession = Depends(get_session),
):
    """Detect the character type of an asset."""
    result = await db.execute(select(Asset).where(Asset.id == request.asset_id))
    asset = result.scalar_one_or_none()

    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset not found: {request.asset_id}",
        )

    if not asset.file_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Asset has no mesh file",
        )

    mesh_path = Path(settings.STORAGE_ROOT) / asset.file_path
    if not mesh_path.exists():
        # Try as absolute path
        mesh_path = Path(asset.file_path)

    if not mesh_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mesh file not found",
        )

    service = get_rigging_service(db)
    detected_type, confidence = await service.detect_character_type(mesh_path)

    return DetectTypeResponse(
        asset_id=request.asset_id,
        detected_type=detected_type,
        confidence=confidence,
    )


@router.get("/templates", response_model=TemplateListResponse)
async def list_templates():
    """List available skeleton templates."""
    service = get_rigging_service()
    templates = service.get_templates()

    return TemplateListResponse(templates=templates)
