"""Pydantic schemas for Assets API."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class TagBase(BaseModel):
    """Base tag schema."""
    name: str = Field(..., min_length=1, max_length=100)
    color: str = Field(default="#6366f1", pattern=r"^#[0-9a-fA-F]{6}$")


class TagCreate(TagBase):
    """Schema for creating a tag."""
    pass


class TagResponse(TagBase):
    """Schema for tag response."""
    id: int

    class Config:
        from_attributes = True


class AssetResponse(BaseModel):
    """Schema for asset response."""
    id: str
    name: str
    description: Optional[str] = None
    source_type: str
    source_image_path: Optional[str] = None
    source_prompt: Optional[str] = None
    generation_params: Optional[dict] = None
    file_path: str
    thumbnail_path: Optional[str] = None
    vertex_count: Optional[int] = None
    face_count: Optional[int] = None
    file_size_bytes: Optional[int] = None
    generation_time_seconds: Optional[float] = None
    status: str
    has_lod: bool = False
    lod_levels: Optional[List[int]] = None
    is_favorite: bool = False
    rating: Optional[int] = None
    tags: List[TagResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AssetListResponse(BaseModel):
    """Schema for paginated asset list."""
    assets: List[AssetResponse]
    total: int
    page: int
    page_size: int


class AssetUpdate(BaseModel):
    """Schema for updating an asset."""
    name: Optional[str] = None
    description: Optional[str] = None
    is_favorite: Optional[bool] = None
    rating: Optional[int] = Field(None, ge=1, le=5)
    tags: Optional[List[int]] = None


class BulkDeleteRequest(BaseModel):
    """Schema for bulk delete request."""
    asset_ids: List[str]


class TagListResponse(BaseModel):
    """Schema for tag list response."""
    tags: List[TagResponse]
