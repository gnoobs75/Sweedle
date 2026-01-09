"""
Pydantic schemas for rigging operations.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field


class CharacterType(str, Enum):
    """Supported character types for rigging."""
    HUMANOID = "humanoid"
    QUADRUPED = "quadruped"
    AUTO = "auto"


class RiggingProcessor(str, Enum):
    """Available rigging processors."""
    UNIRIG = "unirig"
    BLENDER = "blender"
    AUTO = "auto"


class JobPriority(str, Enum):
    """Job priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class RiggingStatus(str, Enum):
    """Rigging job status."""
    PENDING = "pending"
    DETECTING = "detecting"
    RIGGING = "rigging"
    WEIGHTING = "weighting"
    EXPORTING = "exporting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============================================================================
# Skeleton Data Structures
# ============================================================================

class BoneData(BaseModel):
    """Individual bone data."""
    name: str = Field(..., description="Bone name (e.g., 'Hips', 'Spine')")
    parent: Optional[str] = Field(None, description="Parent bone name, null for root")
    head_position: tuple[float, float, float] = Field(..., description="Head position (x, y, z)")
    tail_position: tuple[float, float, float] = Field(..., description="Tail position (x, y, z)")
    rotation: tuple[float, float, float, float] = Field(
        default=(0.0, 0.0, 0.0, 1.0),
        description="Rotation quaternion (x, y, z, w)"
    )
    scale: tuple[float, float, float] = Field(
        default=(1.0, 1.0, 1.0),
        description="Scale (x, y, z)"
    )
    connected: bool = Field(default=False, description="Whether bone is connected to parent")
    deform: bool = Field(default=True, description="Whether bone deforms mesh")


class SkeletonData(BaseModel):
    """Complete skeleton structure."""
    root_bone: str = Field(..., description="Name of the root bone")
    bones: list[BoneData] = Field(..., description="List of all bones")
    character_type: CharacterType = Field(..., description="Detected or specified character type")
    bone_count: int = Field(..., description="Total number of bones")
    bind_pose: Optional[dict[str, list[float]]] = Field(
        None,
        description="Bind pose matrices per bone (4x4 flattened)"
    )

    @classmethod
    def from_bones(cls, bones: list[BoneData], character_type: CharacterType) -> "SkeletonData":
        """Create SkeletonData from a list of bones."""
        root_bones = [b for b in bones if b.parent is None]
        if not root_bones:
            raise ValueError("No root bone found (bone with parent=None)")
        return cls(
            root_bone=root_bones[0].name,
            bones=bones,
            character_type=character_type,
            bone_count=len(bones),
        )


class WeightData(BaseModel):
    """Vertex weight assignment."""
    vertex_index: int = Field(..., description="Vertex index in mesh")
    bone_weights: dict[str, float] = Field(
        ...,
        description="Bone name to weight mapping (weights sum to 1.0)"
    )


class SkinningData(BaseModel):
    """Complete skinning information for a mesh."""
    vertex_count: int = Field(..., description="Number of vertices")
    weights: list[WeightData] = Field(..., description="Per-vertex weight data")
    max_influences: int = Field(default=4, description="Max bone influences per vertex")


# ============================================================================
# API Request/Response Schemas
# ============================================================================

class AutoRigRequest(BaseModel):
    """Request to auto-rig an asset."""
    asset_id: str = Field(..., description="ID of the asset to rig")
    character_type: CharacterType = Field(
        default=CharacterType.AUTO,
        description="Character type (auto-detect if not specified)"
    )
    processor: RiggingProcessor = Field(
        default=RiggingProcessor.AUTO,
        description="Rigging processor to use"
    )
    priority: JobPriority = Field(
        default=JobPriority.NORMAL,
        description="Job priority"
    )


class AutoRigResponse(BaseModel):
    """Response after submitting auto-rig request."""
    job_id: str = Field(..., description="Unique job identifier")
    asset_id: str = Field(..., description="Asset being rigged")
    status: str = Field(..., description="Initial job status")
    message: str = Field(..., description="Status message")
    queue_position: Optional[int] = Field(None, description="Position in queue")


class RiggingJobStatus(BaseModel):
    """Current status of a rigging job."""
    job_id: str = Field(..., description="Job identifier")
    asset_id: str = Field(..., description="Asset being rigged")
    status: RiggingStatus = Field(..., description="Current status")
    progress: float = Field(default=0.0, description="Progress 0.0-1.0")
    stage: str = Field(default="", description="Current processing stage")
    detected_type: Optional[CharacterType] = Field(None, description="Detected character type")
    processor_used: Optional[RiggingProcessor] = Field(None, description="Processor being used")
    error: Optional[str] = Field(None, description="Error message if failed")
    created_at: datetime = Field(..., description="Job creation time")
    started_at: Optional[datetime] = Field(None, description="Processing start time")
    completed_at: Optional[datetime] = Field(None, description="Completion time")


class DetectTypeRequest(BaseModel):
    """Request to detect character type."""
    asset_id: str = Field(..., description="Asset ID to analyze")


class DetectTypeResponse(BaseModel):
    """Response with detected character type."""
    asset_id: str
    detected_type: CharacterType
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    analysis: Optional[dict[str, Any]] = Field(None, description="Analysis details")


class SkeletonResponse(BaseModel):
    """Response containing skeleton data."""
    asset_id: str
    skeleton: SkeletonData
    rigged_mesh_path: str
    processor_used: RiggingProcessor
    created_at: datetime


class SkeletonTemplateInfo(BaseModel):
    """Information about a skeleton template."""
    name: str = Field(..., description="Template name")
    character_type: CharacterType
    bone_count: int
    description: str
    preview_url: Optional[str] = None


class TemplateListResponse(BaseModel):
    """List of available skeleton templates."""
    templates: list[SkeletonTemplateInfo]


# ============================================================================
# Processing Results
# ============================================================================

class RiggingResult(BaseModel):
    """Result of rigging operation."""
    success: bool = Field(..., description="Whether rigging succeeded")
    skeleton: Optional[SkeletonData] = Field(None, description="Generated skeleton")
    skinning: Optional[SkinningData] = Field(None, description="Skinning weights")
    rigged_mesh_path: Optional[str] = Field(None, description="Path to rigged mesh file")
    detected_type: Optional[CharacterType] = Field(None, description="Detected character type")
    processor_used: Optional[RiggingProcessor] = Field(None, description="Processor that was used")
    processing_time: float = Field(default=0.0, description="Processing time in seconds")
    vertex_count: int = Field(default=0, description="Mesh vertex count")
    error: Optional[str] = Field(None, description="Error message if failed")


class CharacterAnalysis(BaseModel):
    """Analysis results for character type detection."""
    bounding_box: tuple[tuple[float, float, float], tuple[float, float, float]]
    dimensions: tuple[float, float, float]  # width, height, depth
    height_to_width_ratio: float
    center_of_mass: tuple[float, float, float]
    vertex_count: int
    is_humanoid_likely: bool
    is_quadruped_likely: bool
    confidence: float
