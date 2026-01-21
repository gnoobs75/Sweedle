"""
Export Router - API endpoints for asset export and processing
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional
from pathlib import Path
import logging

from .lod_generator import LODGenerator, LODResult
from .mesh_optimizer import MeshOptimizer, ValidationResult, OptimizationResult
from .draco_compressor import DracoCompressor, DracoSettings, CompressionResult
from .validator import AssetValidator, AssetValidationResult
from .thumbnail_generator import ThumbnailGenerator, ThumbnailSettings, ThumbnailResult
from .gltf_skinned import GLTFSkinnedExporter

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Models

class GenerateLODsRequest(BaseModel):
    asset_id: str
    ratios: Optional[list[float]] = Field(
        default=None,
        description="LOD ratios (e.g., [1.0, 0.5, 0.25, 0.1])"
    )


class LODLevelResponse(BaseModel):
    level: int
    ratio: float
    file_path: str
    vertex_count: int
    face_count: int
    file_size_bytes: int


class GenerateLODsResponse(BaseModel):
    success: bool
    asset_id: str
    lod_levels: list[LODLevelResponse]
    error: Optional[str] = None


class ValidateAssetRequest(BaseModel):
    asset_id: str
    target_engine: Optional[str] = Field(
        default=None,
        description="Target game engine (unity, unreal, godot)"
    )


class ValidationIssueResponse(BaseModel):
    category: str
    severity: str
    code: str
    message: str
    details: Optional[str] = None
    fix_suggestion: Optional[str] = None


class ValidateAssetResponse(BaseModel):
    is_valid: bool
    asset_id: str
    vertex_count: int
    face_count: int
    has_normals: bool
    has_uvs: bool
    file_size_bytes: int
    issues: list[ValidationIssueResponse]


class OptimizeMeshRequest(BaseModel):
    asset_id: str
    remove_degenerates: bool = True
    merge_duplicates: bool = True
    fix_normals: bool = True
    center_pivot: bool = False
    ground_origin: bool = Field(
        default=True,
        description="Move mesh so bottom is at Y=0 (fixes models spawning half in ground)"
    )


class OptimizeMeshResponse(BaseModel):
    success: bool
    asset_id: str
    original_vertices: int
    optimized_vertices: int
    original_faces: int
    optimized_faces: int
    operations_applied: list[str]
    error: Optional[str] = None


class CompressAssetRequest(BaseModel):
    asset_id: str
    quality: str = Field(
        default="balanced",
        description="Compression quality preset (high_quality, balanced, high_compression)"
    )


class CompressAssetResponse(BaseModel):
    success: bool
    asset_id: str
    original_size_bytes: int
    compressed_size_bytes: int
    compression_ratio: float
    size_reduction_percent: float
    error: Optional[str] = None


class GenerateThumbnailRequest(BaseModel):
    asset_id: str
    width: int = Field(default=512, ge=64, le=2048)
    height: int = Field(default=512, ge=64, le=2048)
    format: str = Field(default="png", pattern="^(png|jpg|webp)$")


class GenerateThumbnailResponse(BaseModel):
    success: bool
    asset_id: str
    thumbnail_path: Optional[str] = None
    width: int
    height: int
    file_size_bytes: int
    error: Optional[str] = None


class ExportToEngineRequest(BaseModel):
    asset_id: str
    engine: str = Field(description="Target engine (unity, unreal, godot)")
    project_path: str = Field(description="Path to engine project")
    include_lods: bool = True
    compress: bool = True
    format: str = Field(default="glb", pattern="^(glb|fbx|obj)$")


class ExportToEngineResponse(BaseModel):
    success: bool
    asset_id: str
    exported_files: list[str]
    error: Optional[str] = None


class ExportSkinnedGLBRequest(BaseModel):
    """Request for exporting skinned GLB with animations."""
    asset_id: str
    include_animations: bool = Field(
        default=True,
        description="Include animation clips in the GLB"
    )
    animation_ids: Optional[list[str]] = Field(
        default=None,
        description="Specific animation IDs to include (None = all)"
    )
    ground_origin: bool = Field(
        default=True,
        description="Move mesh so bottom is at Y=0 (fixes models spawning half in ground)"
    )


class ExportSkinnedGLBResponse(BaseModel):
    """Response from skinned GLB export."""
    success: bool
    asset_id: str
    output_path: Optional[str] = None
    bone_count: int = 0
    animation_count: int = 0
    file_size_bytes: int = 0
    error: Optional[str] = None


# Helper to get asset path (placeholder - should use asset service)
async def get_asset_path(asset_id: str) -> Path:
    """Get the file path for an asset by ID"""
    # TODO: Replace with actual asset service lookup
    from ..config import settings
    asset_dir = Path(settings.storage_path) / "generated" / asset_id

    # Find GLB file
    glb_files = list(asset_dir.glob("*.glb"))
    if glb_files:
        return glb_files[0]

    # Try other formats
    for ext in [".gltf", ".obj", ".fbx"]:
        files = list(asset_dir.glob(f"*{ext}"))
        if files:
            return files[0]

    raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")


# Endpoints

@router.post("/generate-lods", response_model=GenerateLODsResponse)
async def generate_lods(request: GenerateLODsRequest):
    """Generate LOD levels for an asset"""
    try:
        asset_path = await get_asset_path(request.asset_id)

        generator = LODGenerator()
        result = await generator.generate_lods(
            source_path=asset_path,
            ratios=request.ratios,
        )

        return GenerateLODsResponse(
            success=result.success,
            asset_id=request.asset_id,
            lod_levels=[
                LODLevelResponse(
                    level=lod.level,
                    ratio=lod.ratio,
                    file_path=str(lod.file_path),
                    vertex_count=lod.vertex_count,
                    face_count=lod.face_count,
                    file_size_bytes=lod.file_size_bytes,
                )
                for lod in result.lod_levels
            ],
            error=result.error,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"LOD generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate", response_model=ValidateAssetResponse)
async def validate_asset(request: ValidateAssetRequest):
    """Validate an asset for game engine compatibility"""
    try:
        asset_path = await get_asset_path(request.asset_id)

        validator = AssetValidator()
        result = await validator.validate(
            asset_path=asset_path,
            target_engine=request.target_engine,
        )

        return ValidateAssetResponse(
            is_valid=result.is_valid,
            asset_id=request.asset_id,
            vertex_count=result.vertex_count,
            face_count=result.face_count,
            has_normals=result.has_normals,
            has_uvs=result.has_uvs,
            file_size_bytes=result.file_size_bytes,
            issues=[
                ValidationIssueResponse(
                    category=issue.category.value,
                    severity=issue.severity.value,
                    code=issue.code,
                    message=issue.message,
                    details=issue.details,
                    fix_suggestion=issue.fix_suggestion,
                )
                for issue in result.issues
            ],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/optimize", response_model=OptimizeMeshResponse)
async def optimize_mesh(request: OptimizeMeshRequest):
    """Optimize a mesh (remove degenerates, merge vertices, fix normals)"""
    try:
        asset_path = await get_asset_path(request.asset_id)

        optimizer = MeshOptimizer()
        result = await optimizer.optimize(
            input_path=asset_path,
            remove_degenerates=request.remove_degenerates,
            merge_duplicates=request.merge_duplicates,
            fix_normals=request.fix_normals,
            center_pivot=request.center_pivot,
            ground_origin=request.ground_origin,
        )

        return OptimizeMeshResponse(
            success=result.success,
            asset_id=request.asset_id,
            original_vertices=result.original_stats.vertex_count if result.original_stats else 0,
            optimized_vertices=result.optimized_stats.vertex_count if result.optimized_stats else 0,
            original_faces=result.original_stats.face_count if result.original_stats else 0,
            optimized_faces=result.optimized_stats.face_count if result.optimized_stats else 0,
            operations_applied=result.operations_applied,
            error=result.error,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Optimization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compress", response_model=CompressAssetResponse)
async def compress_asset(request: CompressAssetRequest):
    """Compress an asset with Draco"""
    try:
        asset_path = await get_asset_path(request.asset_id)

        compressor = DracoCompressor()

        if request.quality == "high_quality":
            settings = DracoSettings.high_quality()
        elif request.quality == "high_compression":
            settings = DracoSettings.high_compression()
        else:
            settings = DracoSettings.balanced()

        result = await compressor.compress(asset_path, settings=settings)

        return CompressAssetResponse(
            success=result.success,
            asset_id=request.asset_id,
            original_size_bytes=result.original_size_bytes,
            compressed_size_bytes=result.compressed_size_bytes,
            compression_ratio=result.compression_ratio,
            size_reduction_percent=result.size_reduction_percent,
            error=result.error,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Compression failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/thumbnail", response_model=GenerateThumbnailResponse)
async def generate_thumbnail(request: GenerateThumbnailRequest):
    """Generate a thumbnail preview for an asset"""
    try:
        asset_path = await get_asset_path(request.asset_id)

        generator = ThumbnailGenerator()
        settings = ThumbnailSettings(
            width=request.width,
            height=request.height,
            format=request.format,
        )

        result = await generator.generate(asset_path, settings=settings)

        return GenerateThumbnailResponse(
            success=result.success,
            asset_id=request.asset_id,
            thumbnail_path=str(result.thumbnail_path) if result.thumbnail_path else None,
            width=result.width,
            height=result.height,
            file_size_bytes=result.file_size_bytes,
            error=result.error,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Thumbnail generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/to-engine", response_model=ExportToEngineResponse)
async def export_to_engine(request: ExportToEngineRequest, background_tasks: BackgroundTasks):
    """Export an asset to a game engine project"""
    try:
        asset_path = await get_asset_path(request.asset_id)
        project_path = Path(request.project_path)

        if not project_path.exists():
            raise HTTPException(
                status_code=400,
                detail=f"Project path does not exist: {project_path}"
            )

        exported_files = []

        # Determine export destination based on engine
        if request.engine.lower() == "unity":
            export_dir = project_path / "Assets" / "Sweedle" / request.asset_id
        elif request.engine.lower() == "unreal":
            export_dir = project_path / "Content" / "Sweedle" / request.asset_id
        elif request.engine.lower() == "godot":
            export_dir = project_path / "assets" / "sweedle" / request.asset_id
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown engine: {request.engine}"
            )

        export_dir.mkdir(parents=True, exist_ok=True)

        # Copy main asset
        import shutil
        dest_path = export_dir / asset_path.name
        shutil.copy2(asset_path, dest_path)
        exported_files.append(str(dest_path))

        # Generate LODs if requested
        if request.include_lods:
            generator = LODGenerator()
            lod_result = await generator.generate_lods(asset_path, output_dir=export_dir)
            for lod in lod_result.lod_levels[1:]:  # Skip LOD0 (original)
                exported_files.append(str(lod.file_path))

        # Compress if requested
        if request.compress and request.format == "glb":
            compressor = DracoCompressor()
            compressed_path = export_dir / f"{asset_path.stem}_compressed.glb"
            await compressor.compress(dest_path, compressed_path)
            exported_files.append(str(compressed_path))

        return ExportToEngineResponse(
            success=True,
            asset_id=request.asset_id,
            exported_files=exported_files,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Engine export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/skinned-glb", response_model=ExportSkinnedGLBResponse)
async def export_skinned_glb(request: ExportSkinnedGLBRequest):
    """
    Export a rigged asset as a skinned GLB with embedded skeleton and animations.

    This creates a self-contained GLB file that includes:
    - Mesh with skinning weights (vertex deformation)
    - Bone hierarchy as GLTF nodes
    - Optional animation clips

    The output is compatible with Godot 4.x, Unity, Unreal, and Three.js.
    """
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import select
    from ..config import settings
    from ..generation.models import Asset, AnimationClip
    from ..rigging.schemas import SkeletonData, SkinningData

    try:
        # Get database session
        engine = create_async_engine(settings.DATABASE_URL)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as db:
            # Fetch asset
            result = await db.execute(select(Asset).where(Asset.id == request.asset_id))
            asset = result.scalar_one_or_none()

            if not asset:
                raise HTTPException(status_code=404, detail=f"Asset not found: {request.asset_id}")

            if not asset.is_rigged:
                raise HTTPException(status_code=400, detail="Asset is not rigged")

            if not asset.rigging_data:
                raise HTTPException(status_code=400, detail="Asset has no skeleton data")

            if not asset.skinning_data:
                raise HTTPException(status_code=400, detail="Asset has no skinning data. Please re-rig the asset.")

            # Parse skeleton and skinning data
            skeleton = SkeletonData(**asset.rigging_data)
            skinning = SkinningData(**asset.skinning_data)

            # Get source mesh path - paths in DB are relative to backend dir
            raw_path = asset.rigged_mesh_path or asset.textured_path or asset.file_path
            source_mesh = Path(raw_path)

            # Paths stored in DB already include "storage/" prefix
            # They are relative to the backend directory, not to STORAGE_ROOT
            # So just use them as-is (they're already correct relative paths)

            if not source_mesh.exists():
                raise HTTPException(status_code=404, detail=f"Source mesh not found: {source_mesh}")

            # Prepare animations if requested
            animations = []
            if request.include_animations:
                # Fetch animations
                anim_query = select(AnimationClip).where(AnimationClip.asset_id == request.asset_id)
                if request.animation_ids:
                    anim_query = anim_query.where(AnimationClip.id.in_(request.animation_ids))

                anim_result = await db.execute(anim_query)
                clips = anim_result.scalars().all()

                for clip in clips:
                    if clip.keyframe_data:
                        anim_dict = {
                            "name": clip.name,
                            "duration": clip.duration_seconds,
                            "tracks": []
                        }
                        for track in clip.keyframe_data.get("tracks", []):
                            track_dict = {
                                "bone_name": track.get("bone_name"),
                                "times": track.get("times", []),
                            }
                            # Handle rotations (flatten from [[x,y,z,w],...] to [[x,y,z,w],...])
                            if track.get("rotations"):
                                track_dict["rotations"] = track["rotations"]
                            if track.get("positions"):
                                track_dict["positions"] = track["positions"]
                            anim_dict["tracks"].append(track_dict)
                        animations.append(anim_dict)

            # Determine output path
            output_dir = Path(settings.EXPORT_DIR) / request.asset_id
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"{asset.name or request.asset_id}_skinned.glb"

            # Export skinned GLB
            exporter = GLTFSkinnedExporter()
            result_path = exporter.export(
                mesh_path=source_mesh,
                skeleton=skeleton,
                skinning=skinning,
                output_path=output_path,
                animations=animations if animations else None,
                ground_origin=request.ground_origin,
            )

            # Get file size
            file_size = result_path.stat().st_size

            return ExportSkinnedGLBResponse(
                success=True,
                asset_id=request.asset_id,
                output_path=str(result_path),
                bone_count=len(skeleton.bones),
                animation_count=len(animations),
                file_size_bytes=file_size,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Skinned GLB export failed: {e}", exc_info=True)
        return ExportSkinnedGLBResponse(
            success=False,
            asset_id=request.asset_id,
            error=str(e),
        )
