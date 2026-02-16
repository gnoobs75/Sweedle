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


class GeneratePreviewRequest(BaseModel):
    """Request to generate animation preview."""
    clip_id: str = Field(..., description="Animation clip ID")
    width: int = Field(default=256, ge=64, le=512)
    height: int = Field(default=256, ge=64, le=512)
    fps: int = Field(default=15, ge=5, le=30)
    format: str = Field(default="gif", pattern="^(gif|webp)$")


class GeneratePreviewResponse(BaseModel):
    """Response for animation preview generation."""
    success: bool
    clip_id: str
    preview_path: str | None = None
    frame_count: int = 0
    duration_ms: int = 0
    file_size_bytes: int = 0
    error: str | None = None


@router.post("/clips/{clip_id}/preview", response_model=GeneratePreviewResponse)
async def generate_preview(
    clip_id: str,
    request: GeneratePreviewRequest = None,
    db: AsyncSession = Depends(get_session),
):
    """
    Generate an animated preview (GIF/WebP) for an animation clip.

    Args:
        clip_id: Animation clip identifier
        request: Preview generation options

    Returns:
        Preview file path and metadata
    """
    import numpy as np
    from PIL import Image
    import io
    from ..config import settings
    from ..generation.models import AnimationClip, Asset
    from sqlalchemy import select

    if request is None:
        request = GeneratePreviewRequest(clip_id=clip_id)

    try:
        # Get animation clip
        query = select(AnimationClip).where(AnimationClip.id == clip_id)
        result = await db.execute(query)
        clip = result.scalar_one_or_none()

        if not clip:
            return GeneratePreviewResponse(
                success=False,
                clip_id=clip_id,
                error="Animation clip not found",
            )

        # Get asset for skeleton data
        query = select(Asset).where(Asset.id == clip.asset_id)
        result = await db.execute(query)
        asset = result.scalar_one_or_none()

        if not asset or not asset.rigging_data:
            return GeneratePreviewResponse(
                success=False,
                clip_id=clip_id,
                error="Asset rigging data not found",
            )

        # Get keyframe data
        keyframe_data = clip.keyframe_data
        if not keyframe_data or 'tracks' not in keyframe_data:
            return GeneratePreviewResponse(
                success=False,
                clip_id=clip_id,
                error="Animation keyframe data not found",
            )

        # Get skeleton bones
        skeleton = asset.rigging_data
        bones = skeleton.get('bones', [])
        if not bones:
            return GeneratePreviewResponse(
                success=False,
                clip_id=clip_id,
                error="No bones in skeleton",
            )

        # Generate frames
        duration = clip.duration_seconds
        frame_count = int(duration * request.fps)
        frame_count = max(5, min(frame_count, 60))  # Limit to 5-60 frames

        frames = []
        for frame_idx in range(frame_count):
            t = frame_idx / frame_count * duration

            # Create frame using matplotlib
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            from mpl_toolkits.mplot3d import Axes3D

            fig = plt.figure(figsize=(request.width/100, request.height/100), dpi=100)
            ax = fig.add_subplot(111, projection='3d')

            # Draw bones
            for bone in bones:
                pos = bone.get('head_position', [0, 0, 0])
                tail = bone.get('tail_position', pos)

                # Apply animation transforms at time t
                for track in keyframe_data.get('tracks', []):
                    if track.get('bone_name') == bone.get('name'):
                        times = track.get('times', [])
                        values = track.get('values', [])
                        if times and values and track.get('property') == 'position':
                            # Simple linear interpolation
                            for i, time in enumerate(times[:-1]):
                                if time <= t <= times[i+1]:
                                    alpha = (t - time) / (times[i+1] - time)
                                    val_idx = i * 3
                                    if val_idx + 5 < len(values):
                                        pos = [
                                            values[val_idx] + alpha * (values[val_idx+3] - values[val_idx]),
                                            values[val_idx+1] + alpha * (values[val_idx+4] - values[val_idx+1]),
                                            values[val_idx+2] + alpha * (values[val_idx+5] - values[val_idx+2]),
                                        ]
                                    break

                # Draw bone line
                ax.plot3D(
                    [pos[0], tail[0]],
                    [pos[2], tail[2]],  # Swap Y and Z for better view
                    [pos[1], tail[1]],
                    color='#6366f1',
                    linewidth=2,
                )
                # Draw joint
                ax.scatter([pos[0]], [pos[2]], [pos[1]], color='#f59e0b', s=20)

            # Style the plot
            ax.set_facecolor('#1f2937')
            fig.patch.set_facecolor('#1f2937')
            ax.set_xlim(-1, 1)
            ax.set_ylim(-1, 1)
            ax.set_zlim(0, 2)
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_zticks([])
            ax.xaxis.pane.fill = False
            ax.yaxis.pane.fill = False
            ax.zaxis.pane.fill = False
            ax.xaxis.pane.set_edgecolor('none')
            ax.yaxis.pane.set_edgecolor('none')
            ax.zaxis.pane.set_edgecolor('none')

            # Rotate view slightly for each frame for 3D effect
            ax.view_init(elev=20, azim=30 + frame_idx * 2)

            # Save to buffer
            buf = io.BytesIO()
            plt.savefig(buf, format='png', facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight', pad_inches=0)
            buf.seek(0)
            frames.append(Image.open(buf).convert('RGBA'))
            plt.close(fig)

        if not frames:
            return GeneratePreviewResponse(
                success=False,
                clip_id=clip_id,
                error="Failed to generate frames",
            )

        # Save as GIF or WebP
        output_dir = settings.GENERATED_DIR / clip.asset_id
        output_dir.mkdir(parents=True, exist_ok=True)

        if request.format == 'gif':
            output_path = output_dir / f"anim_preview_{clip_id[:8]}.gif"
            frames[0].save(
                output_path,
                save_all=True,
                append_images=frames[1:],
                duration=int(1000 / request.fps),
                loop=0,
            )
        else:
            output_path = output_dir / f"anim_preview_{clip_id[:8]}.webp"
            frames[0].save(
                output_path,
                save_all=True,
                append_images=frames[1:],
                duration=int(1000 / request.fps),
                loop=0,
            )

        # Get file size
        file_size = output_path.stat().st_size

        # Update clip with preview path
        relative_path = f"{clip.asset_id}/anim_preview_{clip_id[:8]}.{request.format}"
        clip.preview_path = relative_path
        await db.commit()

        logger.info(f"Generated animation preview: {output_path}")

        return GeneratePreviewResponse(
            success=True,
            clip_id=clip_id,
            preview_path=f"/storage/generated/{relative_path}",
            frame_count=len(frames),
            duration_ms=int(duration * 1000),
            file_size_bytes=file_size,
        )

    except Exception as e:
        logger.error(f"Failed to generate animation preview: {e}")
        return GeneratePreviewResponse(
            success=False,
            clip_id=clip_id,
            error=str(e),
        )


# ============ Animation Retargeting Endpoints ============

from .schemas import (
    RetargetAnimationRequest,
    RetargetAnimationResponse,
    GetMappingSuggestionsRequest,
    GetMappingSuggestionsResponse,
    BoneMappingSuggestion,
    RetargetingPreset,
    RetargetingPresetInfo,
    BoneMapping,
)


# Predefined bone mapping presets
BONE_MAPPING_PRESETS = {
    RetargetingPreset.MIXAMO_TO_STANDARD: {
        "name": "Mixamo to Standard",
        "description": "Map Mixamo bone names to standard naming convention",
        "source_type": "Mixamo",
        "target_type": "Standard",
        "mappings": [
            ("mixamorig:Hips", "Hips"),
            ("mixamorig:Spine", "Spine"),
            ("mixamorig:Spine1", "Spine1"),
            ("mixamorig:Spine2", "Chest"),
            ("mixamorig:Neck", "Neck"),
            ("mixamorig:Head", "Head"),
            ("mixamorig:LeftShoulder", "LeftShoulder"),
            ("mixamorig:LeftArm", "LeftArm"),
            ("mixamorig:LeftForeArm", "LeftForeArm"),
            ("mixamorig:LeftHand", "LeftHand"),
            ("mixamorig:RightShoulder", "RightShoulder"),
            ("mixamorig:RightArm", "RightArm"),
            ("mixamorig:RightForeArm", "RightForeArm"),
            ("mixamorig:RightHand", "RightHand"),
            ("mixamorig:LeftUpLeg", "LeftUpLeg"),
            ("mixamorig:LeftLeg", "LeftLeg"),
            ("mixamorig:LeftFoot", "LeftFoot"),
            ("mixamorig:RightUpLeg", "RightUpLeg"),
            ("mixamorig:RightLeg", "RightLeg"),
            ("mixamorig:RightFoot", "RightFoot"),
        ],
    },
    RetargetingPreset.STANDARD_TO_MIXAMO: {
        "name": "Standard to Mixamo",
        "description": "Map standard bone names to Mixamo naming convention",
        "source_type": "Standard",
        "target_type": "Mixamo",
        "mappings": [
            ("Hips", "mixamorig:Hips"),
            ("Spine", "mixamorig:Spine"),
            ("Chest", "mixamorig:Spine2"),
            ("Neck", "mixamorig:Neck"),
            ("Head", "mixamorig:Head"),
            ("LeftShoulder", "mixamorig:LeftShoulder"),
            ("LeftArm", "mixamorig:LeftArm"),
            ("LeftForeArm", "mixamorig:LeftForeArm"),
            ("LeftHand", "mixamorig:LeftHand"),
            ("RightShoulder", "mixamorig:RightShoulder"),
            ("RightArm", "mixamorig:RightArm"),
            ("RightForeArm", "mixamorig:RightForeArm"),
            ("RightHand", "mixamorig:RightHand"),
            ("LeftUpLeg", "mixamorig:LeftUpLeg"),
            ("LeftLeg", "mixamorig:LeftLeg"),
            ("LeftFoot", "mixamorig:LeftFoot"),
            ("RightUpLeg", "mixamorig:RightUpLeg"),
            ("RightLeg", "mixamorig:RightLeg"),
            ("RightFoot", "mixamorig:RightFoot"),
        ],
    },
    RetargetingPreset.BLENDER_TO_STANDARD: {
        "name": "Blender to Standard",
        "description": "Map Blender Rigify bone names to standard",
        "source_type": "Blender Rigify",
        "target_type": "Standard",
        "mappings": [
            ("spine", "Hips"),
            ("spine.001", "Spine"),
            ("spine.002", "Chest"),
            ("spine.003", "Neck"),
            ("spine.004", "Head"),
            ("shoulder.L", "LeftShoulder"),
            ("upper_arm.L", "LeftArm"),
            ("forearm.L", "LeftForeArm"),
            ("hand.L", "LeftHand"),
            ("shoulder.R", "RightShoulder"),
            ("upper_arm.R", "RightArm"),
            ("forearm.R", "RightForeArm"),
            ("hand.R", "RightHand"),
            ("thigh.L", "LeftUpLeg"),
            ("shin.L", "LeftLeg"),
            ("foot.L", "LeftFoot"),
            ("thigh.R", "RightUpLeg"),
            ("shin.R", "RightLeg"),
            ("foot.R", "RightFoot"),
        ],
    },
}


@router.get("/retargeting/presets", response_model=list[RetargetingPresetInfo])
async def list_retargeting_presets():
    """List available retargeting presets."""
    result = []
    for preset_id, preset_data in BONE_MAPPING_PRESETS.items():
        result.append(RetargetingPresetInfo(
            id=preset_id,
            name=preset_data["name"],
            description=preset_data["description"],
            source_type=preset_data["source_type"],
            target_type=preset_data["target_type"],
            mappings_count=len(preset_data["mappings"]),
        ))
    return result


@router.post("/retargeting/suggest-mappings", response_model=GetMappingSuggestionsResponse)
async def suggest_bone_mappings(
    request: GetMappingSuggestionsRequest,
    db: AsyncSession = Depends(get_session),
):
    """
    Automatically suggest bone mappings between two skeletons.

    Uses name similarity and bone position to suggest mappings.
    """
    from ..generation.models import Asset
    from sqlalchemy import select
    from difflib import SequenceMatcher

    # Get source and target assets
    source_query = select(Asset).where(Asset.id == request.source_asset_id)
    target_query = select(Asset).where(Asset.id == request.target_asset_id)

    source_result = await db.execute(source_query)
    target_result = await db.execute(target_query)

    source_asset = source_result.scalar_one_or_none()
    target_asset = target_result.scalar_one_or_none()

    if not source_asset or not source_asset.rigging_data:
        return GetMappingSuggestionsResponse(
            success=False,
            source_bones=[],
            target_bones=[],
            suggestions=[],
            unmapped_source=[],
            unmapped_target=[],
            message="Source asset not found or not rigged",
        )

    if not target_asset or not target_asset.rigging_data:
        return GetMappingSuggestionsResponse(
            success=False,
            source_bones=[],
            target_bones=[],
            suggestions=[],
            unmapped_source=[],
            unmapped_target=[],
            message="Target asset not found or not rigged",
        )

    # Extract bone names
    source_bones = [b.get("name", "") for b in source_asset.rigging_data.get("bones", [])]
    target_bones = [b.get("name", "") for b in target_asset.rigging_data.get("bones", [])]

    # Generate suggestions based on name similarity
    suggestions = []
    mapped_source = set()
    mapped_target = set()

    # Common bone name patterns for matching
    BONE_KEYWORDS = {
        "hips": ["hip", "pelvis", "root"],
        "spine": ["spine", "torso", "back"],
        "chest": ["chest", "spine2", "ribcage"],
        "neck": ["neck"],
        "head": ["head", "skull"],
        "shoulder": ["shoulder", "clavicle"],
        "arm": ["arm", "upperarm", "upper_arm"],
        "forearm": ["forearm", "lowerarm", "lower_arm", "elbow"],
        "hand": ["hand", "wrist"],
        "upleg": ["upleg", "thigh", "upperleg", "upper_leg"],
        "leg": ["leg", "shin", "calf", "lowerleg", "lower_leg", "knee"],
        "foot": ["foot", "ankle"],
    }

    def normalize_bone_name(name: str) -> str:
        """Normalize bone name for comparison."""
        return name.lower().replace("_", "").replace(".", "").replace(":", "").replace("-", "")

    def get_bone_similarity(source: str, target: str) -> float:
        """Calculate similarity between bone names."""
        s_norm = normalize_bone_name(source)
        t_norm = normalize_bone_name(target)

        # Direct match
        if s_norm == t_norm:
            return 1.0

        # Check if both contain same keyword
        for category, keywords in BONE_KEYWORDS.items():
            s_has = any(kw in s_norm for kw in keywords)
            t_has = any(kw in t_norm for kw in keywords)
            if s_has and t_has:
                # Check side matching (left/right)
                s_left = "left" in s_norm or s_norm.endswith("l") or ".l" in source.lower()
                s_right = "right" in s_norm or s_norm.endswith("r") or ".r" in source.lower()
                t_left = "left" in t_norm or t_norm.endswith("l") or ".l" in target.lower()
                t_right = "right" in t_norm or t_norm.endswith("r") or ".r" in target.lower()

                if (s_left and t_left) or (s_right and t_right) or (not s_left and not s_right and not t_left and not t_right):
                    return 0.8

        # Sequence matching as fallback
        return SequenceMatcher(None, s_norm, t_norm).ratio()

    # Find best matches
    for source_bone in source_bones:
        best_match = None
        best_score = 0.5  # Minimum threshold

        for target_bone in target_bones:
            if target_bone in mapped_target:
                continue

            score = get_bone_similarity(source_bone, target_bone)
            if score > best_score:
                best_score = score
                best_match = target_bone

        if best_match:
            suggestions.append(BoneMappingSuggestion(
                source_bone=source_bone,
                target_bone=best_match,
                confidence=best_score,
                reason="Name similarity" if best_score < 0.8 else "Strong name match",
            ))
            mapped_source.add(source_bone)
            mapped_target.add(best_match)

    unmapped_source = [b for b in source_bones if b not in mapped_source]
    unmapped_target = [b for b in target_bones if b not in mapped_target]

    return GetMappingSuggestionsResponse(
        success=True,
        source_bones=source_bones,
        target_bones=target_bones,
        suggestions=suggestions,
        unmapped_source=unmapped_source,
        unmapped_target=unmapped_target,
        message=f"Found {len(suggestions)} bone mapping suggestions",
    )


@router.post("/retargeting/apply", response_model=RetargetAnimationResponse)
async def retarget_animation(
    request: RetargetAnimationRequest,
    db: AsyncSession = Depends(get_session),
):
    """
    Retarget an animation from one skeleton to another.

    This takes an existing animation clip and creates a new clip
    with bone names mapped to the target skeleton.
    """
    from ..generation.models import AnimationClip, Asset
    from sqlalchemy import select

    # Get source clip
    clip_query = select(AnimationClip).where(AnimationClip.id == request.source_clip_id)
    clip_result = await db.execute(clip_query)
    source_clip = clip_result.scalar_one_or_none()

    if not source_clip:
        return RetargetAnimationResponse(
            success=False,
            source_bones_mapped=0,
            target_bones_affected=0,
            unmapped_bones=[],
            warnings=["Source animation clip not found"],
            message="Source animation clip not found",
            error="Source clip not found",
        )

    # Get target asset
    target_query = select(Asset).where(Asset.id == request.target_asset_id)
    target_result = await db.execute(target_query)
    target_asset = target_result.scalar_one_or_none()

    if not target_asset or not target_asset.rigging_data:
        return RetargetAnimationResponse(
            success=False,
            source_bones_mapped=0,
            target_bones_affected=0,
            unmapped_bones=[],
            warnings=["Target asset not found or not rigged"],
            message="Target asset not found or not rigged",
            error="Target asset not rigged",
        )

    try:
        # Build bone mapping
        bone_map = {}
        warnings = []

        if request.preset and request.preset != RetargetingPreset.AUTO_DETECT:
            # Use preset mappings
            preset_data = BONE_MAPPING_PRESETS.get(request.preset)
            if preset_data:
                for source, target in preset_data["mappings"]:
                    bone_map[source] = target
            else:
                warnings.append(f"Unknown preset: {request.preset}")

        if request.custom_mappings:
            # Override with custom mappings
            for mapping in request.custom_mappings:
                bone_map[mapping.source_bone] = mapping.target_bone

        if request.preset == RetargetingPreset.AUTO_DETECT:
            # Auto-detect mappings
            suggestion_request = GetMappingSuggestionsRequest(
                source_asset_id=source_clip.asset_id,
                target_asset_id=request.target_asset_id,
            )
            suggestions_response = await suggest_bone_mappings(suggestion_request, db)
            for suggestion in suggestions_response.suggestions:
                if suggestion.confidence >= 0.6:
                    bone_map[suggestion.source_bone] = suggestion.target_bone

        # Get source keyframe data
        source_data = source_clip.keyframe_data
        if not source_data or "tracks" not in source_data:
            return RetargetAnimationResponse(
                success=False,
                source_bones_mapped=0,
                target_bones_affected=0,
                unmapped_bones=[],
                warnings=["Source animation has no keyframe data"],
                message="No keyframe data in source animation",
                error="No keyframe data",
            )

        # Retarget keyframes
        target_tracks = []
        source_bones_mapped = 0
        unmapped_bones = []
        target_bone_names = {b.get("name") for b in target_asset.rigging_data.get("bones", [])}

        for track in source_data["tracks"]:
            source_bone = track.get("bone_name")
            target_bone = bone_map.get(source_bone, source_bone)

            # Check if target bone exists
            if target_bone in target_bone_names:
                new_track = {
                    **track,
                    "bone_name": target_bone,
                }
                target_tracks.append(new_track)
                source_bones_mapped += 1
            else:
                unmapped_bones.append(source_bone)

        if not target_tracks:
            return RetargetAnimationResponse(
                success=False,
                source_bones_mapped=0,
                target_bones_affected=0,
                unmapped_bones=unmapped_bones,
                warnings=["No bones could be mapped"],
                message="Retargeting failed - no compatible bones",
                error="No compatible bones",
            )

        # Create new animation clip
        clip_id = str(uuid.uuid4())
        clip_name = request.name or f"{source_clip.name} (Retargeted)"

        new_clip = AnimationClip(
            id=clip_id,
            asset_id=request.target_asset_id,
            name=clip_name,
            description=f"Retargeted from {source_clip.name}",
            animation_type=source_clip.animation_type,
            character_type=target_asset.character_type or source_clip.character_type,
            parameters=source_clip.parameters,
            duration_seconds=source_clip.duration_seconds,
            frame_rate=source_clip.frame_rate,
            loop_mode=source_clip.loop_mode,
            keyframe_data={
                **source_data,
                "tracks": target_tracks,
            },
        )

        db.add(new_clip)

        # Update target asset
        target_asset.has_animations = True
        await db.commit()

        logger.info(f"Retargeted animation {source_clip.id} to asset {request.target_asset_id}")

        return RetargetAnimationResponse(
            success=True,
            clip_id=clip_id,
            source_bones_mapped=source_bones_mapped,
            target_bones_affected=len({t["bone_name"] for t in target_tracks}),
            unmapped_bones=unmapped_bones,
            warnings=warnings,
            message=f"Successfully retargeted animation with {source_bones_mapped} bones",
        )

    except Exception as e:
        await db.rollback()
        logger.error(f"Retargeting failed: {e}")
        return RetargetAnimationResponse(
            success=False,
            source_bones_mapped=0,
            target_bones_affected=0,
            unmapped_bones=[],
            warnings=[str(e)],
            message="Retargeting failed",
            error=str(e),
        )
