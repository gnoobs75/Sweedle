"""
Animation module for Sweedle.

Provides procedural animation generation for rigged 3D models.
"""

from .schemas import (
    AnimationType,
    LoopMode,
    AnimationParameters,
    AnimationPreset,
    AnimationData,
    KeyframeTrack,
    CreateAnimationRequest,
    AnimationClipResponse,
)
from .service import AnimationService, ANIMATION_PRESETS

__all__ = [
    "AnimationType",
    "LoopMode",
    "AnimationParameters",
    "AnimationPreset",
    "AnimationData",
    "KeyframeTrack",
    "CreateAnimationRequest",
    "AnimationClipResponse",
    "AnimationService",
    "ANIMATION_PRESETS",
]
