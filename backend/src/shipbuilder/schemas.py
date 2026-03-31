"""Pydantic schemas for Ship Builder API."""

from typing import Optional
from pydantic import BaseModel, Field


class ShipGenerateRequest(BaseModel):
    """Request to generate a 3D ship model from a concept image using TRELLIS.2."""

    image_base64: str = Field(..., description="Base64-encoded concept art PNG (with or without data URI prefix)")
    ship_name: str = Field(default="generated-ship", description="Name for the ship model")
    faction: Optional[str] = Field(default=None, description="Faction name (e.g. UNEF, Kristang)")
    class_id: Optional[str] = Field(default=None, description="Fleet class: frigate, destroyer, cruiser, etc.")

    # TRELLIS.2 generation settings
    resolution: int = Field(default=512, description="Output resolution: 512 (~16GB VRAM, ~10s) or 1024 (~22GB VRAM, ~34s)")
    sampler_steps: int = Field(default=12, description="Number of sampler steps for structure and latent generation")
    decimation_target: int = Field(default=30000, description="Target face count for mesh decimation")
    texture_size: int = Field(default=1024, description="PBR texture atlas resolution in pixels")
    seed: Optional[int] = Field(default=None, description="Random seed for reproducibility")
    pbr: bool = Field(default=True, description="Include PBR materials (always true for TRELLIS.2)")


class ShipGenerateResponse(BaseModel):
    """Response from ship generation."""
    ok: bool
    glb_base64: Optional[str] = None
    glb_path: Optional[str] = None
    error: Optional[str] = None
    vertex_count: int = 0
    face_count: int = 0
    generation_time_s: float = 0.0
    texture_applied: bool = False
    vram_peak_gb: float = 0.0
    downgraded: bool = False
    downgrade_reason: Optional[str] = None


class VRAMStatusResponse(BaseModel):
    """VRAM safety status for pre-flight checks."""
    ok: bool
    free_gb: float
    total_gb: float
    allocated_gb: float
    circuit_breaker_tripped: bool
    message: str


# Fleet class configurations matching CoE FLEET_CLASS_CONFIG
FLEET_CLASS_CONFIG = {
    "frigate": {
        "bbox": [5, 1, 1],
        "label": "Frigate",
        "prompt_suffix": "small fast frigate, light armor, forward gun barrels, antenna spines, scout vessel",
    },
    "destroyer": {
        "bbox": [6, 1, 1],
        "label": "Destroyer",
        "prompt_suffix": "destroyer warship, torpedo tubes, heavier armor plating, more weapon turrets, escort vessel",
    },
    "cruiser": {
        "bbox": [7, 2, 1],
        "label": "Cruiser",
        "prompt_suffix": "cruiser warship, wider hull, sensor dome arrays, modular hull sections, balanced firepower",
    },
    "battlecruiser": {
        "bbox": [8, 2, 1],
        "label": "Battlecruiser",
        "prompt_suffix": "battlecruiser, thick overlapping armor plates, heavy weapon turrets, armored command bridge",
    },
    "battleship": {
        "bbox": [9, 3, 2],
        "label": "Battleship",
        "prompt_suffix": "massive battleship, multiple deck levels, dense armor plating, heavy turret batteries, intimidating scale",
    },
    "capital": {
        "bbox": [10, 3, 2],
        "label": "Capital",
        "prompt_suffix": "enormous capital ship, multiple weapon batteries, shield generator domes, fleet command flagship",
    },
    "starcarrier": {
        "bbox": [12, 4, 2],
        "label": "Starcarrier",
        "prompt_suffix": "long starcarrier, exposed flight deck, hangar bays, launch rails, carrier operations, pencil-shaped hull",
    },
}
