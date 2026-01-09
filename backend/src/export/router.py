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
