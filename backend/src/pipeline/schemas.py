"""Pydantic schemas for pipeline management."""

from pydantic import BaseModel
from typing import Optional


class PipelineStatusResponse(BaseModel):
    """Response for pipeline status endpoint."""
    shape_loaded: bool
    texture_loaded: bool
    vram_allocated_gb: float
    vram_free_gb: float
    vram_total_gb: float
    ready_for_stage: str  # Which workflow stage we're ready for


class PrepareStageRequest(BaseModel):
    """Request to prepare for a specific workflow stage."""
    stage: str  # mesh, texture, rigging, export


class PrepareStageResponse(BaseModel):
    """Response after preparing for a stage."""
    success: bool
    message: str
    freed_gb: Optional[float] = None
    loaded_pipeline: Optional[str] = None


class UnloadResponse(BaseModel):
    """Response after unloading pipelines."""
    success: bool
    message: str
    freed_gb: float
