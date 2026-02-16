"""Mesh editing schemas."""

from typing import Optional, List
from pydantic import BaseModel, Field


class MeshInfo(BaseModel):
    """Mesh information."""
    vertexCount: int
    faceCount: int
    hasNormals: bool
    hasUvs: bool
    isWatertight: bool
    boundingBoxMin: List[float]
    boundingBoxMax: List[float]
    centerOfMass: List[float]


class SmoothMeshRequest(BaseModel):
    """Request for mesh smoothing."""
    asset_id: str
    iterations: int = Field(default=1, ge=1, le=10)
    lambda_factor: float = Field(default=0.5, ge=0.0, le=1.0)


class SmoothMeshResponse(BaseModel):
    """Response for mesh smoothing."""
    success: bool
    asset_id: str
    original_vertex_count: int
    new_vertex_count: int
    message: str
    error: Optional[str] = None


class RepairMeshRequest(BaseModel):
    """Request for mesh repair."""
    asset_id: str
    fill_holes: bool = True
    fix_normals: bool = True
    remove_degenerates: bool = True
    merge_duplicates: bool = True


class RepairMeshResponse(BaseModel):
    """Response for mesh repair."""
    success: bool
    asset_id: str
    holes_filled: int
    faces_removed: int
    vertices_merged: int
    normals_fixed: bool
    message: str
    error: Optional[str] = None


class DecimateMeshRequest(BaseModel):
    """Request for mesh decimation."""
    asset_id: str
    target_faces: Optional[int] = None
    ratio: Optional[float] = Field(default=None, ge=0.01, le=1.0)


class DecimateMeshResponse(BaseModel):
    """Response for mesh decimation."""
    success: bool
    asset_id: str
    original_faces: int
    new_faces: int
    reduction_percent: float
    message: str
    error: Optional[str] = None


class CenterPivotRequest(BaseModel):
    """Request for centering pivot."""
    asset_id: str
    center_x: bool = True
    center_y: bool = False  # Usually keep Y at bottom
    center_z: bool = True


class CenterPivotResponse(BaseModel):
    """Response for centering pivot."""
    success: bool
    asset_id: str
    offset_applied: List[float]
    message: str
    error: Optional[str] = None


class ScaleMeshRequest(BaseModel):
    """Request for scaling mesh."""
    asset_id: str
    scale_factor: float = Field(ge=0.001, le=1000.0)
    uniform: bool = True
    scale_x: Optional[float] = None
    scale_y: Optional[float] = None
    scale_z: Optional[float] = None


class ScaleMeshResponse(BaseModel):
    """Response for scaling mesh."""
    success: bool
    asset_id: str
    scale_applied: List[float]
    message: str
    error: Optional[str] = None


class MeshInfoRequest(BaseModel):
    """Request for mesh info."""
    asset_id: str


class MeshInfoResponse(BaseModel):
    """Response for mesh info."""
    success: bool
    asset_id: str
    info: MeshInfo
    error: Optional[str] = None


class GenerateCollisionRequest(BaseModel):
    """Request for collision mesh generation."""
    asset_id: str
    method: str = Field(default="convex_hull", pattern="^(convex_hull|simplified|box|capsule|sphere)$")
    simplification_ratio: Optional[float] = Field(default=0.1, ge=0.01, le=0.5)


class CollisionMeshInfo(BaseModel):
    """Information about generated collision mesh."""
    method: str
    vertex_count: int
    face_count: int
    file_path: str
    file_size_bytes: int


class GenerateCollisionResponse(BaseModel):
    """Response for collision mesh generation."""
    success: bool
    asset_id: str
    collision: Optional[CollisionMeshInfo] = None
    message: str
    error: Optional[str] = None
