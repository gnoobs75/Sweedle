"""Schemas for workflow templates."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class MeshSettings(BaseModel):
    """Settings for mesh generation stage."""
    inference_steps: int = Field(default=30, ge=5, le=100)
    guidance_scale: float = Field(default=5.5, ge=1.0, le=15.0)
    octree_resolution: int = Field(default=256)
    seed: Optional[int] = None


class TextureSettings(BaseModel):
    """Settings for texture generation stage."""
    resolution: int = Field(default=1024)
    camera_views: int = Field(default=4)


class RiggingSettings(BaseModel):
    """Settings for rigging stage."""
    character_type: str = Field(default="auto")  # auto, humanoid, quadruped
    processor: str = Field(default="auto")  # auto, unirig, blender
    auto_decimate: bool = Field(default=True)
    target_vertices: int = Field(default=30000)


class AnimationSettings(BaseModel):
    """Settings for animation stage."""
    presets: List[str] = Field(default_factory=list)  # Preset IDs to apply
    default_speed: float = Field(default=1.0)
    default_intensity: float = Field(default=1.0)


class ExportSettings(BaseModel):
    """Settings for export stage."""
    format: str = Field(default="glb")  # glb, fbx, obj
    draco_compression: bool = Field(default=False)
    generate_lods: bool = Field(default=False)
    lod_levels: List[float] = Field(default_factory=lambda: [0.5, 0.25])
    center_pivot: bool = Field(default=True)
    ground_origin: bool = Field(default=True)


class WorkflowTemplateCreate(BaseModel):
    """Create a new workflow template."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = None

    include_mesh: bool = True
    include_texture: bool = True
    include_rigging: bool = False
    include_animation: bool = False
    include_export: bool = True

    mesh_settings: Optional[MeshSettings] = None
    texture_settings: Optional[TextureSettings] = None
    rigging_settings: Optional[RiggingSettings] = None
    animation_settings: Optional[AnimationSettings] = None
    export_settings: Optional[ExportSettings] = None


class WorkflowTemplateUpdate(BaseModel):
    """Update an existing workflow template."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = None

    include_mesh: Optional[bool] = None
    include_texture: Optional[bool] = None
    include_rigging: Optional[bool] = None
    include_animation: Optional[bool] = None
    include_export: Optional[bool] = None

    mesh_settings: Optional[MeshSettings] = None
    texture_settings: Optional[TextureSettings] = None
    rigging_settings: Optional[RiggingSettings] = None
    animation_settings: Optional[AnimationSettings] = None
    export_settings: Optional[ExportSettings] = None


class WorkflowTemplateResponse(BaseModel):
    """Workflow template response."""
    id: str
    name: str
    description: Optional[str]
    category: Optional[str]

    include_mesh: bool
    include_texture: bool
    include_rigging: bool
    include_animation: bool
    include_export: bool

    mesh_settings: Optional[Dict[str, Any]]
    texture_settings: Optional[Dict[str, Any]]
    rigging_settings: Optional[Dict[str, Any]]
    animation_settings: Optional[Dict[str, Any]]
    export_settings: Optional[Dict[str, Any]]

    is_builtin: bool
    use_count: int
    created_at: datetime
    updated_at: datetime


class WorkflowTemplateList(BaseModel):
    """List of workflow templates."""
    templates: List[WorkflowTemplateResponse]
    total: int


class ApplyTemplateRequest(BaseModel):
    """Request to apply a template to start a workflow."""
    template_id: str
    source_image_path: Optional[str] = None
    asset_name: Optional[str] = None


class ApplyTemplateResponse(BaseModel):
    """Response from applying a template."""
    success: bool
    job_id: Optional[str] = None
    asset_id: Optional[str] = None
    stages: List[str]
    message: str
    error: Optional[str] = None
