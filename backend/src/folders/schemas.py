"""Pydantic schemas for folders."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class FolderBase(BaseModel):
    """Base folder schema."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    color: str = Field(default="#6366f1", pattern=r"^#[0-9a-fA-F]{6}$")
    icon: str = Field(default="folder")


class FolderCreate(FolderBase):
    """Schema for creating a folder."""
    parent_id: Optional[int] = None


class FolderUpdate(BaseModel):
    """Schema for updating a folder."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    color: Optional[str] = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    icon: Optional[str] = None
    parent_id: Optional[int] = None


class FolderResponse(FolderBase):
    """Schema for folder response."""
    id: int
    parent_id: Optional[int] = None
    asset_count: int = 0
    child_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FolderWithChildren(FolderResponse):
    """Folder response with nested children."""
    children: List["FolderWithChildren"] = []


class FolderTree(BaseModel):
    """Complete folder tree structure."""
    folders: List[FolderWithChildren]
    total_folders: int
    total_assets: int


class MoveAssetsRequest(BaseModel):
    """Request to move assets to a folder."""
    asset_ids: List[str]
    folder_id: Optional[int] = None  # None means move to root


class MoveAssetsResponse(BaseModel):
    """Response for moving assets."""
    success: bool
    moved_count: int
    message: str


class FolderListResponse(BaseModel):
    """Response for listing folders."""
    folders: List[FolderResponse]
    total: int
