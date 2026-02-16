"""Folders API router."""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database import get_session
from src.generation.models import Asset, Folder

from .schemas import (
    FolderCreate,
    FolderListResponse,
    FolderResponse,
    FolderTree,
    FolderUpdate,
    FolderWithChildren,
    MoveAssetsRequest,
    MoveAssetsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/folders", tags=["folders"])


def folder_to_response(folder: Folder, asset_count: int = 0, child_count: int = 0) -> FolderResponse:
    """Convert Folder model to response schema."""
    return FolderResponse(
        id=folder.id,
        name=folder.name,
        description=folder.description,
        color=folder.color,
        icon=folder.icon,
        parent_id=folder.parent_id,
        asset_count=asset_count,
        child_count=child_count,
        created_at=folder.created_at,
        updated_at=folder.updated_at,
    )


@router.get("", response_model=FolderListResponse)
async def list_folders(
    parent_id: Optional[int] = None,
    include_counts: bool = True,
    db: AsyncSession = Depends(get_session),
):
    """List folders, optionally filtered by parent."""
    # Build query
    query = select(Folder)

    if parent_id is not None:
        query = query.where(Folder.parent_id == parent_id)
    else:
        # Get root folders only
        query = query.where(Folder.parent_id.is_(None))

    query = query.order_by(Folder.name)

    result = await db.execute(query)
    folders = result.scalars().all()

    # Get counts if requested
    folder_responses = []
    for folder in folders:
        asset_count = 0
        child_count = 0

        if include_counts:
            # Count assets in folder
            count_query = select(func.count(Asset.id)).where(Asset.folder_id == folder.id)
            asset_result = await db.execute(count_query)
            asset_count = asset_result.scalar() or 0

            # Count child folders
            child_query = select(func.count(Folder.id)).where(Folder.parent_id == folder.id)
            child_result = await db.execute(child_query)
            child_count = child_result.scalar() or 0

        folder_responses.append(folder_to_response(folder, asset_count, child_count))

    # Get total count
    total_query = select(func.count(Folder.id))
    if parent_id is not None:
        total_query = total_query.where(Folder.parent_id == parent_id)
    else:
        total_query = total_query.where(Folder.parent_id.is_(None))

    total_result = await db.execute(total_query)
    total = total_result.scalar() or 0

    return FolderListResponse(folders=folder_responses, total=total)


@router.get("/tree", response_model=FolderTree)
async def get_folder_tree(
    db: AsyncSession = Depends(get_session),
):
    """Get complete folder tree structure."""
    # Get all folders
    query = select(Folder).order_by(Folder.name)
    result = await db.execute(query)
    all_folders = result.scalars().all()

    # Build folder lookup and count assets
    folder_map = {}
    for folder in all_folders:
        # Count assets
        count_query = select(func.count(Asset.id)).where(Asset.folder_id == folder.id)
        count_result = await db.execute(count_query)
        asset_count = count_result.scalar() or 0

        folder_map[folder.id] = {
            "folder": folder,
            "asset_count": asset_count,
            "children": [],
        }

    # Build tree structure
    root_folders = []
    for folder_id, data in folder_map.items():
        folder = data["folder"]
        if folder.parent_id is None:
            root_folders.append(data)
        elif folder.parent_id in folder_map:
            folder_map[folder.parent_id]["children"].append(data)

    def build_folder_with_children(data) -> FolderWithChildren:
        folder = data["folder"]
        children = [build_folder_with_children(child) for child in data["children"]]
        return FolderWithChildren(
            id=folder.id,
            name=folder.name,
            description=folder.description,
            color=folder.color,
            icon=folder.icon,
            parent_id=folder.parent_id,
            asset_count=data["asset_count"],
            child_count=len(children),
            created_at=folder.created_at,
            updated_at=folder.updated_at,
            children=children,
        )

    tree = [build_folder_with_children(data) for data in root_folders]

    # Get totals
    total_folders = len(all_folders)
    total_assets_query = select(func.count(Asset.id))
    total_assets_result = await db.execute(total_assets_query)
    total_assets = total_assets_result.scalar() or 0

    return FolderTree(
        folders=tree,
        total_folders=total_folders,
        total_assets=total_assets,
    )


@router.get("/{folder_id}", response_model=FolderResponse)
async def get_folder(
    folder_id: int,
    db: AsyncSession = Depends(get_session),
):
    """Get a specific folder by ID."""
    query = select(Folder).where(Folder.id == folder_id)
    result = await db.execute(query)
    folder = result.scalar_one_or_none()

    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    # Count assets
    count_query = select(func.count(Asset.id)).where(Asset.folder_id == folder.id)
    count_result = await db.execute(count_query)
    asset_count = count_result.scalar() or 0

    # Count children
    child_query = select(func.count(Folder.id)).where(Folder.parent_id == folder.id)
    child_result = await db.execute(child_query)
    child_count = child_result.scalar() or 0

    return folder_to_response(folder, asset_count, child_count)


@router.post("", response_model=FolderResponse)
async def create_folder(
    request: FolderCreate,
    db: AsyncSession = Depends(get_session),
):
    """Create a new folder."""
    # Validate parent exists if specified
    if request.parent_id is not None:
        parent_query = select(Folder).where(Folder.id == request.parent_id)
        parent_result = await db.execute(parent_query)
        parent = parent_result.scalar_one_or_none()

        if not parent:
            raise HTTPException(status_code=404, detail="Parent folder not found")

    # Check for duplicate name in same parent
    name_query = select(Folder).where(
        Folder.name == request.name,
        Folder.parent_id == request.parent_id
    )
    name_result = await db.execute(name_query)
    existing = name_result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Folder '{request.name}' already exists in this location"
        )

    # Create folder
    folder = Folder(
        name=request.name,
        description=request.description,
        color=request.color,
        icon=request.icon,
        parent_id=request.parent_id,
    )

    db.add(folder)
    await db.commit()
    await db.refresh(folder)

    logger.info(f"Created folder: {folder.name} (id={folder.id})")

    return folder_to_response(folder, 0, 0)


