"""
Rigging module for Sweedle.

Provides auto-rigging capabilities for 3D assets using:
- UniRig (ML-based) for humanoid characters
- Blender headless for quadrupeds and advanced rigging
"""

from .config import rigging_settings
from .schemas import (
    CharacterType,
    RiggingProcessor,
    BoneData,
    SkeletonData,
    WeightData,
    RiggingResult,
    AutoRigRequest,
    RiggingJobStatus,
)

__all__ = [
    "rigging_settings",
    "CharacterType",
    "RiggingProcessor",
    "BoneData",
    "SkeletonData",
    "WeightData",
    "RiggingResult",
    "AutoRigRequest",
    "RiggingJobStatus",
]
