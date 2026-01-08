"""Generation configuration and parameter schemas."""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class GenerationMode(str, Enum):
    """Generation quality/speed modes."""
    FAST = "fast"        # Fewer steps, lower quality
    STANDARD = "standard"  # Balanced
    QUALITY = "quality"   # More steps, higher quality


class OutputFormat(str, Enum):
    """Supported output formats."""
    GLB = "glb"
    OBJ = "obj"
    PLY = "ply"
    STL = "stl"


@dataclass
class TextureConfig:
    """Configuration for texture generation."""
    enabled: bool = True
    max_num_views: int = 6
    resolution: int = 512


@dataclass
class GenerationConfig:
    """Configuration for 3D generation pipeline.

    Attributes:
        inference_steps: Number of diffusion steps (5-100). More = higher quality.
        guidance_scale: How closely to follow the input (1.0-15.0).
        octree_resolution: Mesh resolution (128, 256, 384, 512).
        seed: Random seed for reproducibility. None = random.
        texture: Texture generation settings.
        face_count: Optional max face count for simplification.
        output_format: Output file format.
        mode: Generation mode preset.
    """
    # Shape generation parameters
    inference_steps: int = 30
    guidance_scale: float = 5.5
    octree_resolution: int = 256
    seed: Optional[int] = None

    # Texture settings
    texture: TextureConfig = field(default_factory=TextureConfig)

    # Post-processing
    face_count: Optional[int] = None
    remove_floaters: bool = True

    # Output
    output_format: OutputFormat = OutputFormat.GLB

    # Preset mode
    mode: GenerationMode = GenerationMode.STANDARD

    def __post_init__(self):
        """Apply mode presets if using non-standard mode."""
        if self.mode == GenerationMode.FAST:
            self.inference_steps = min(self.inference_steps, 10)
            self.octree_resolution = min(self.octree_resolution, 128)
        elif self.mode == GenerationMode.QUALITY:
            self.inference_steps = max(self.inference_steps, 50)
            self.octree_resolution = max(self.octree_resolution, 384)

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "inference_steps": self.inference_steps,
            "guidance_scale": self.guidance_scale,
            "octree_resolution": self.octree_resolution,
            "seed": self.seed,
            "texture_enabled": self.texture.enabled,
            "texture_resolution": self.texture.resolution,
            "face_count": self.face_count,
            "output_format": self.output_format.value,
            "mode": self.mode.value,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GenerationConfig":
        """Create from dictionary."""
        texture = TextureConfig(
            enabled=data.get("texture_enabled", True),
            resolution=data.get("texture_resolution", 512),
        )
        return cls(
            inference_steps=data.get("inference_steps", 30),
            guidance_scale=data.get("guidance_scale", 5.5),
            octree_resolution=data.get("octree_resolution", 256),
            seed=data.get("seed"),
            texture=texture,
            face_count=data.get("face_count"),
            output_format=OutputFormat(data.get("output_format", "glb")),
            mode=GenerationMode(data.get("mode", "standard")),
        )


# Preset configurations
PRESETS = {
    "fast": GenerationConfig(
        mode=GenerationMode.FAST,
        inference_steps=5,
        octree_resolution=128,
        texture=TextureConfig(enabled=False),
    ),
    "standard": GenerationConfig(
        mode=GenerationMode.STANDARD,
        inference_steps=30,
        octree_resolution=256,
    ),
    "quality": GenerationConfig(
        mode=GenerationMode.QUALITY,
        inference_steps=50,
        octree_resolution=384,
    ),
    "game_ready": GenerationConfig(
        mode=GenerationMode.STANDARD,
        inference_steps=30,
        octree_resolution=256,
        face_count=50000,
    ),
}
