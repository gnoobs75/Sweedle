"""
Pydantic schemas for animation operations.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class AnimationType(str, Enum):
    """Available animation types."""
    IDLE = "idle"
    WALK = "walk"
    RUN = "run"
    ATTACK = "attack"
    # Quadruped-specific
    TROT = "trot"
    TAIL_WAG = "tail_wag"
    BITE = "bite"


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
