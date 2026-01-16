"""
Animation API router.
"""

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..config import settings
from pydantic import BaseModel, Field
from typing import Optional

from .schemas import (
    AnimationPreset,
    CreateAnimationRequest,
    AnimationClipResponse,
    AnimationClipListResponse,
    AnimationParameters,
    AnimationData,
    AnimationType,
    LoopMode,
)
from .service import AnimationService, ANIMATION_PRESETS
from .fbx_parser import get_fbx_parser
from .retargeting import retarget_mixamo_animation, validate_mixamo_for_skeleton
from ..rigging.schemas import SkeletonData

logger = logging.getLogger(__name__)


class ValidateAnimationRequest(BaseModel):
    """Request to validate animation compatibility."""
    asset_id: str = Field(..., description="Asset to validate")
    preset_id: str = Field(..., description="Animation preset to check")


class ValidateAnimationResponse(BaseModel):
    """Animation validation result."""
    is_valid: bool = Field(..., description="Whether animation can be created")
    animation_type: str
    character_type: str
    coverage_percent: float = Field(..., description="Percentage of bones found")
    missing_required: list[str] = Field(default_factory=list)
    missing_optional: list[str] = Field(default_factory=list)
    found_bones: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

router = APIRouter(prefix="/animation", tags=["animation"])


@router.get("/presets", response_model=list[AnimationPreset])
async def list_presets(character_type: str = None):
    """
    List available animation presets.

    Args:
        character_type: Filter by character type (humanoid/quadruped)

    Returns:
        List of animation presets
    """
    presets = list(ANIMATION_PRESETS.values())
    if character_type:
        presets = [p for p in presets if p.character_type == character_type]
    return presets


@router.get("/presets/{preset_id}", response_model=AnimationPreset)
async def get_preset(preset_id: str):
    """
    Get a specific animation preset.

    Args:
        preset_id: Preset identifier

    Returns:
        Animation preset details
    """
    preset = ANIMATION_PRESETS.get(preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail=f"Preset not found: {preset_id}")
    return preset


