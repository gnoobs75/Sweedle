"""Assets API router."""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import desc, asc, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select

from src.config import settings
from src.database import get_session
from src.generation.models import Asset, Tag, asset_tags, AssetStatus, GenerationType
from src.assets.schemas import (
    AssetListResponse,
    AssetResponse,
    AssetUpdate,
    BulkDeleteRequest,
    TagCreate,
    TagListResponse,
    TagResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def asset_to_response(asset: Asset) -> AssetResponse:
    """Convert Asset ORM model to response schema."""
    return AssetResponse(
        id=asset.id,
        name=asset.name,
        description=asset.description,
        source_type=asset.source_type.value if asset.source_type else "image_to_3d",
        source_image_path=asset.source_image_path,
        source_prompt=asset.source_prompt,
        generation_params=asset.generation_params,
        file_path=asset.file_path,
        thumbnail_path=asset.thumbnail_path,
        vertex_count=asset.vertex_count,
        face_count=asset.face_count,
        file_size_bytes=asset.file_size_bytes,
        generation_time_seconds=asset.generation_time_seconds,
        status=asset.status.value if asset.status else "pending",
        has_lod=asset.has_lod or False,
        lod_levels=asset.lod_levels,
        is_favorite=asset.is_favorite or False,
        rating=asset.rating,
        tags=[TagResponse(id=t.id, name=t.name, color=t.color) for t in asset.tags],
        created_at=asset.created_at,
        updated_at=asset.updated_at,
    )


@router.get("", response_model=AssetListResponse)
async def list_assets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    tags: Optional[str] = None,
    source_type: Optional[str] = None,
    has_lod: Optional[bool] = None,
    is_favorite: Optional[bool] = None,
    sort_by: str = Query("created", pattern="^(created|name|size|rating)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_session),
):
    """List assets with filters and pagination."""
    try:
        # Build base query
        query = select(Asset).options(selectinload(Asset.tags))
        count_query = select(func.count(Asset.id))

        # Apply filters to both queries
        if search:
            search_filter = f"%{search}%"
            search_cond = or_(
                Asset.name.ilike(search_filter),
                Asset.description.ilike(search_filter),
            )
            query = query.where(search_cond)
            count_query = count_query.where(search_cond)

        if source_type and source_type != "all":
            try:
                gen_type = GenerationType(source_type)
                query = query.where(Asset.source_type == gen_type)
                count_query = count_query.where(Asset.source_type == gen_type)
            except ValueError:
                pass

        if has_lod is not None:
            query = query.where(Asset.has_lod == has_lod)
            count_query = count_query.where(Asset.has_lod == has_lod)

        if is_favorite is not None:
            query = query.where(Asset.is_favorite == is_favorite)
            count_query = count_query.where(Asset.is_favorite == is_favorite)

        # Apply sorting
        sort_column_map = {
            "created": Asset.created_at,
            "name": Asset.name,
            "size": Asset.file_size_bytes,
            "rating": Asset.rating,
        }
        sort_column = sort_column_map.get(sort_by, Asset.created_at)
        order_func = desc if sort_order == "desc" else asc
        query = query.order_by(order_func(sort_column))

        # Get total count
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Execute query
        result = await db.execute(query)
        assets = result.scalars().unique().all()

        return AssetListResponse(
            assets=[asset_to_response(a) for a in assets],
            total=total,
            page=page,
            page_size=page_size,
        )
    except Exception as e:
        logger.error(f"Error listing assets: {e}")
        raise HTTPException(500, f"Error listing assets: {str(e)}")


@router.get("/tags", response_model=TagListResponse)
async def list_tags(db: AsyncSession = Depends(get_session)):
    """List all tags."""
    try:
        result = await db.execute(select(Tag).order_by(Tag.name))
        tags = result.scalars().all()
        return TagListResponse(
            tags=[TagResponse(id=t.id, name=t.name, color=t.color) for t in tags]
        )
    except Exception as e:
        logger.error(f"Error listing tags: {e}")
        raise HTTPException(500, f"Error listing tags: {str(e)}")


@router.post("/tags", response_model=TagResponse)
async def create_tag(
    tag_data: TagCreate,
    db: AsyncSession = Depends(get_session),
):
    """Create a new tag."""
    # Check for duplicate
    result = await db.execute(select(Tag).where(Tag.name == tag_data.name))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(400, f"Tag '{tag_data.name}' already exists")

    tag = Tag(name=tag_data.name, color=tag_data.color)
    db.add(tag)
    await db.flush()
    await db.refresh(tag)

    return TagResponse(id=tag.id, name=tag.name, color=tag.color)


@router.delete("/tags/{tag_id}")
async def delete_tag(
    tag_id: int,
    db: AsyncSession = Depends(get_session),
):
    """Delete a tag."""
    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = result.scalar_one_or_none()
    if not tag:
        raise HTTPException(404, "Tag not found")

    await db.delete(tag)
    return {"message": "Tag deleted", "tag_id": tag_id}


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Get a single asset by ID."""
    result = await db.execute(
        select(Asset)
        .options(selectinload(Asset.tags))
        .where(Asset.id == asset_id)
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(404, "Asset not found")

    return asset_to_response(asset)


@router.patch("/{asset_id}", response_model=AssetResponse)
async def update_asset(
    asset_id: str,
    updates: AssetUpdate,
    db: AsyncSession = Depends(get_session),
):
    """Update an asset."""
    result = await db.execute(
        select(Asset)
        .options(selectinload(Asset.tags))
        .where(Asset.id == asset_id)
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(404, "Asset not found")

    # Apply updates
    if updates.name is not None:
        asset.name = updates.name
    if updates.description is not None:
        asset.description = updates.description
    if updates.is_favorite is not None:
        asset.is_favorite = updates.is_favorite
    if updates.rating is not None:
        asset.rating = updates.rating

    # Handle tag updates
    if updates.tags is not None:
        # Get tags by IDs
        tag_result = await db.execute(select(Tag).where(Tag.id.in_(updates.tags)))
        new_tags = tag_result.scalars().all()
        asset.tags = list(new_tags)

    await db.flush()
    await db.refresh(asset)

    return asset_to_response(asset)


@router.delete("/{asset_id}")
async def delete_asset(
    asset_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Delete an asset."""
    result = await db.execute(select(Asset).where(Asset.id == asset_id))
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(404, "Asset not found")

    # TODO: Also delete files from disk

    await db.delete(asset)
    return {"message": "Asset deleted", "asset_id": asset_id}


@router.post("/bulk-delete")
async def bulk_delete_assets(
    request: BulkDeleteRequest,
    db: AsyncSession = Depends(get_session),
):
    """Delete multiple assets."""
    deleted_count = 0
    for asset_id in request.asset_ids:
        result = await db.execute(select(Asset).where(Asset.id == asset_id))
        asset = result.scalar_one_or_none()
        if asset:
            await db.delete(asset)
            deleted_count += 1

    return {"message": f"Deleted {deleted_count} assets", "deleted_count": deleted_count}


@router.get("/{asset_id}/download")
async def download_asset(
    asset_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Download an asset file."""
    result = await db.execute(select(Asset).where(Asset.id == asset_id))
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(404, "Asset not found")

    # Build the correct file path: generated/{asset_id}/{asset_id}.glb
    file_path = settings.GENERATED_DIR / asset_id / f"{asset_id}.glb"
    if not file_path.exists():
        # Fallback to the stored file_path if direct path doesn't exist
        if asset.file_path:
            file_path = settings.GENERATED_DIR / asset.file_path
        if not file_path.exists():
            raise HTTPException(404, "Asset file not found on disk")

    return FileResponse(
        path=file_path,
        filename=f"{asset.name}.glb",
        media_type="model/gltf-binary",
    )


@router.post("/{asset_id}/tags/{tag_id}")
async def add_tag_to_asset(
    asset_id: str,
    tag_id: int,
    db: AsyncSession = Depends(get_session),
):
    """Add a tag to an asset."""
    result = await db.execute(
        select(Asset)
        .options(selectinload(Asset.tags))
        .where(Asset.id == asset_id)
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(404, "Asset not found")

    tag_result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = tag_result.scalar_one_or_none()
    if not tag:
        raise HTTPException(404, "Tag not found")

    if tag not in asset.tags:
        asset.tags.append(tag)
        await db.flush()

    return {"message": "Tag added", "asset_id": asset_id, "tag_id": tag_id}


@router.delete("/{asset_id}/tags/{tag_id}")
async def remove_tag_from_asset(
    asset_id: str,
    tag_id: int,
    db: AsyncSession = Depends(get_session),
):
    """Remove a tag from an asset."""
    result = await db.execute(
        select(Asset)
        .options(selectinload(Asset.tags))
        .where(Asset.id == asset_id)
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(404, "Asset not found")

    tag_result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = tag_result.scalar_one_or_none()
    if not tag:
        raise HTTPException(404, "Tag not found")

    if tag in asset.tags:
        asset.tags.remove(tag)
        await db.flush()

    return {"message": "Tag removed", "asset_id": asset_id, "tag_id": tag_id}
