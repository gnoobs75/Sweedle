"""Router for asset variants and version history."""

import logging
import shutil
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.config import settings
from src.database import get_session
from src.generation.models import Asset, GenerationJob, VariantGroup, AssetVersion, JobStatus

from .schemas import (
    VariantGroupCreate,
    VariantGroupResponse,
    VariantGroupDetail,
    VariantAssetInfo,
    GenerateVariantsRequest,
    GenerateVariantsResponse,
    AssetVersionResponse,
    VersionHistoryResponse,
    CreateVersionRequest,
    CreateVersionResponse,
    RestoreVersionRequest,
    RestoreVersionResponse,
    SetPrimaryVariantRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/groups", response_model=list[VariantGroupResponse])
async def list_variant_groups(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_session),
):
    """List all variant groups."""
    # Get groups with variant counts
    result = await db.execute(
        select(VariantGroup)
        .order_by(VariantGroup.updated_at.desc())
        .offset(offset)
        .limit(limit)
    )
    groups = result.scalars().all()

    responses = []
    for group in groups:
        # Count variants
        count_result = await db.execute(
            select(func.count(Asset.id)).where(Asset.variant_group_id == group.id)
        )
        variant_count = count_result.scalar() or 0

        responses.append(VariantGroupResponse(
            id=group.id,
            name=group.name,
            description=group.description,
            source_type=group.source_type.value if group.source_type else "image_to_3d",
            source_image_path=group.source_image_path,
            source_prompt=group.source_prompt,
            primary_asset_id=group.primary_asset_id,
            variant_count=variant_count,
            created_at=group.created_at,
        ))

    return responses


