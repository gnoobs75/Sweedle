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
from ..generation.models import Asset, GenerationJob, AssetStatus, JobStatus

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
    UpdateSkeletonRequest,
    SkinningData,
    WeightData,
)
from .service import get_rigging_service
from .skeleton import (
    get_default_landmarks,
    get_landmark_info,
    generate_skeleton_from_landmarks,
    fit_landmarks_to_mesh,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rigging", tags=["rigging"])


@router.post("/auto-rig", response_model=AutoRigResponse)
async def auto_rig_asset(
    asset_id: str = Form(...),
    character_type: CharacterType = Form(default=CharacterType.AUTO),
    processor: RiggingProcessor = Form(default=RiggingProcessor.AUTO),
    priority: JobPriority = Form(default=JobPriority.NORMAL),
    force: bool = Form(default=False, description="Force re-rigging even if already rigged"),
    db: AsyncSession = Depends(get_session),
):
    """
    Submit an asset for auto-rigging.

    Creates a rigging job that will be processed by the background worker.
    Progress updates are sent via WebSocket.

    Args:
        force: If True, allows re-rigging an already rigged asset
    """
    # Verify asset exists
    result = await db.execute(select(Asset).where(Asset.id == asset_id))
    asset = result.scalar_one_or_none()

    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset not found: {asset_id}",
        )

    if asset.status != AssetStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Asset is not ready for rigging (status: {asset.status.value if hasattr(asset.status, 'value') else asset.status})",
        )

    # Allow re-rigging if force=True or if skeleton data is missing
    if asset.is_rigged and not force and asset.rigging_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Asset is already rigged. Use force=True to re-rig.",
        )

    # Check if there's an existing rigging job for this asset
    existing_job = await db.execute(
        select(GenerationJob).where(
            GenerationJob.asset_id == asset_id,
            GenerationJob.job_type == "rig_asset",
            GenerationJob.status.in_([JobStatus.PENDING, JobStatus.PROCESSING]),
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
        status=JobStatus.PENDING,
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
        position=0,
    )

    logger.info(f"Created rigging job {job_id} for asset {asset_id}")

    return AutoRigResponse(
        job_id=job_id,
        asset_id=asset_id,
        status="pending",
        message="Rigging job queued successfully",
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


@router.patch("/skeleton/{asset_id}")
async def update_skeleton(
    asset_id: str,
    request: UpdateSkeletonRequest,
    db: AsyncSession = Depends(get_session),
):
    """
    Update skeleton bone positions.

    Allows tuning of individual bone positions after auto-rigging.
    Used by the BoneTuner UI for fixing floating bones.
    """
    result = await db.execute(select(Asset).where(Asset.id == asset_id))
    asset = result.scalar_one_or_none()

    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset not found: {asset_id}",
        )

    if not asset.is_rigged or not asset.rigging_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Asset is not rigged or has no skeleton data",
        )

    # Get current skeleton data
    skeleton_data = dict(asset.rigging_data)
    bones = skeleton_data.get("bones", [])

    # Create a map of bone name to index for quick lookup
    bone_map = {bone["name"]: idx for idx, bone in enumerate(bones)}

    # Apply edits
    updated_count = 0
    for edit in request.edits:
        if edit.bone_name in bone_map:
            idx = bone_map[edit.bone_name]
            bones[idx]["head_position"] = list(edit.head_position)
            bones[idx]["tail_position"] = list(edit.tail_position)
            updated_count += 1
        else:
            logger.warning(f"Bone not found for edit: {edit.bone_name}")

    if updated_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No bones were updated. Check bone names.",
        )

    # Save updated skeleton data
    skeleton_data["bones"] = bones
    asset.rigging_data = skeleton_data
    await db.commit()

    logger.info(f"Updated {updated_count} bones for asset {asset_id}")

    return {
        "message": f"Updated {updated_count} bone(s)",
        "asset_id": asset_id,
        "updated_bones": [e.bone_name for e in request.edits if e.bone_name in bone_map],
    }


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


