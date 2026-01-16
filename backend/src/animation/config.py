"""
Animation configuration settings.
"""

from pydantic_settings import BaseSettings


class AnimationSettings(BaseSettings):
    """Animation module settings."""

    # Default frame rate for procedural animations
    default_fps: int = 30

    # Maximum animation duration in seconds
    max_duration: float = 30.0

    # Default loop mode
    default_loop_mode: str = "loop"

    # Parameter limits
    min_speed: float = 0.1
    max_speed: float = 3.0
    min_intensity: float = 0.1
    max_intensity: float = 2.0

    class Config:
        env_prefix = "ANIMATION_"


animation_settings = AnimationSettings()
