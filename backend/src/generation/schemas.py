"""Pydantic schemas for generation API."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class GenerationMode(str, Enum):
    """Generation quality modes."""
    FAST = "fast"
    STANDARD = "standard"
    QUALITY = "quality"


class OutputFormat(str, Enum):
    """Output file formats."""
    GLB = "glb"
    OBJ = "obj"
    PLY = "ply"
    STL = "stl"


class JobStatus(str, Enum):
    """Job status values."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GenerationType(str, Enum):
    """Type of generation."""
    IMAGE_TO_3D = "image_to_3d"
    TEXT_TO_3D = "text_to_3d"


# Request schemas

class GenerationParameters(BaseModel):
    """Generation parameters for API requests."""
    inference_steps: int = Field(30, ge=5, le=100, description="Number of diffusion steps")
    guidance_scale: float = Field(5.5, ge=1.0, le=15.0, description="Guidance scale")
    octree_resolution: int = Field(256, description="Mesh resolution (128, 256, 384, 512)")
    seed: Optional[int] = Field(None, ge=0, le=2147483647, description="Random seed")
    generate_texture: bool = Field(True, description="Generate PBR texture")
    face_count: Optional[int] = Field(None, ge=100, le=1000000, description="Max face count")
    output_format: OutputFormat = Field(OutputFormat.GLB, description="Output format")
    mode: GenerationMode = Field(GenerationMode.STANDARD, description="Quality preset")


class ImageToThreeDRequest(BaseModel):
    """Request for image-to-3D generation via form data."""
    name: Optional[str] = Field(None, max_length=255, description="Asset name")
    parameters: GenerationParameters = Field(default_factory=GenerationParameters)
    project_id: Optional[str] = Field(None, description="Project to add asset to")
    tags: list[str] = Field(default_factory=list, description="Tags to apply")


class TextToThreeDRequest(BaseModel):
    """Request for text-to-3D generation."""
    prompt: str = Field(..., min_length=3, max_length=500, description="Text prompt")
    name: Optional[str] = Field(None, max_length=255, description="Asset name")
    parameters: GenerationParameters = Field(default_factory=GenerationParameters)
    project_id: Optional[str] = Field(None, description="Project to add asset to")
    tags: list[str] = Field(default_factory=list, description="Tags to apply")


class BatchGenerationItem(BaseModel):
    """Single item in batch generation request."""
    image_path: str = Field(..., description="Path to image file")
    name: Optional[str] = Field(None, description="Asset name")
    parameters: GenerationParameters = Field(default_factory=GenerationParameters)


class BatchGenerationRequest(BaseModel):
    """Request for batch generation."""
    items: list[BatchGenerationItem] = Field(..., min_length=1, max_length=100)
    project_id: Optional[str] = Field(None, description="Project to add assets to")
    tags: list[str] = Field(default_factory=list, description="Tags to apply to all")


# Response schemas

class GenerationResponse(BaseModel):
    """Response after submitting generation request."""
    job_id: str
    asset_id: str
    status: JobStatus
    message: str
    queue_position: Optional[int] = None


class JobProgress(BaseModel):
    """Progress update for a job."""
    progress: float = Field(..., ge=0.0, le=1.0)
    stage: str
    message: str


class JobStatusResponse(BaseModel):
    """Detailed job status response."""
    job_id: str
    asset_id: Optional[str]
    status: JobStatus
    progress: float
    stage: str
    message: Optional[str]
    error: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


class GenerationResultResponse(BaseModel):
    """Response with generation results."""
    job_id: str
    asset_id: str
    success: bool
    mesh_url: Optional[str]
    thumbnail_url: Optional[str]
    vertex_count: int
    face_count: int
    generation_time: float
    parameters: dict[str, Any]
    error: Optional[str]


class QueueStatusResponse(BaseModel):
    """Queue status response."""
    queue_size: int
    current_job_id: Optional[str]
    pending_count: int
    processing_count: int
    completed_count: int