@router.get("/groups/{group_id}", response_model=VariantGroupDetail)
async def get_variant_group(
    group_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Get detailed variant group with all variants."""
    result = await db.execute(
        select(VariantGroup)
        .options(selectinload(VariantGroup.variants))
        .where(VariantGroup.id == group_id)
    )
    group = result.scalar_one_or_none()

    if not group:
        raise HTTPException(status_code=404, detail="Variant group not found")

    variants = [
        VariantAssetInfo(
            id=asset.id,
            name=asset.name,
            thumbnail_path=asset.thumbnail_path,
            generation_seed=asset.generation_seed,
            variant_index=asset.variant_index,
            vertex_count=asset.vertex_count,
            face_count=asset.face_count,
            is_primary=asset.id == group.primary_asset_id,
            created_at=asset.created_at,
        )
        for asset in sorted(group.variants, key=lambda a: a.variant_index or 0)
    ]

    return VariantGroupDetail(
        id=group.id,
        name=group.name,
        description=group.description,
        source_type=group.source_type.value if group.source_type else "image_to_3d",
        source_image_path=group.source_image_path,
        source_prompt=group.source_prompt,
        primary_asset_id=group.primary_asset_id,
        variants=variants,
        created_at=group.created_at,
        updated_at=group.updated_at,
    )


@router.post("/generate", response_model=GenerateVariantsResponse)
async def generate_variants(
    request: GenerateVariantsRequest,
    db: AsyncSession = Depends(get_session),
):
    """Generate multiple variants from an existing asset."""
    # Get source asset
    result = await db.execute(select(Asset).where(Asset.id == request.asset_id))
    source_asset = result.scalar_one_or_none()

    if not source_asset:
        raise HTTPException(status_code=404, detail="Source asset not found")

    if not source_asset.source_image_path:
        raise HTTPException(status_code=400, detail="Asset has no source image for variant generation")

    try:
        # Create variant group
        group_id = str(uuid.uuid4())
        name_prefix = request.name_prefix or source_asset.name
        group = VariantGroup(
            id=group_id,
            name=f"{name_prefix} Variants",
            description=f"Generated {request.count} variants from {source_asset.name}",
            source_type=source_asset.source_type,
            source_image_path=source_asset.source_image_path,
            source_prompt=source_asset.source_prompt,
            primary_asset_id=source_asset.id,
        )
        db.add(group)

        # Link source asset to group
        source_asset.variant_group_id = group_id
        source_asset.variant_index = 0

        # Create generation jobs for new variants
        job_ids = []
        for i in range(request.count):
            import random
            seed = random.randint(0, 2**31 - 1)

            # Create new asset entry
            asset_id = str(uuid.uuid4())
            variant_name = f"{name_prefix} (Variant {i + 1})"

            new_asset = Asset(
                id=asset_id,
                name=variant_name,
                source_type=source_asset.source_type,
                source_image_path=source_asset.source_image_path,
                source_prompt=source_asset.source_prompt,
                generation_params={
                    **(source_asset.generation_params or {}),
                    "seed": seed,
                },
                file_path="",  # Will be set after generation
                status="pending",
                variant_group_id=group_id,
                generation_seed=seed,
                variant_index=i + 1,
            )
            db.add(new_asset)

            # Create generation job
            job_id = str(uuid.uuid4())
            job = GenerationJob(
                id=job_id,
                asset_id=asset_id,
                job_type="image_to_3d",
                priority=1,
                status=JobStatus.PENDING,
                payload={
                    "source_image_path": source_asset.source_image_path,
                    "name": variant_name,
                    "seed": seed,
                    **(source_asset.generation_params or {}),
                },
            )
            db.add(job)
            job_ids.append(job_id)

            # Queue the job
            from src.core.queue import get_queue
            queue = get_queue()
            await queue.enqueue({
                "job_id": job_id,
                "asset_id": asset_id,
                "type": "image_to_3d",
                "payload": job.payload,
            })

        await db.commit()

        logger.info(f"Created variant group {group_id} with {request.count} variants")

        return GenerateVariantsResponse(
            success=True,
            variant_group_id=group_id,
            job_ids=job_ids,
            message=f"Started generating {request.count} variants",
        )

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create variants: {e}")
        return GenerateVariantsResponse(
            success=False,
            variant_group_id="",
            job_ids=[],
            message="Failed to generate variants",
            error=str(e),
        )


@router.post("/groups/{group_id}/set-primary")
async def set_primary_variant(
    group_id: str,
    request: SetPrimaryVariantRequest,
    db: AsyncSession = Depends(get_session),
):
    """Set the primary variant in a group."""
    # Verify group exists
    result = await db.execute(select(VariantGroup).where(VariantGroup.id == group_id))
    group = result.scalar_one_or_none()

    if not group:
        raise HTTPException(status_code=404, detail="Variant group not found")

    # Verify asset belongs to group
    result = await db.execute(
        select(Asset).where(Asset.id == request.asset_id, Asset.variant_group_id == group_id)
    )
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(status_code=400, detail="Asset not found in variant group")

    group.primary_asset_id = request.asset_id
    await db.commit()

    return {"success": True, "message": f"Set {asset.name} as primary variant"}


@router.delete("/groups/{group_id}")
async def delete_variant_group(
    group_id: str,
    delete_assets: bool = False,
    db: AsyncSession = Depends(get_session),
):
    """Delete a variant group. Optionally delete all assets in the group."""
    result = await db.execute(
        select(VariantGroup)
        .options(selectinload(VariantGroup.variants))
        .where(VariantGroup.id == group_id)
    )
    group = result.scalar_one_or_none()

    if not group:
        raise HTTPException(status_code=404, detail="Variant group not found")

    if delete_assets:
        # Delete all assets in the group
        for asset in group.variants:
            # Delete files
            if asset.file_path:
                file_path = settings.GENERATED_DIR / asset.file_path
                if file_path.exists():
                    file_path.unlink()
            if asset.thumbnail_path:
                thumb_path = settings.GENERATED_DIR / asset.thumbnail_path
                if thumb_path.exists():
                    thumb_path.unlink()
            await db.delete(asset)
    else:
        # Just unlink assets from group
        for asset in group.variants:
            asset.variant_group_id = None
            asset.variant_index = None

    await db.delete(group)
    await db.commit()

    return {
        "success": True,
        "message": f"Deleted variant group" + (" and all assets" if delete_assets else ""),
    }


# ============ Version History Endpoints ============


@router.get("/assets/{asset_id}/versions", response_model=VersionHistoryResponse)
async def get_version_history(
    asset_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Get version history for an asset."""
    result = await db.execute(
        select(Asset)
        .options(selectinload(Asset.versions))
        .where(Asset.id == asset_id)
    )
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    versions = [
        AssetVersionResponse(
            id=v.id,
            asset_id=v.asset_id,
            version_number=v.version_number,
            change_type=v.change_type,
            change_description=v.change_description,
            file_path=v.file_path,
            thumbnail_path=v.thumbnail_path,
            vertex_count=v.vertex_count,
            face_count=v.face_count,
            file_size_bytes=v.file_size_bytes,
            created_at=v.created_at,
        )
        for v in sorted(asset.versions, key=lambda v: v.version_number, reverse=True)
    ]

    current_version = max((v.version_number for v in asset.versions), default=0)

    return VersionHistoryResponse(
        asset_id=asset.id,
        asset_name=asset.name,
        current_version=current_version,
        versions=versions,
    )


@router.post("/versions/create", response_model=CreateVersionResponse)
async def create_version(
    request: CreateVersionRequest,
    db: AsyncSession = Depends(get_session),
):
    """Create a version snapshot of an asset's current state."""
    result = await db.execute(
        select(Asset)
        .options(selectinload(Asset.versions))
        .where(Asset.id == request.asset_id)
    )
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    try:
        # Get next version number
        current_max = max((v.version_number for v in asset.versions), default=0)
        new_version_number = current_max + 1

        # Create backup of current file
        source_path = settings.GENERATED_DIR / asset.file_path
        if not source_path.exists():
            raise HTTPException(status_code=400, detail="Asset file not found")

        # Create versions directory
        versions_dir = settings.GENERATED_DIR / "versions" / asset.id
        versions_dir.mkdir(parents=True, exist_ok=True)

        # Copy file to versions directory
        backup_filename = f"v{new_version_number}_{source_path.name}"
        backup_path = versions_dir / backup_filename
        shutil.copy2(source_path, backup_path)

        # Copy thumbnail if exists
        backup_thumb_path = None
        if asset.thumbnail_path:
            thumb_source = settings.GENERATED_DIR / asset.thumbnail_path
            if thumb_source.exists():
                backup_thumb_filename = f"v{new_version_number}_thumb_{thumb_source.name}"
                backup_thumb_path = versions_dir / backup_thumb_filename
                shutil.copy2(thumb_source, backup_thumb_path)

        # Create version record
        version_id = str(uuid.uuid4())
        version = AssetVersion(
            id=version_id,
            asset_id=asset.id,
            version_number=new_version_number,
            change_type=request.change_type,
            change_description=request.change_description,
            file_path=str(backup_path.relative_to(settings.GENERATED_DIR)),
            thumbnail_path=str(backup_thumb_path.relative_to(settings.GENERATED_DIR)) if backup_thumb_path else None,
            vertex_count=asset.vertex_count,
            face_count=asset.face_count,
            file_size_bytes=asset.file_size_bytes,
        )
        db.add(version)
        await db.commit()

        logger.info(f"Created version {new_version_number} for asset {asset.id}")

        return CreateVersionResponse(
            success=True,
            version_id=version_id,
            version_number=new_version_number,
            message=f"Created version {new_version_number}",
        )

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create version: {e}")
        return CreateVersionResponse(
            success=False,
            version_id="",
            version_number=0,
            message="Failed to create version",
            error=str(e),
        )


@router.post("/versions/restore", response_model=RestoreVersionResponse)
async def restore_version(
    request: RestoreVersionRequest,
    db: AsyncSession = Depends(get_session),
):
    """Restore an asset to a previous version."""
    result = await db.execute(
        select(AssetVersion).where(AssetVersion.id == request.version_id)
    )
    version = result.scalar_one_or_none()

    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    result = await db.execute(
        select(Asset)
        .options(selectinload(Asset.versions))
        .where(Asset.id == version.asset_id)
    )
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    try:
        backup_version_id = None

        # Create backup of current state if requested
        if request.create_backup:
            current_max = max((v.version_number for v in asset.versions), default=0)
            new_version_number = current_max + 1

            source_path = settings.GENERATED_DIR / asset.file_path
            if source_path.exists():
                versions_dir = settings.GENERATED_DIR / "versions" / asset.id
                versions_dir.mkdir(parents=True, exist_ok=True)

                backup_filename = f"v{new_version_number}_{source_path.name}"
                backup_path = versions_dir / backup_filename
                shutil.copy2(source_path, backup_path)

                backup_version_id = str(uuid.uuid4())
                backup_version = AssetVersion(
                    id=backup_version_id,
                    asset_id=asset.id,
                    version_number=new_version_number,
                    change_type="manual",
                    change_description=f"Backup before restoring to v{version.version_number}",
                    file_path=str(backup_path.relative_to(settings.GENERATED_DIR)),
                    vertex_count=asset.vertex_count,
                    face_count=asset.face_count,
                    file_size_bytes=asset.file_size_bytes,
                )
                db.add(backup_version)

        # Restore the version
        version_file = settings.GENERATED_DIR / version.file_path
        if not version_file.exists():
            raise HTTPException(status_code=400, detail="Version file not found")

        dest_path = settings.GENERATED_DIR / asset.file_path
        shutil.copy2(version_file, dest_path)

        # Update asset metadata
        asset.vertex_count = version.vertex_count
        asset.face_count = version.face_count
        asset.file_size_bytes = version.file_size_bytes

        # Restore thumbnail if available
        if version.thumbnail_path:
            version_thumb = settings.GENERATED_DIR / version.thumbnail_path
            if version_thumb.exists() and asset.thumbnail_path:
                dest_thumb = settings.GENERATED_DIR / asset.thumbnail_path
                shutil.copy2(version_thumb, dest_thumb)

        await db.commit()

        logger.info(f"Restored asset {asset.id} to version {version.version_number}")

        return RestoreVersionResponse(
            success=True,
            restored_version=version.version_number,
            backup_version_id=backup_version_id,
            message=f"Restored to version {version.version_number}",
        )

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to restore version: {e}")
        return RestoreVersionResponse(
            success=False,
            restored_version=0,
            backup_version_id=None,
            message="Failed to restore version",
            error=str(e),
        )


@router.delete("/versions/{version_id}")
async def delete_version(
    version_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Delete a specific version (and its backup files)."""
    result = await db.execute(
        select(AssetVersion).where(AssetVersion.id == version_id)
    )
    version = result.scalar_one_or_none()

    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    # Delete backup files
    if version.file_path:
        file_path = settings.GENERATED_DIR / version.file_path
        if file_path.exists():
            file_path.unlink()

    if version.thumbnail_path:
        thumb_path = settings.GENERATED_DIR / version.thumbnail_path
        if thumb_path.exists():
            thumb_path.unlink()

    await db.delete(version)
    await db.commit()

    return {"success": True, "message": f"Deleted version {version.version_number}"}
