"""
Rigging configuration settings.
"""

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings


class RiggingSettings(BaseSettings):
    """Configuration for rigging operations."""

    # UniRig settings
    UNIRIG_MODEL_PATH: str = "models/unirig"
    UNIRIG_DEVICE: str = "cuda"
    UNIRIG_ENABLED: bool = True

    # Blender settings
    BLENDER_PATH: str = "blender"
    BLENDER_TIMEOUT: int = 300  # 5 minutes
    BLENDER_ENABLED: bool = True

    # Skeleton templates
    HUMANOID_BONE_COUNT: int = 65
    QUADRUPED_BONE_COUNT: int = 45

    # Processing limits
    MAX_VERTICES_FOR_UNIRIG: int = 100000
    MAX_VERTICES_FOR_RIGGING: int = 500000
    FALLBACK_TO_BLENDER: bool = True

    # Character detection
    HUMANOID_HEIGHT_RATIO_MIN: float = 1.5  # height/width ratio
    HUMANOID_HEIGHT_RATIO_MAX: float = 4.0
    QUADRUPED_HEIGHT_RATIO_MAX: float = 1.5

    # Output settings
    DEFAULT_EXPORT_FORMAT: str = "glb"
    ENABLE_FBX_EXPORT: bool = True
    ENABLE_WEIGHT_VISUALIZATION: bool = True

    # Storage
    RIGGED_SUBDIR: str = "rigged"

    class Config:
        env_prefix = "RIGGING_"
        case_sensitive = False


rigging_settings = RiggingSettings()
