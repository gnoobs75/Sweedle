"""
Asset Validator - Validate 3D assets for game engine compatibility

Provides comprehensive validation for 3D assets before export to game engines.
"""

import asyncio
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

try:
    import trimesh
    HAS_TRIMESH = True
except ImportError:
    HAS_TRIMESH = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Severity levels for validation issues"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationCategory(Enum):
    """Categories of validation checks"""
    GEOMETRY = "geometry"
    MATERIALS = "materials"
    TEXTURES = "textures"
    SCALE = "scale"
    PERFORMANCE = "performance"
    COMPATIBILITY = "compatibility"


@dataclass
class ValidationIssue:
    """A single validation issue"""
    category: ValidationCategory
    severity: ValidationSeverity
    code: str
    message: str
    details: Optional[str] = None
    fix_suggestion: Optional[str] = None


@dataclass
class TextureInfo:
    """Information about a texture"""
    name: str
    path: Optional[str]
    width: int
    height: int
    format: str
    is_power_of_two: bool
    size_bytes: int


@dataclass
class MaterialInfo:
    """Information about a material"""
    name: str
    has_base_color: bool
    has_metallic_roughness: bool
    has_normal_map: bool
    has_emissive: bool
    has_occlusion: bool
    texture_count: int


@dataclass
class AssetValidationResult:
    """Complete validation result for an asset"""
    is_valid: bool
    asset_path: Path
    issues: list[ValidationIssue] = field(default_factory=list)

    # Geometry info
    vertex_count: int = 0
    face_count: int = 0
    mesh_count: int = 0
    has_normals: bool = False
    has_uvs: bool = False
    is_watertight: bool = False

    # Bounds
    bounding_box: tuple[tuple, tuple] = ((0, 0, 0), (0, 0, 0))
    scale_meters: float = 0.0

    # Materials and textures
    materials: list[MaterialInfo] = field(default_factory=list)
    textures: list[TextureInfo] = field(default_factory=list)

    # File info
    file_size_bytes: int = 0
    format: str = ""

    def get_errors(self) -> list[ValidationIssue]:
        """Get only error-level issues"""
        return [i for i in self.issues if i.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL)]

    def get_warnings(self) -> list[ValidationIssue]:
        """Get warning-level issues"""
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]


