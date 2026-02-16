"""Schemas for asset variants and version history."""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class VariantGroupCreate(BaseModel):
    """Create a new variant group."""
    name: str
    description: Optional[str] = None


class VariantGroupResponse(BaseModel):
    """Basic variant group response."""
    id: str
    name: str
    description: Optional[str]
    source_type: str
    source_image_path: Optional[str]
    source_prompt: Optional[str]
    primary_asset_id: Optional[str]
    variant_count: int
    created_at: datetime


class VariantAssetInfo(BaseModel):
    """Asset info within a variant group."""
    id: str
    name: str
    thumbnail_path: Optional[str]
    generation_seed: Optional[int]
    variant_index: Optional[int]
    vertex_count: Optional[int]
    face_count: Optional[int]
    is_primary: bool
    created_at: datetime


class VariantGroupDetail(BaseModel):
    """Detailed variant group with all variants."""
    id: str
    name: str
    description: Optional[str]
    source_type: str
    source_image_path: Optional[str]
    source_prompt: Optional[str]
    primary_asset_id: Optional[str]
    variants: List[VariantAssetInfo]
    created_at: datetime
    updated_at: datetime


class GenerateVariantsRequest(BaseModel):
    """Request to generate multiple variants."""
    asset_id: str  # Source asset to create variants from
    count: int = Field(default=4, ge=1, le=10)  # Number of variants to generate
    name_prefix: Optional[str] = None  # Optional name prefix for variants


class GenerateVariantsResponse(BaseModel):
    """Response for variant generation."""
    success: bool
    variant_group_id: str
    job_ids: List[str]  # Generation job IDs for each variant
    message: str
    error: Optional[str] = None


class AssetVersionResponse(BaseModel):
    """Single version history entry."""
    id: str
    asset_id: str
    version_number: int
    change_type: str
    change_description: Optional[str]
    file_path: str
    thumbnail_path: Optional[str]
    vertex_count: Optional[int]
    face_count: Optional[int]
    file_size_bytes: Optional[int]
    created_at: datetime


class VersionHistoryResponse(BaseModel):
    """Full version history for an asset."""
    asset_id: str
    asset_name: str
    current_version: int
    versions: List[AssetVersionResponse]


class CreateVersionRequest(BaseModel):
    """Request to create a version snapshot."""
    asset_id: str
    change_type: str = Field(pattern="^(mesh_edit|texture_change|rigging|animation|manual)$")
    change_description: Optional[str] = None


class CreateVersionResponse(BaseModel):
    """Response for version creation."""
    success: bool
    version_id: str
    version_number: int
    message: str
    error: Optional[str] = None


class RestoreVersionRequest(BaseModel):
    """Request to restore a specific version."""
    version_id: str
    create_backup: bool = True  # Create a backup of current state before restore


class RestoreVersionResponse(BaseModel):
    """Response for version restoration."""
    success: bool
    restored_version: int
    backup_version_id: Optional[str]  # ID of backup version if created
    message: str
    error: Optional[str] = None


class SetPrimaryVariantRequest(BaseModel):
    """Request to set primary variant in a group."""
    variant_group_id: str
    asset_id: str
