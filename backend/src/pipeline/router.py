"""Pipeline management API endpoints."""

import logging
from fastapi import APIRouter, HTTPException

from .schemas import (
    PipelineStatusResponse,
    PrepareStageRequest,
    PrepareStageResponse,
    UnloadResponse,
)
from .service import get_pipeline_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


@router.get("/status", response_model=PipelineStatusResponse)
async def get_pipeline_status():
    """Get current pipeline status and VRAM usage."""
    service = get_pipeline_service()
    status = service.get_status()
    return PipelineStatusResponse(**status)


@router.post("/prepare/{stage}", response_model=PrepareStageResponse)
async def prepare_for_stage(stage: str):
    """Prepare VRAM for a specific workflow stage.

    This will load/unload pipelines as needed to ensure the target
    stage can run without VRAM issues.

    Stages:
    - mesh: Load shape pipeline (~10GB)
    - texture: Unload shape, prepare texture pipeline (~18GB)
    - rigging: Unload all, minimal VRAM needed
    - export: Unload all
    """
    valid_stages = ["mesh", "texture", "rigging", "export"]
    if stage not in valid_stages:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid stage. Must be one of: {valid_stages}"
        )

    service = get_pipeline_service()
    result = await service.prepare_for_stage(stage)

    return PrepareStageResponse(**result)


@router.post("/unload", response_model=UnloadResponse)
async def unload_all_pipelines():
    """Unload all pipelines to free VRAM.

    Use this before switching to a different heavy operation
    or when VRAM is running low.
    """
    service = get_pipeline_service()
    result = await service.unload_all()

    return UnloadResponse(**result)