@router.patch("/{folder_id}", response_model=FolderResponse)
async def update_folder(
    folder_id: int,
    request: FolderUpdate,
    db: AsyncSession = Depends(get_session),
):
    """Update a folder."""
    query = select(Folder).where(Folder.id == folder_id)
    result = await db.execute(query)
    folder = result.scalar_one_or_none()

    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    # Validate new parent if changing
    if request.parent_id is not None and request.parent_id != folder.parent_id:
        # Cannot move folder into itself or its children
        if request.parent_id == folder_id:
            raise HTTPException(status_code=400, detail="Cannot move folder into itself")

        # Check parent exists
        parent_query = select(Folder).where(Folder.id == request.parent_id)
        parent_result = await db.execute(parent_query)
        parent = parent_result.scalar_one_or_none()

        if not parent:
            raise HTTPException(status_code=404, detail="Parent folder not found")

        # Check for circular reference
        current_parent = parent
        while current_parent is not None:
            if current_parent.id == folder_id:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot create circular folder structure"
                )
            if current_parent.parent_id:
                parent_query = select(Folder).where(Folder.id == current_parent.parent_id)
                parent_result = await db.execute(parent_query)
                current_parent = parent_result.scalar_one_or_none()
            else:
                current_parent = None

    # Check for duplicate name if changing name or parent
    new_name = request.name if request.name is not None else folder.name
    new_parent = request.parent_id if request.parent_id is not None else folder.parent_id

    if new_name != folder.name or new_parent != folder.parent_id:
        name_query = select(Folder).where(
            Folder.name == new_name,
            Folder.parent_id == new_parent,
            Folder.id != folder_id
        )
        name_result = await db.execute(name_query)
        existing = name_result.scalar_one_or_none()

        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Folder '{new_name}' already exists in this location"
            )

    # Update fields
    if request.name is not None:
        folder.name = request.name
    if request.description is not None:
        folder.description = request.description
    if request.color is not None:
        folder.color = request.color
    if request.icon is not None:
        folder.icon = request.icon
    if request.parent_id is not None:
        folder.parent_id = request.parent_id

    await db.commit()
    await db.refresh(folder)

    # Get counts
    count_query = select(func.count(Asset.id)).where(Asset.folder_id == folder.id)
    count_result = await db.execute(count_query)
    asset_count = count_result.scalar() or 0

    child_query = select(func.count(Folder.id)).where(Folder.parent_id == folder.id)
    child_result = await db.execute(child_query)
    child_count = child_result.scalar() or 0

    logger.info(f"Updated folder: {folder.name} (id={folder.id})")

    return folder_to_response(folder, asset_count, child_count)


@router.delete("/{folder_id}")
async def delete_folder(
    folder_id: int,
    move_assets_to: Optional[int] = None,
    db: AsyncSession = Depends(get_session),
):
    """Delete a folder. Optionally move assets to another folder."""
    query = select(Folder).where(Folder.id == folder_id)
    result = await db.execute(query)
    folder = result.scalar_one_or_none()

    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    # Move assets if requested
    if move_assets_to is not None:
        # Validate target folder
        target_query = select(Folder).where(Folder.id == move_assets_to)
        target_result = await db.execute(target_query)
        target = target_result.scalar_one_or_none()

        if not target:
            raise HTTPException(status_code=404, detail="Target folder not found")

        # Move assets
        await db.execute(
            Asset.__table__.update()
            .where(Asset.folder_id == folder_id)
            .values(folder_id=move_assets_to)
        )
    else:
        # Move assets to root (no folder)
        await db.execute(
            Asset.__table__.update()
            .where(Asset.folder_id == folder_id)
            .values(folder_id=None)
        )

    # Delete folder (children will be cascade deleted)
    await db.delete(folder)
    await db.commit()

    logger.info(f"Deleted folder: {folder.name} (id={folder_id})")

    return {"success": True, "message": f"Folder '{folder.name}' deleted"}


@router.post("/move-assets", response_model=MoveAssetsResponse)
async def move_assets(
    request: MoveAssetsRequest,
    db: AsyncSession = Depends(get_session),
):
    """Move assets to a folder (or root if folder_id is None)."""
    # Validate target folder if specified
    if request.folder_id is not None:
        folder_query = select(Folder).where(Folder.id == request.folder_id)
        folder_result = await db.execute(folder_query)
        folder = folder_result.scalar_one_or_none()

        if not folder:
            raise HTTPException(status_code=404, detail="Target folder not found")

    # Update assets
    moved_count = 0
    for asset_id in request.asset_ids:
        asset_query = select(Asset).where(Asset.id == asset_id)
        asset_result = await db.execute(asset_query)
        asset = asset_result.scalar_one_or_none()

        if asset:
            asset.folder_id = request.folder_id
            moved_count += 1

    await db.commit()

    folder_name = "root" if request.folder_id is None else f"folder {request.folder_id}"
    logger.info(f"Moved {moved_count} assets to {folder_name}")

    return MoveAssetsResponse(
        success=True,
        moved_count=moved_count,
        message=f"Moved {moved_count} asset(s) to {folder_name}",
    )