@router.post("/validate", response_model=ValidateAnimationResponse)
async def validate_animation(
    request: ValidateAnimationRequest,
    db: AsyncSession = Depends(get_session),
):
    """
    Validate that an asset's skeleton supports an animation preset.

    Use this before creating an animation to check for missing bones
    and get warnings about animation compatibility.

    Args:
        request: Validation request with asset and preset IDs

    Returns:
        Validation result with missing bones and warnings
    """
    service = AnimationService(db)
    try:
        result = await service.validate_animation(
            request.asset_id,
            request.preset_id,
        )
        return ValidateAnimationResponse(
            is_valid=result.is_valid,
            animation_type=result.animation_type.value,
            character_type=result.character_type,
            coverage_percent=result.coverage_percent,
            missing_required=result.missing_required,
            missing_optional=result.missing_optional,
            found_bones=result.found_bones,
            warnings=result.warnings,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/clips", response_model=AnimationClipResponse)
async def create_animation(
    request: CreateAnimationRequest,
    db: AsyncSession = Depends(get_session),
):
    """
    Create an animation clip from a preset.

    This generates procedural animation keyframes for the specified
    rigged asset using the selected preset and parameters.

    Args:
        request: Animation creation parameters

    Returns:
        Created animation clip info
    """
    service = AnimationService(db)
    try:
        clip = await service.create_animation(request)
        return AnimationClipResponse(
            id=clip.id,
            asset_id=clip.asset_id,
            name=clip.name,
            animation_type=AnimationType(clip.animation_type),
            duration=clip.duration_seconds,
            parameters=AnimationParameters(**clip.parameters),
            loop_mode=LoopMode(clip.loop_mode),
            created_at=clip.created_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/clips/asset/{asset_id}", response_model=AnimationClipListResponse)
async def list_asset_animations(
    asset_id: str,
    db: AsyncSession = Depends(get_session),
):
    """
    List all animation clips for an asset.

    Args:
        asset_id: Asset identifier

    Returns:
        List of animation clips
    """
    service = AnimationService(db)
    clips = await service.get_asset_animations(asset_id)
    return AnimationClipListResponse(
        clips=[
            AnimationClipResponse(
                id=c.id,
                asset_id=c.asset_id,
                name=c.name,
                animation_type=AnimationType(c.animation_type),
                duration=c.duration_seconds,
                parameters=AnimationParameters(**c.parameters),
                loop_mode=LoopMode(c.loop_mode),
                created_at=c.created_at,
            )
            for c in clips
        ],
        total=len(clips),
    )


@router.get("/clips/{clip_id}", response_model=AnimationClipResponse)
async def get_animation(
    clip_id: str,
    db: AsyncSession = Depends(get_session),
):
    """
    Get a specific animation clip.

    Args:
        clip_id: Animation clip identifier

    Returns:
        Animation clip details
    """
    service = AnimationService(db)
    clip = await service.get_animation(clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail=f"Animation clip not found: {clip_id}")
    return AnimationClipResponse(
        id=clip.id,
        asset_id=clip.asset_id,
        name=clip.name,
        animation_type=AnimationType(clip.animation_type),
        duration=clip.duration_seconds,
        parameters=AnimationParameters(**clip.parameters),
        loop_mode=LoopMode(clip.loop_mode),
        created_at=clip.created_at,
    )


@router.delete("/clips/{clip_id}")
async def delete_animation(
    clip_id: str,
    db: AsyncSession = Depends(get_session),
):
    """
    Delete an animation clip.

    Args:
        clip_id: Animation clip identifier

    Returns:
        Deletion confirmation
    """
    service = AnimationService(db)
    deleted = await service.delete_animation(clip_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Animation clip not found: {clip_id}")
    return {"message": "Animation clip deleted", "clip_id": clip_id}


@router.get("/clips/{clip_id}/data", response_model=AnimationData)
async def get_animation_data(
    clip_id: str,
    db: AsyncSession = Depends(get_session),
):
    """
    Get the keyframe data for an animation clip.

    This returns the full animation data including keyframe tracks,
    suitable for playback in the frontend viewer.

    Args:
        clip_id: Animation clip identifier

    Returns:
        Animation keyframe data
    """
    service = AnimationService(db)
    data = await service.get_animation_data(clip_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Animation clip not found: {clip_id}")
    return data


@router.put("/clips/{clip_id}/regenerate", response_model=AnimationClipResponse)
async def regenerate_animation(
    clip_id: str,
    parameters: AnimationParameters,
    db: AsyncSession = Depends(get_session),
):
    """
    Regenerate an animation with new parameters.

    Args:
        clip_id: Animation clip identifier
        parameters: New animation parameters

    Returns:
        Updated animation clip
    """
    service = AnimationService(db)
    clip = await service.regenerate_animation(clip_id, parameters)
    if not clip:
        raise HTTPException(status_code=404, detail=f"Animation clip not found: {clip_id}")
    return AnimationClipResponse(
        id=clip.id,
        asset_id=clip.asset_id,
        name=clip.name,
        animation_type=AnimationType(clip.animation_type),
        duration=clip.duration_seconds,
        parameters=AnimationParameters(**clip.parameters),
        loop_mode=LoopMode(clip.loop_mode),
        created_at=clip.created_at,
    )


# ============================================================================
# Mixamo Import Endpoints
# ============================================================================


class MixamoValidateResponse(BaseModel):
    """Response from Mixamo FBX validation."""
    is_valid: bool = Field(..., description="Whether the FBX can be imported")
    animation_name: str = Field(..., description="Animation name from FBX")
    duration_seconds: float = Field(..., description="Animation duration")
    fps: int = Field(..., description="Animation frame rate")
    source_bones: int = Field(..., description="Number of bones in FBX")
    mapped_bones: int = Field(..., description="Bones successfully mapped")
    coverage_percent: float = Field(..., description="Bone mapping coverage")
    has_all_required: bool = Field(..., description="Has all required bones")
    missing_required: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class MixamoUploadResponse(BaseModel):
    """Response from Mixamo animation import."""
    success: bool
    clip_id: str = Field(..., description="Created animation clip ID")
    name: str = Field(..., description="Animation name")
    duration_seconds: float = Field(..., description="Animation duration")
    mapped_bones: int = Field(..., description="Number of bones with animation")
    warnings: list[str] = Field(default_factory=list)


@router.post("/mixamo/validate", response_model=MixamoValidateResponse)
async def validate_mixamo_fbx(
    file: UploadFile = File(..., description="Mixamo FBX file"),
    asset_id: Optional[str] = Form(None, description="Optional asset ID to check compatibility"),
    db: AsyncSession = Depends(get_session),
):
    """
    Validate a Mixamo FBX file before importing.

    Upload an FBX animation downloaded from Mixamo to check if it can be
    imported and retargeted. Optionally specify an asset ID to check
    compatibility with that asset's skeleton.

    Args:
        file: FBX file from Mixamo
        asset_id: Optional asset to check skeleton compatibility

    Returns:
        Validation result with bone mapping info
    """
    if not file.filename.lower().endswith('.fbx'):
        raise HTTPException(status_code=400, detail="File must be an FBX file")

    # Save uploaded file temporarily
    temp_dir = Path(settings.STORAGE_PATH) / "temp" / "mixamo"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"{uuid.uuid4()}.fbx"

    try:
        # Write uploaded file
        content = await file.read()
        temp_path.write_bytes(content)

        # Parse FBX
        parser = get_fbx_parser()
        animation_data = await parser.parse(temp_path)

        # If asset_id provided, validate against that skeleton
        if asset_id:
            service = AnimationService(db)
            asset = await service._get_asset(asset_id)
            if not asset:
                raise HTTPException(status_code=404, detail=f"Asset not found: {asset_id}")
            if not asset.rigging_data:
                raise HTTPException(status_code=400, detail="Asset is not rigged")

            skeleton = SkeletonData(**asset.rigging_data)
            validation = await validate_mixamo_for_skeleton(animation_data, skeleton)

            return MixamoValidateResponse(
                is_valid=validation["is_compatible"],
                animation_name=animation_data.name,
                duration_seconds=animation_data.duration_seconds,
                fps=animation_data.fps,
                source_bones=validation["source_bones"],
                mapped_bones=validation["bones_available_in_target"],
                coverage_percent=validation["coverage_percent"],
                has_all_required=validation["has_all_required"],
                missing_required=validation["missing_required"],
                warnings=validation["warnings"],
            )
        else:
            # Just validate the FBX structure
            from .mixamo_mapping import validate_bone_mapping
            source_bones = list(animation_data.bones.keys())
            mapping = validate_bone_mapping(source_bones)

            return MixamoValidateResponse(
                is_valid=mapping["is_valid"],
                animation_name=animation_data.name,
                duration_seconds=animation_data.duration_seconds,
                fps=animation_data.fps,
                source_bones=len(source_bones),
                mapped_bones=mapping["mapped_bones"],
                coverage_percent=mapping["coverage_percent"],
                has_all_required=mapping["has_all_required"],
                missing_required=mapping["missing_required"],
                warnings=mapping["warnings"],
            )

    except RuntimeError as e:
        logger.error(f"FBX parsing failed: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to parse FBX: {str(e)}")
    finally:
        # Clean up temp file
        if temp_path.exists():
            temp_path.unlink()


@router.post("/mixamo/upload", response_model=MixamoUploadResponse)
async def upload_mixamo_animation(
    file: UploadFile = File(..., description="Mixamo FBX file"),
    asset_id: str = Form(..., description="Asset ID to apply animation to"),
    name: Optional[str] = Form(None, description="Custom animation name"),
    db: AsyncSession = Depends(get_session),
):
    """
    Upload and import a Mixamo animation for a rigged asset.

    Upload an FBX animation downloaded from Mixamo. The animation will be
    parsed, retargeted to the asset's skeleton, and saved as an animation clip.

    Args:
        file: FBX file from Mixamo
        asset_id: Asset to apply the animation to
        name: Optional custom name for the animation

    Returns:
        Created animation clip info
    """
    if not file.filename.lower().endswith('.fbx'):
        raise HTTPException(status_code=400, detail="File must be an FBX file")

    # Get the asset and validate it's rigged
    service = AnimationService(db)
    asset = await service._get_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset not found: {asset_id}")
    if not asset.rigging_data:
        raise HTTPException(status_code=400, detail="Asset must be rigged before importing animations")

    skeleton = SkeletonData(**asset.rigging_data)

    # Save uploaded file temporarily
    temp_dir = Path(settings.STORAGE_PATH) / "temp" / "mixamo"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"{uuid.uuid4()}.fbx"

    try:
        # Write uploaded file
        content = await file.read()
        temp_path.write_bytes(content)

        # Parse FBX
        parser = get_fbx_parser()
        animation_data = await parser.parse(temp_path)

        # Retarget animation
        animation_name = name or animation_data.name
        result = retarget_mixamo_animation(
            animation_data,
            skeleton,
            animation_name,
        )

        if not result.success:
            raise HTTPException(
                status_code=400,
                detail=f"Retargeting failed: {result.error}"
            )

        # Save as animation clip
        clip = await service.create_animation_from_data(
            asset_id=asset_id,
            name=animation_name,
            animation_data=result.animation_data,
            source="mixamo",
        )

        return MixamoUploadResponse(
            success=True,
            clip_id=clip.id,
            name=clip.name,
            duration_seconds=clip.duration_seconds,
            mapped_bones=result.mapped_bones,
            warnings=result.warnings,
        )

    except RuntimeError as e:
        logger.error(f"Mixamo import failed: {e}")
        raise HTTPException(status_code=400, detail=f"Import failed: {str(e)}")
    finally:
        # Clean up temp file
        if temp_path.exists():
            temp_path.unlink()
