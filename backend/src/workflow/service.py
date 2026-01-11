"""Workflow management service."""

import logging
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.generation.models import Asset, WorkflowStage

logger = logging.getLogger(__name__)

# Stage progression order
STAGE_ORDER = [
    WorkflowStage.UPLOADED,
    WorkflowStage.MESH_GENERATED,
    WorkflowStage.MESH_APPROVED,
    WorkflowStage.TEXTURED,
    WorkflowStage.TEXTURE_APPROVED,
    WorkflowStage.RIGGED,
    WorkflowStage.EXPORTED,
]


def get_next_stage(current: WorkflowStage) -> Optional[WorkflowStage]:
    """Get the next stage in the workflow."""
    try:
        idx = STAGE_ORDER.index(current)
        if idx < len(STAGE_ORDER) - 1:
            return STAGE_ORDER[idx + 1]
    except ValueError:
        pass
    return None


def get_prev_stage(current: WorkflowStage) -> Optional[WorkflowStage]:
    """Get the previous stage in the workflow."""
    try:
        idx = STAGE_ORDER.index(current)
        if idx > 0:
            return STAGE_ORDER[idx - 1]
    except ValueError:
        pass
    return None


class WorkflowService:
    """Service for managing asset workflow progression."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_asset(self, asset_id: str) -> Optional[Asset]:
        """Get an asset by ID."""
        result = await self.db.execute(
            select(Asset).where(Asset.id == asset_id)
        )
        return result.scalar_one_or_none()

    async def get_workflow_status(self, asset_id: str) -> dict:
        """Get the current workflow status for an asset."""
        asset = await self.get_asset(asset_id)
        if not asset:
            return {"error": f"Asset {asset_id} not found"}

        return {
            "asset_id": asset_id,
            "workflow_stage": asset.workflow_stage or WorkflowStage.UPLOADED.value,
            "has_mesh": bool(asset.file_path or asset.mesh_path),
            "has_texture": asset.has_texture,
            "is_rigged": asset.is_rigged,
            "mesh_path": asset.mesh_path,
            "textured_path": asset.textured_path,
            "rigged_mesh_path": asset.rigged_mesh_path,
        }

    async def advance_stage(self, asset_id: str, to_stage: str) -> dict:
        """Advance an asset to a specific workflow stage."""
        asset = await self.get_asset(asset_id)
        if not asset:
            return {"success": False, "error": f"Asset {asset_id} not found"}

        try:
            target_stage = WorkflowStage(to_stage)
        except ValueError:
            return {"success": False, "error": f"Invalid stage: {to_stage}"}

        # Update the workflow stage
        asset.workflow_stage = target_stage.value
        await self.db.commit()

        # Broadcast update via WebSocket
        from src.core.websocket_manager import get_websocket_manager
        ws = get_websocket_manager()
        await ws.send_workflow_update(
            asset_id=asset_id,
            stage=target_stage.value,
            status="advanced",
            message_text=f"Advanced to {target_stage.value}",
        )

        logger.info(f"Asset {asset_id} advanced to stage {target_stage.value}")

        return {
            "success": True,
            "message": f"Advanced to {target_stage.value}",
            "asset_id": asset_id,
            "new_stage": target_stage.value,
        }

    async def approve_stage(self, asset_id: str) -> dict:
        """Approve the current stage and advance to next."""
        asset = await self.get_asset(asset_id)
        if not asset:
            return {"success": False, "error": f"Asset {asset_id} not found"}

        current_stage = WorkflowStage(asset.workflow_stage or WorkflowStage.UPLOADED.value)

        # Determine next stage based on current
        next_stage = None
        if current_stage == WorkflowStage.UPLOADED:
            # After upload, should have generated mesh
            next_stage = WorkflowStage.MESH_GENERATED
        elif current_stage == WorkflowStage.MESH_GENERATED:
            next_stage = WorkflowStage.MESH_APPROVED
        elif current_stage == WorkflowStage.MESH_APPROVED:
            next_stage = WorkflowStage.TEXTURED
        elif current_stage == WorkflowStage.TEXTURED:
            next_stage = WorkflowStage.TEXTURE_APPROVED
        elif current_stage == WorkflowStage.TEXTURE_APPROVED:
            next_stage = WorkflowStage.RIGGED
        elif current_stage == WorkflowStage.RIGGED:
            next_stage = WorkflowStage.EXPORTED
        elif current_stage == WorkflowStage.EXPORTED:
            # Already at final stage
            return {
                "success": True,
                "message": "Already at final stage",
                "asset_id": asset_id,
                "approved_stage": current_stage.value,
                "next_stage": None,
            }

        if next_stage:
            asset.workflow_stage = next_stage.value
            await self.db.commit()

            # Broadcast update
            from src.core.websocket_manager import get_websocket_manager
            ws = get_websocket_manager()
            await ws.send_workflow_update(
                asset_id=asset_id,
                stage=next_stage.value,
                status="approved",
                message_text=f"Stage {current_stage.value} approved, now at {next_stage.value}",
            )

            logger.info(f"Asset {asset_id} stage {current_stage.value} approved, now at {next_stage.value}")

        return {
            "success": True,
            "message": f"Stage {current_stage.value} approved",
            "asset_id": asset_id,
            "approved_stage": current_stage.value,
            "next_stage": next_stage.value if next_stage else None,
        }

    async def skip_to_export(self, asset_id: str) -> dict:
        """Skip remaining stages and go directly to export."""
        asset = await self.get_asset(asset_id)
        if not asset:
            return {"success": False, "error": f"Asset {asset_id} not found"}

        current_stage = WorkflowStage(asset.workflow_stage or WorkflowStage.UPLOADED.value)
        current_idx = STAGE_ORDER.index(current_stage)
        export_idx = STAGE_ORDER.index(WorkflowStage.EXPORTED)

        # Collect skipped stages
        skipped = []
        for i in range(current_idx + 1, export_idx):
            skipped.append(STAGE_ORDER[i].value)

        # Jump to exported
        asset.workflow_stage = WorkflowStage.EXPORTED.value
        await self.db.commit()

        # Broadcast update
        from src.core.websocket_manager import get_websocket_manager
        ws = get_websocket_manager()
        await ws.send_workflow_update(
            asset_id=asset_id,
            stage=WorkflowStage.EXPORTED.value,
            status="skipped_to_export",
            message_text=f"Skipped stages: {', '.join(skipped)}",
        )

        logger.info(f"Asset {asset_id} skipped to export, skipped stages: {skipped}")

        return {
            "success": True,
            "message": "Skipped to export stage",
            "asset_id": asset_id,
            "skipped_stages": skipped,
        }

    async def set_stage(self, asset_id: str, stage: WorkflowStage) -> bool:
        """Set an asset's workflow stage directly."""
        asset = await self.get_asset(asset_id)
        if not asset:
            return False

        asset.workflow_stage = stage.value
        await self.db.commit()
        return True


# Dependency injection helper
def get_workflow_service(db: AsyncSession) -> WorkflowService:
    """Create a workflow service instance."""
    return WorkflowService(db)