@router.post("/reset/{asset_id}")
async def reset_rigging(
    asset_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Reset the rigging state for an asset.

    Clears is_rigged flag, skeleton data, and rigged mesh path.
    Use this if rigging failed and left the asset in a bad state.
    """
    result = await db.execute(select(Asset).where(Asset.id == asset_id))
    asset = result.scalar_one_or_none()

    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset not found: {asset_id}",
        )

    # Clear rigging state
    asset.is_rigged = False
    asset.rigging_data = None
    asset.character_type = None
    asset.rigged_mesh_path = None
    asset.rigging_processor = None
    await db.commit()

    logger.info(f"Reset rigging state for asset {asset_id}")

    return {
        "message": "Rigging state reset successfully",
        "asset_id": asset_id,
    }


# ============================================================================
# LANDMARK-BASED SKELETON GENERATION
# ============================================================================


@router.get("/landmarks/{character_type}")
async def get_landmarks(character_type: CharacterType):
    """
    Get default landmark positions for a character type.

    Returns the key positions that users can adjust to generate a skeleton.
    Only 8 landmarks for quadruped, 7 for humanoid.
    """
    if character_type == CharacterType.AUTO:
        character_type = CharacterType.QUADRUPED  # Default for landmark mode

    return {
        "character_type": character_type.value,
        "landmarks": get_default_landmarks(character_type),
    }


@router.get("/landmarks/info/{character_type}")
async def get_landmarks_info(character_type: CharacterType):
    """
    Get landmark metadata including descriptions and colors for UI.
    """
    if character_type == CharacterType.AUTO:
        character_type = CharacterType.QUADRUPED

    return {
        "character_type": character_type.value,
        "landmarks": get_landmark_info(character_type),
    }


@router.post("/landmarks/generate")
async def generate_from_landmarks(
    character_type: CharacterType = Form(...),
    landmarks: str = Form(..., description="JSON string of landmark positions"),
):
    """
    Generate a full skeleton from landmark positions.

    Users position 8 key landmarks (for quadruped) and this generates
    the complete 45-bone skeleton with proper chains between landmarks.
    """
    import json

    try:
        landmark_data = json.loads(landmarks)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid landmarks JSON: {e}",
        )

    if character_type == CharacterType.AUTO:
        character_type = CharacterType.QUADRUPED

    try:
        skeleton = generate_skeleton_from_landmarks(landmark_data, character_type)
        skeleton_data = skeleton.to_skeleton_data()

        return {
            "success": True,
            "character_type": character_type.value,
            "skeleton": skeleton_data.model_dump(),
            "bone_count": skeleton_data.bone_count,
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to generate skeleton from landmarks: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate skeleton: {e}",
        )


@router.post("/landmarks/fit/{asset_id}")
async def fit_landmarks_to_asset(
    asset_id: str,
    character_type: CharacterType = Form(default=CharacterType.QUADRUPED),
    db: AsyncSession = Depends(get_session),
):
    """
    Fit default landmarks to an asset's mesh bounds.

    Returns landmark positions scaled and positioned to fit the asset.
    """
    import numpy as np

    result = await db.execute(select(Asset).where(Asset.id == asset_id))
    asset = result.scalar_one_or_none()

    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset not found: {asset_id}",
        )

    if not asset.file_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Asset has no mesh file",
        )

    # Load mesh to get bounds
    mesh_path = Path(settings.STORAGE_ROOT) / asset.file_path
    if not mesh_path.exists():
        mesh_path = Path(asset.file_path)

    if not mesh_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mesh file not found",
        )

    try:
        import trimesh
        mesh = trimesh.load(str(mesh_path))

        if isinstance(mesh, trimesh.Scene):
            geometries = list(mesh.geometry.values())
            if geometries:
                mesh = trimesh.util.concatenate(geometries)
            else:
                raise ValueError("No geometry in mesh")

        mesh_bounds = (np.array(mesh.bounds[0]), np.array(mesh.bounds[1]))

        if character_type == CharacterType.AUTO:
            # Detect type from mesh aspect ratio
            dims = mesh_bounds[1] - mesh_bounds[0]
            height_ratio = dims[1] / max(max(dims[0], dims[2]), 0.001)
            character_type = CharacterType.HUMANOID if height_ratio > 1.5 else CharacterType.QUADRUPED

        fitted_landmarks = fit_landmarks_to_mesh(mesh_bounds, character_type)

        return {
            "success": True,
            "asset_id": asset_id,
            "character_type": character_type.value,
            "landmarks": fitted_landmarks,
            "mesh_bounds": {
                "min": mesh_bounds[0].tolist(),
                "max": mesh_bounds[1].tolist(),
            },
        }

    except Exception as e:
        logger.error(f"Failed to fit landmarks to asset: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fit landmarks: {e}",
        )


@router.post("/landmarks/apply/{asset_id}")
async def apply_landmarks_to_asset(
    asset_id: str,
    character_type: CharacterType = Form(...),
    landmarks: str = Form(..., description="JSON string of landmark positions"),
    db: AsyncSession = Depends(get_session),
):
    """
    Apply landmark-generated skeleton to an asset.

    Generates skeleton from landmarks, computes skinning weights, and saves to asset.
    """
    import json
    import numpy as np
    import trimesh

    result = await db.execute(select(Asset).where(Asset.id == asset_id))
    asset = result.scalar_one_or_none()

    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset not found: {asset_id}",
        )

    try:
        landmark_data = json.loads(landmarks)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid landmarks JSON: {e}",
        )

    if character_type == CharacterType.AUTO:
        character_type = CharacterType.QUADRUPED

    # Load mesh for weight computation
    mesh_path = Path(settings.STORAGE_ROOT) / asset.file_path
    if not mesh_path.exists():
        mesh_path = Path(asset.file_path)

    if not mesh_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mesh file not found",
        )

    try:
        mesh = trimesh.load(str(mesh_path))
        if isinstance(mesh, trimesh.Scene):
            geometries = list(mesh.geometry.values())
            if geometries:
                mesh = trimesh.util.concatenate(geometries)
            else:
                raise ValueError("No geometry in mesh")

        # Generate skeleton
        skeleton = generate_skeleton_from_landmarks(landmark_data, character_type)
        skeleton_data = skeleton.to_skeleton_data()

        # Compute skinning weights
        skinning_data = _compute_skinning_weights(mesh, skeleton)

        # Save to asset
        asset.is_rigged = True
        asset.character_type = character_type.value
        asset.rigging_data = skeleton_data.model_dump()
        asset.skinning_data = skinning_data.model_dump()
        asset.rigging_processor = "landmarks"
        await db.commit()

        logger.info(f"Applied landmark skeleton to asset {asset_id}: {skeleton_data.bone_count} bones, {skinning_data.vertex_count} vertices weighted")

        return {
            "success": True,
            "asset_id": asset_id,
            "skeleton": skeleton_data.model_dump(),
            "bone_count": skeleton_data.bone_count,
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to apply landmarks: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply landmarks: {e}",
        )


def _compute_skinning_weights(mesh: "trimesh.Trimesh", skeleton) -> SkinningData:
    """
    Compute skinning weights using proximity-based algorithm.

    Each vertex is weighted to the closest bones based on distance.
    """
    import numpy as np

    vertices = mesh.vertices
    bones = skeleton.get_all_bones()

    # Only use deforming bones
    deform_bones = [b for b in bones if b.deform]

    weights_list = []

    for vi, vertex in enumerate(vertices):
        bone_weights = {}

        # Calculate distance to each bone
        distances = []
        for bone in deform_bones:
            # Distance from vertex to bone segment
            dist = _point_to_segment_distance(
                vertex,
                bone.head,
                bone.tail,
            )
            distances.append((bone.name, dist))

        # Sort by distance
        distances.sort(key=lambda x: x[1])

        # Take top 4 closest bones (standard for game engines)
        max_influences = 4
        closest = distances[:max_influences]

        # Convert distances to weights using inverse distance weighting
        if closest:
            total_inv_dist = sum(1.0 / max(d, 0.001) for _, d in closest)

            for bone_name, dist in closest:
                weight = (1.0 / max(dist, 0.001)) / total_inv_dist
                if weight > 0.01:  # Threshold small weights
                    bone_weights[bone_name] = weight

            # Normalize weights
            total = sum(bone_weights.values())
            if total > 0:
                bone_weights = {k: v / total for k, v in bone_weights.items()}

        weights_list.append(WeightData(
            vertex_index=vi,
            bone_weights=bone_weights,
        ))

    return SkinningData(
        vertex_count=len(vertices),
        weights=weights_list,
        max_influences=4,
    )


def _point_to_segment_distance(
    point: "np.ndarray",
    seg_start: "np.ndarray",
    seg_end: "np.ndarray",
) -> float:
    """Calculate distance from point to line segment."""
    import numpy as np

    segment = seg_end - seg_start
    segment_length_sq = np.dot(segment, segment)

    if segment_length_sq < 1e-10:
        # Degenerate segment
        return float(np.linalg.norm(point - seg_start))

    # Project point onto segment
    t = max(0, min(1, np.dot(point - seg_start, segment) / segment_length_sq))
    projection = seg_start + t * segment

    return float(np.linalg.norm(point - projection))