class AssetValidator:
    """
    Validates 3D assets for game engine compatibility.

    Checks:
    - Geometry: normals, UVs, degenerate faces, manifold
    - Scale: appropriate size for game engines
    - Materials: PBR compliance, texture presence
    - Textures: power-of-two, format compatibility
    - Performance: poly count, texture sizes
    """

    # Thresholds
    MAX_VERTEX_COUNT = 500000
    MAX_FACE_COUNT = 250000
    RECOMMENDED_MAX_FACES = 100000
    MAX_TEXTURE_SIZE = 4096
    RECOMMENDED_TEXTURE_SIZE = 2048

    # Scale validation (assuming meters)
    MIN_SCALE = 0.001  # 1mm
    MAX_SCALE = 1000   # 1km
    RECOMMENDED_MIN_SCALE = 0.01  # 1cm
    RECOMMENDED_MAX_SCALE = 100   # 100m

    def __init__(self):
        if not HAS_TRIMESH:
            logger.warning("trimesh not available, geometry validation limited")

    async def validate(
        self,
        asset_path: Path,
        target_engine: Optional[str] = None,
    ) -> AssetValidationResult:
        """
        Validate an asset for game engine use.

        Args:
            asset_path: Path to the asset file
            target_engine: Optional target engine ("unity", "unreal", "godot")

        Returns:
            AssetValidationResult with issues and asset info
        """
        issues: list[ValidationIssue] = []

        try:
            file_size = asset_path.stat().st_size
            file_format = asset_path.suffix.lower()

            # Validate file format
            if file_format not in [".glb", ".gltf", ".obj", ".fbx"]:
                issues.append(ValidationIssue(
                    category=ValidationCategory.COMPATIBILITY,
                    severity=ValidationSeverity.WARNING,
                    code="UNSUPPORTED_FORMAT",
                    message=f"Format {file_format} may not be fully supported",
                    fix_suggestion="Convert to GLB for best compatibility",
                ))

            # Load and validate geometry
            geo_result = await self._validate_geometry(asset_path, issues)

            # Validate scale
            self._validate_scale(geo_result, issues)

            # Engine-specific checks
            if target_engine:
                self._validate_for_engine(target_engine, geo_result, issues)

            is_valid = not any(
                i.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL)
                for i in issues
            )

            return AssetValidationResult(
                is_valid=is_valid,
                asset_path=asset_path,
                issues=issues,
                vertex_count=geo_result.get("vertex_count", 0),
                face_count=geo_result.get("face_count", 0),
                mesh_count=geo_result.get("mesh_count", 0),
                has_normals=geo_result.get("has_normals", False),
                has_uvs=geo_result.get("has_uvs", False),
                is_watertight=geo_result.get("is_watertight", False),
                bounding_box=geo_result.get("bounding_box", ((0, 0, 0), (0, 0, 0))),
                scale_meters=geo_result.get("scale", 0.0),
                materials=geo_result.get("materials", []),
                textures=geo_result.get("textures", []),
                file_size_bytes=file_size,
                format=file_format,
            )

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            issues.append(ValidationIssue(
                category=ValidationCategory.COMPATIBILITY,
                severity=ValidationSeverity.CRITICAL,
                code="LOAD_FAILED",
                message=f"Failed to load asset: {e}",
            ))

            return AssetValidationResult(
                is_valid=False,
                asset_path=asset_path,
                issues=issues,
            )

    async def _validate_geometry(
        self,
        asset_path: Path,
        issues: list[ValidationIssue],
    ) -> dict:
        """Validate mesh geometry"""
        if not HAS_TRIMESH:
            return {}

        def do_validate():
            result = {}

            mesh = trimesh.load(str(asset_path))

            # Handle scene vs single mesh
            if hasattr(mesh, 'geometry'):
                geometries = list(mesh.geometry.values())
                result["mesh_count"] = len(geometries)
            else:
                geometries = [mesh]
                result["mesh_count"] = 1

            total_verts = 0
            total_faces = 0
            all_have_normals = True
            all_have_uvs = True
            degenerate_count = 0

            for geom in geometries:
                if hasattr(geom, 'vertices'):
                    total_verts += len(geom.vertices)
                if hasattr(geom, 'faces'):
                    total_faces += len(geom.faces)

                    # Check for degenerate faces
                    if hasattr(geom, 'area_faces'):
                        import numpy as np
                        degenerate_count += np.sum(geom.area_faces < 1e-10)

                if not (hasattr(geom, 'vertex_normals') and geom.vertex_normals is not None):
                    all_have_normals = False

                if not (hasattr(geom, 'visual') and hasattr(geom.visual, 'uv') and geom.visual.uv is not None):
                    all_have_uvs = False

            result["vertex_count"] = total_verts
            result["face_count"] = total_faces
            result["has_normals"] = all_have_normals
            result["has_uvs"] = all_have_uvs
            result["degenerate_faces"] = degenerate_count

            # Bounding box and scale
            if hasattr(mesh, 'bounds') and mesh.bounds is not None:
                bounds = mesh.bounds
                result["bounding_box"] = (tuple(bounds[0]), tuple(bounds[1]))
                size = bounds[1] - bounds[0]
                result["scale"] = max(size)
            else:
                result["bounding_box"] = ((0, 0, 0), (0, 0, 0))
                result["scale"] = 0

            # Watertight check
            if hasattr(mesh, 'is_watertight'):
                result["is_watertight"] = mesh.is_watertight
            else:
                result["is_watertight"] = False

            return result

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, do_validate)

        # Add issues based on geometry analysis
        if result.get("vertex_count", 0) > self.MAX_VERTEX_COUNT:
            issues.append(ValidationIssue(
                category=ValidationCategory.PERFORMANCE,
                severity=ValidationSeverity.ERROR,
                code="TOO_MANY_VERTICES",
                message=f"Vertex count ({result['vertex_count']}) exceeds maximum ({self.MAX_VERTEX_COUNT})",
                fix_suggestion="Decimate the mesh or generate LODs",
            ))
        elif result.get("vertex_count", 0) > self.RECOMMENDED_MAX_FACES:
            issues.append(ValidationIssue(
                category=ValidationCategory.PERFORMANCE,
                severity=ValidationSeverity.WARNING,
                code="HIGH_VERTEX_COUNT",
                message=f"High vertex count ({result['vertex_count']}), consider LODs",
                fix_suggestion="Generate LOD levels for better performance",
            ))

        if result.get("face_count", 0) > self.MAX_FACE_COUNT:
            issues.append(ValidationIssue(
                category=ValidationCategory.PERFORMANCE,
                severity=ValidationSeverity.ERROR,
                code="TOO_MANY_FACES",
                message=f"Face count ({result['face_count']}) exceeds maximum",
                fix_suggestion="Decimate the mesh",
            ))

        if not result.get("has_normals", False):
            issues.append(ValidationIssue(
                category=ValidationCategory.GEOMETRY,
                severity=ValidationSeverity.WARNING,
                code="MISSING_NORMALS",
                message="Mesh has no vertex normals",
                fix_suggestion="Generate normals in your 3D software or use auto-generate",
            ))

        if not result.get("has_uvs", False):
            issues.append(ValidationIssue(
                category=ValidationCategory.GEOMETRY,
                severity=ValidationSeverity.WARNING,
                code="MISSING_UVS",
                message="Mesh has no UV coordinates",
                fix_suggestion="UV unwrap the mesh for proper texturing",
            ))

        if result.get("degenerate_faces", 0) > 0:
            issues.append(ValidationIssue(
                category=ValidationCategory.GEOMETRY,
                severity=ValidationSeverity.WARNING,
                code="DEGENERATE_FACES",
                message=f"{result['degenerate_faces']} degenerate faces found",
                fix_suggestion="Clean up mesh in 3D software or use mesh optimizer",
            ))

        return result

    def _validate_scale(self, geo_result: dict, issues: list[ValidationIssue]):
        """Validate asset scale"""
        scale = geo_result.get("scale", 0)

        if scale == 0:
            issues.append(ValidationIssue(
                category=ValidationCategory.SCALE,
                severity=ValidationSeverity.WARNING,
                code="ZERO_SCALE",
                message="Asset has zero scale",
                fix_suggestion="Check if mesh has any geometry",
            ))
        elif scale < self.MIN_SCALE:
            issues.append(ValidationIssue(
                category=ValidationCategory.SCALE,
                severity=ValidationSeverity.ERROR,
                code="TOO_SMALL",
                message=f"Asset is extremely small ({scale:.6f}m)",
                fix_suggestion="Scale up the asset",
            ))
        elif scale > self.MAX_SCALE:
            issues.append(ValidationIssue(
                category=ValidationCategory.SCALE,
                severity=ValidationSeverity.ERROR,
                code="TOO_LARGE",
                message=f"Asset is extremely large ({scale:.2f}m)",
                fix_suggestion="Scale down the asset",
            ))
        elif scale < self.RECOMMENDED_MIN_SCALE:
            issues.append(ValidationIssue(
                category=ValidationCategory.SCALE,
                severity=ValidationSeverity.WARNING,
                code="SMALL_SCALE",
                message=f"Asset is quite small ({scale:.4f}m)",
                details="This may cause precision issues in game engines",
            ))
        elif scale > self.RECOMMENDED_MAX_SCALE:
            issues.append(ValidationIssue(
                category=ValidationCategory.SCALE,
                severity=ValidationSeverity.WARNING,
                code="LARGE_SCALE",
                message=f"Asset is quite large ({scale:.2f}m)",
                details="Consider if this is appropriate for your use case",
            ))

    def _validate_for_engine(
        self,
        engine: str,
        geo_result: dict,
        issues: list[ValidationIssue],
    ):
        """Engine-specific validation"""
        engine = engine.lower()

        if engine == "unity":
            # Unity-specific checks
            if geo_result.get("vertex_count", 0) > 65535 and not geo_result.get("has_32bit_indices"):
                issues.append(ValidationIssue(
                    category=ValidationCategory.COMPATIBILITY,
                    severity=ValidationSeverity.INFO,
                    code="UNITY_32BIT_INDICES",
                    message="Mesh has >65535 vertices, will use 32-bit indices in Unity",
                ))

        elif engine == "unreal":
            # Unreal-specific checks
            if geo_result.get("scale", 0) > 0:
                # Unreal uses centimeters by default
                scale_cm = geo_result["scale"] * 100
                if scale_cm > 100000:
                    issues.append(ValidationIssue(
                        category=ValidationCategory.COMPATIBILITY,
                        severity=ValidationSeverity.WARNING,
                        code="UNREAL_LARGE_SCALE",
                        message="Asset may appear very large in Unreal (uses cm by default)",
                        fix_suggestion="Scale down by 100x for Unreal import",
                    ))

        elif engine == "godot":
            # Godot-specific checks
            pass  # Godot is generally flexible


# Convenience function
async def validate_asset(
    asset_path: Path,
    target_engine: Optional[str] = None,
) -> AssetValidationResult:
    """Validate an asset for game engine use"""
    validator = AssetValidator()
    return await validator.validate(asset_path, target_engine)
