"""Pydantic schemas for workflow management."""

from pydantic import BaseModel
from typing import Optional, Literal


WorkflowStageType = Literal[
    "uploaded",
    "mesh_generated",
    "mesh_approved",
    "textured",
    "texture_approved",
    "rigged",
    "exported"
]


class WorkflowStatusResponse(BaseModel):
    """Response for workflow status."""
    asset_id: str
    workflow_stage: WorkflowStageType
    has_mesh: bool
    has_texture: bool
    is_rigged: bool
    mesh_path: Optional[str] = None
    textured_path: Optional[str] = None
    rigged_mesh_path: Optional[str] = None


class AdvanceStageRequest(BaseModel):
    """Request to advance to next workflow stage."""
    to_stage: WorkflowStageType


class AdvanceStageResponse(BaseModel):
    """Response after advancing stage."""
    success: bool
    message: str
    asset_id: str
    new_stage: WorkflowStageType


class ApproveStageResponse(BaseModel):
    """Response after approving current stage."""
    success: bool
    message: str
    asset_id: str
    approved_stage: WorkflowStageType
    next_stage: Optional[WorkflowStageType] = None


class SkipToExportResponse(BaseModel):
    """Response after skipping to export."""
    success: bool
    message: str
    asset_id: str
    skipped_stages: list[WorkflowStageType]


class WorkflowErrorResponse(BaseModel):
    """Error response."""
    success: bool = False
    error: str
    asset_id: Optional[str] = None
