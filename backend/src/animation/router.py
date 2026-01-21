"""
Animation API router.
"""

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from pydantic import BaseModel, Field

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
