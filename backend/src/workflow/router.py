"""Workflow management API endpoints."""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from .schemas import (
    WorkflowStatusResponse,
    AdvanceStageRequest,
    AdvanceStageResponse,
    ApproveStageResponse,
    SkipToExportResponse,
)
from .service import get_workflow_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workflow", tags=["workflow"])


@router.get("/{asset_id}/status", response_model=WorkflowStatusResponse)
async def get_workflow_status(
    asset_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Get the current workflow status for an asset."""
    service = get_workflow_service(db)
    result = await service.get_workflow_status(asset_id)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return WorkflowStatusResponse(**result)


@router.post("/{asset_id}/advance", response_model=AdvanceStageResponse)
async def advance_workflow_stage(
    asset_id: str,
    request: AdvanceStageRequest,
    db: AsyncSession = Depends(get_session),
):
    """Advance an asset to a specific workflow stage.

    Use this when you need to set a specific stage, such as after
    completing a generation step.
    """
    service = get_workflow_service(db)
    result = await service.advance_stage(asset_id, request.to_stage)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed"))

    return AdvanceStageResponse(**result)


@router.post("/{asset_id}/approve", response_model=ApproveStageResponse)
async def approve_current_stage(
    asset_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Approve the current workflow stage and advance to the next.

    This is called when the user reviews and approves the result
    of the current stage (e.g., approving the generated mesh).
    """
    service = get_workflow_service(db)
    result = await service.approve_stage(asset_id)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed"))

    return ApproveStageResponse(**result)


@router.post("/{asset_id}/skip-to-export", response_model=SkipToExportResponse)
async def skip_to_export(
    asset_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Skip remaining workflow stages and go directly to export.

    Use this when the user wants to export the asset in its current
    state without completing remaining stages (e.g., export without
    texturing or rigging).
    """
    service = get_workflow_service(db)
    result = await service.skip_to_export(asset_id)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed"))

    return SkipToExportResponse(**result)
