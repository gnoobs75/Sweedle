"""
Pydantic schemas for animation operations.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class AnimationType(str, Enum):
    """Available animation types."""
    # Common animations (both humanoid and quadruped)
    IDLE = "idle"
    WALK = "walk"
    RUN = "run"
    ATTACK = "attack"
    JUMP = "jump"
    DIE = "die"
    SIT = "sit"
    LIE_DOWN = "lie_down"

    # Humanoid-specific
    CROUCH = "crouch"
    DODGE = "dodge"
    WAVE = "wave"
    CHEER = "cheer"
    PICKUP = "pickup"

    # Quadruped-specific
    TROT = "trot"
    GALLOP = "gallop"
    TAIL_WAG = "tail_wag"
    BITE = "bite"
    SHAKE = "shake"
    POUNCE = "pounce"
    HOWL = "howl"
    ROLL_OVER = "roll_over"
    PLAY_DEAD = "play_dead"


class LoopMode(str, Enum):
    """Animation loop modes."""
    LOOP = "loop"
    ONCE = "once"
    PINGPONG = "pingpong"


class AnimationParameters(BaseModel):
    """Parameters for procedural animation generation."""
    speed: float = Field(
        default=1.0,
        ge=0.1,
        le=3.0,
        description="Animation speed multiplier"
    )
    intensity: float = Field(
        default=1.0,
        ge=0.1,
        le=2.0,
        description="Movement intensity/amplitude"
    )
    blend_factor: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Blend with base pose"
    )


class AnimationPreset(BaseModel):
    """Animation preset definition."""
    id: str
    name: str
    description: str
    animation_type: AnimationType
    character_type: str  # humanoid or quadruped
    default_parameters: AnimationParameters
    duration: float
    thumbnail_url: Optional[str] = None
    tags: list[str] = []


class KeyframeTrack(BaseModel):
    """Animation track for a single bone."""
    bone_name: str = Field(..., description="Target bone name")
    times: list[float] = Field(..., description="Keyframe times in seconds")
    positions: Optional[list[list[float]]] = Field(
        None,
        description="Position values [x,y,z] per keyframe"
    )
    rotations: Optional[list[list[float]]] = Field(
        None,
        description="Rotation quaternions [x,y,z,w] per keyframe"
    )
    scales: Optional[list[list[float]]] = Field(
        None,
        description="Scale values [x,y,z] per keyframe"
    )


class AnimationData(BaseModel):
    """Complete animation data for export/playback."""
    name: str
    duration: float
    frame_rate: int
    tracks: list[KeyframeTrack]


class CreateAnimationRequest(BaseModel):
    """Request to create an animation from a preset."""
    asset_id: str = Field(..., description="ID of the rigged asset")
    preset_id: str = Field(..., description="ID of the animation preset")
    name: Optional[str] = Field(None, description="Custom name for the animation")
    parameters: Optional[AnimationParameters] = Field(
        None,
        description="Custom parameters (uses preset defaults if not specified)"
    )
    loop_mode: LoopMode = Field(
        default=LoopMode.LOOP,
        description="Animation loop mode"
    )


class AnimationClipResponse(BaseModel):
    """Animation clip response."""
    id: str
    asset_id: str
    name: str
    animation_type: AnimationType
    duration: float
    parameters: AnimationParameters
    loop_mode: LoopMode
    created_at: datetime


class AnimationClipListResponse(BaseModel):
    """List of animation clips response."""
    clips: list[AnimationClipResponse]
    total: int


# ============ Animation Retargeting Schemas ============

class BoneMapping(BaseModel):
    """Mapping between source and target bone names."""
    source_bone: str = Field(..., description="Bone name in source skeleton")
    target_bone: str = Field(..., description="Bone name in target skeleton")
    scale_factor: float = Field(default=1.0, ge=0.1, le=10.0, description="Scale factor for proportional retargeting")


class RetargetingPreset(str, Enum):
    """Predefined bone mapping presets for common skeleton types."""
    MIXAMO_TO_STANDARD = "mixamo_to_standard"
    STANDARD_TO_MIXAMO = "standard_to_mixamo"
    BLENDER_TO_STANDARD = "blender_to_standard"
    STANDARD_TO_BLENDER = "standard_to_blender"
    UNITY_TO_STANDARD = "unity_to_standard"
    STANDARD_TO_UNITY = "standard_to_unity"
    AUTO_DETECT = "auto_detect"


class RetargetAnimationRequest(BaseModel):
    """Request to retarget animation from source to target asset."""
    source_clip_id: str = Field(..., description="Animation clip ID to retarget from")
    target_asset_id: str = Field(..., description="Target asset to apply animation to")
    name: Optional[str] = Field(None, description="Name for the retargeted animation")
    preset: Optional[RetargetingPreset] = Field(
        None,
        description="Use a predefined bone mapping preset"
    )
    custom_mappings: Optional[list[BoneMapping]] = Field(
        None,
        description="Custom bone mappings (overrides preset)"
    )
    adjust_proportions: bool = Field(
        default=True,
        description="Adjust animations for different skeleton proportions"
    )
    preserve_root_motion: bool = Field(
        default=True,
        description="Keep root bone motion"
    )


class RetargetAnimationResponse(BaseModel):
    """Response from animation retargeting."""
    success: bool
    clip_id: Optional[str] = None
    source_bones_mapped: int
    target_bones_affected: int
    unmapped_bones: list[str]
    warnings: list[str]
    message: str
    error: Optional[str] = None


class GetMappingSuggestionsRequest(BaseModel):
    """Request for auto-generated bone mapping suggestions."""
    source_asset_id: str = Field(..., description="Asset with source skeleton")
    target_asset_id: str = Field(..., description="Asset with target skeleton")


class BoneMappingSuggestion(BaseModel):
    """Suggested mapping between bones."""
    source_bone: str
    target_bone: str
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in the mapping")
    reason: str = Field(..., description="Why this mapping was suggested")


class GetMappingSuggestionsResponse(BaseModel):
    """Response with suggested bone mappings."""
    success: bool
    source_bones: list[str]
    target_bones: list[str]
    suggestions: list[BoneMappingSuggestion]
    unmapped_source: list[str]
    unmapped_target: list[str]
    message: str


class RetargetingPresetInfo(BaseModel):
    """Information about a retargeting preset."""
    id: RetargetingPreset
    name: str
    description: str
    source_type: str
    target_type: str
    mappings_count: int
