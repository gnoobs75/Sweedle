"""
Mesh Optimizer - Optimize and validate 3D meshes

Provides mesh optimization, validation, and quality checks for 3D assets.
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
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

logger = logging.getLogger(__name__)


class MeshIssue(Enum):
    """Types of mesh issues"""
    DEGENERATE_FACES = "degenerate_faces"
    DUPLICATE_VERTICES = "duplicate_vertices"
    NON_MANIFOLD = "non_manifold"
    INVERTED_NORMALS = "inverted_normals"
    MISSING_NORMALS = "missing_normals"
    MISSING_UVS = "missing_uvs"
    DISCONNECTED_COMPONENTS = "disconnected_components"
    HIGH_POLY_COUNT = "high_poly_count"
    LOW_POLY_COUNT = "low_poly_count"


@dataclass
class MeshStats:
    """Statistics for a mesh"""
    vertex_count: int = 0
    face_count: int = 0
    edge_count: int = 0
    component_count: int = 1
    has_normals: bool = False
    has_uvs: bool = False
    is_watertight: bool = False
    is_manifold: bool = True
    bounding_box_size: tuple[float, float, float] = (0, 0, 0)
    surface_area: float = 0
    volume: float = 0


@dataclass
class ValidationResult:
    """Result of mesh validation"""
    is_valid: bool
    stats: MeshStats
    issues: list[MeshIssue] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class OptimizationResult:
    """Result of mesh optimization"""
    success: bool
    input_path: Path
    output_path: Optional[Path] = None
    original_stats: Optional[MeshStats] = None
    optimized_stats: Optional[MeshStats] = None
    operations_applied: list[str] = field(default_factory=list)
    error: Optional[str] = None


class MeshOptimizer:
    """
    Optimizes 3D meshes for game engine use.

    Operations:
    - Remove degenerate faces
    - Merge duplicate vertices
    - Optimize vertex cache
    - Normalize scale
    - Fix normals
    - Center pivot
    """

    # Thresholds
    MAX_RECOMMENDED_FACES = 100000
    MIN_FACES = 10
    DUPLICATE_VERTEX_THRESHOLD = 1e-6

    def __init__(self):
        if not HAS_TRIMESH:
            raise ImportError("trimesh is required for mesh optimization")

    async def validate(self, mesh_path: Path) -> ValidationResult:
        """
        Validate a mesh and return stats and issues.

        Args:
            mesh_path: Path to mesh file

        Returns:
            ValidationResult with stats and any issues found
        """
        issues: list[MeshIssue] = []
        warnings: list[str] = []
        errors: list[str] = []

        try:
            def do_validate():
                mesh = trimesh.load(str(mesh_path))
                stats = self._get_stats(mesh)

                # Check for issues
                if hasattr(mesh, 'faces') and hasattr(mesh, 'face_adjacency'):
                    # Check for degenerate faces
                    if hasattr(mesh, 'area_faces'):
                        degenerate_count = np.sum(mesh.area_faces < 1e-10)
                        if degenerate_count > 0:
                            issues.append(MeshIssue.DEGENERATE_FACES)
                            warnings.append(f"{degenerate_count} degenerate faces found")

                    # Check manifold
                    if not mesh.is_watertight:
                        if hasattr(mesh, 'is_manifold') and not mesh.is_manifold:
                            issues.append(MeshIssue.NON_MANIFOLD)
                            warnings.append("Mesh is non-manifold")

                # Check normals
                if not stats.has_normals:
                    issues.append(MeshIssue.MISSING_NORMALS)
                    warnings.append("Mesh has no vertex normals")

                # Check UVs
                if not stats.has_uvs:
                    issues.append(MeshIssue.MISSING_UVS)
                    warnings.append("Mesh has no UV coordinates")

                # Check poly count
                if stats.face_count > self.MAX_RECOMMENDED_FACES:
                    issues.append(MeshIssue.HIGH_POLY_COUNT)
                    warnings.append(f"High poly count: {stats.face_count} faces")
                elif stats.face_count < self.MIN_FACES:
                    issues.append(MeshIssue.LOW_POLY_COUNT)
                    warnings.append(f"Very low poly count: {stats.face_count} faces")

                return stats

            loop = asyncio.get_event_loop()
            stats = await loop.run_in_executor(None, do_validate)

            return ValidationResult(
                is_valid=len(errors) == 0,
                stats=stats,
                issues=issues,
                warnings=warnings,
                errors=errors,
            )

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return ValidationResult(
                is_valid=False,
                stats=MeshStats(),
                issues=issues,
                warnings=warnings,
                errors=[str(e)],
            )

    async def optimize(
        self,
        input_path: Path,
        output_path: Optional[Path] = None,
        remove_degenerates: bool = True,
        merge_duplicates: bool = True,
        fix_normals: bool = True,
        center_pivot: bool = False,
        normalize_scale: bool = False,
        target_scale: float = 1.0,
    ) -> OptimizationResult:
        """
        Optimize a mesh file.

        Args:
            input_path: Input mesh file
            output_path: Output path (default: overwrite input)
            remove_degenerates: Remove degenerate faces
            merge_duplicates: Merge duplicate vertices
            fix_normals: Ensure consistent normals
            center_pivot: Center the mesh at origin
            normalize_scale: Scale to target size
            target_scale: Target size for normalization

        Returns:
            OptimizationResult with stats and operations applied
        """
        output_path = output_path or input_path
        operations: list[str] = []

        try:
            def do_optimize():
                mesh = trimesh.load(str(input_path))
                original_stats = self._get_stats(mesh)

                # Handle scene with multiple geometries
                if hasattr(mesh, 'geometry'):
                    for name, geom in mesh.geometry.items():
                        if hasattr(geom, 'faces'):
                            mesh.geometry[name] = self._optimize_single_mesh(
                                geom,
                                remove_degenerates,
                                merge_duplicates,
                                fix_normals,
                                center_pivot,
                                normalize_scale,
                                target_scale,
                                operations,
                            )
                elif hasattr(mesh, 'faces'):
                    mesh = self._optimize_single_mesh(
                        mesh,
                        remove_degenerates,
                        merge_duplicates,
                        fix_normals,
                        center_pivot,
                        normalize_scale,
                        target_scale,
                        operations,
                    )

                # Export
                mesh.export(str(output_path))
                optimized_stats = self._get_stats(trimesh.load(str(output_path)))

                return original_stats, optimized_stats

            loop = asyncio.get_event_loop()
            original_stats, optimized_stats = await loop.run_in_executor(None, do_optimize)

            return OptimizationResult(
                success=True,
                input_path=input_path,
                output_path=output_path,
                original_stats=original_stats,
                optimized_stats=optimized_stats,
                operations_applied=operations,
            )

        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            return OptimizationResult(
                success=False,
                input_path=input_path,
                error=str(e),
            )

    def _optimize_single_mesh(
        self,
        mesh,
        remove_degenerates: bool,
        merge_duplicates: bool,
        fix_normals: bool,
        center_pivot: bool,
        normalize_scale: bool,
        target_scale: float,
        operations: list[str],
    ):
        """Optimize a single trimesh mesh"""
        if remove_degenerates:
            original_faces = len(mesh.faces)
            mesh.remove_degenerate_faces()
            removed = original_faces - len(mesh.faces)
            if removed > 0:
                operations.append(f"Removed {removed} degenerate faces")

        if merge_duplicates:
            original_verts = len(mesh.vertices)
            mesh.merge_vertices()
            merged = original_verts - len(mesh.vertices)
            if merged > 0:
                operations.append(f"Merged {merged} duplicate vertices")

        if fix_normals:
            mesh.fix_normals()
            operations.append("Fixed normals")

        if center_pivot:
            mesh.vertices -= mesh.centroid
            operations.append("Centered pivot")

        if normalize_scale:
            scale = mesh.scale
            if scale > 0:
                target_factor = target_scale / scale
                mesh.apply_scale(target_factor)
                operations.append(f"Normalized scale to {target_scale}")

        return mesh

    def _get_stats(self, mesh) -> MeshStats:
        """Extract statistics from a mesh"""
        try:
            if hasattr(mesh, 'geometry'):
                # Scene with multiple meshes
                total_verts = 0
                total_faces = 0
                total_edges = 0
                has_normals = True
                has_uvs = True

                for geom in mesh.geometry.values():
                    if hasattr(geom, 'vertices'):
                        total_verts += len(geom.vertices)
                    if hasattr(geom, 'faces'):
                        total_faces += len(geom.faces)
                    if hasattr(geom, 'edges'):
                        total_edges += len(geom.edges)
                    if hasattr(geom, 'vertex_normals'):
                        has_normals = has_normals and geom.vertex_normals is not None
                    if hasattr(geom, 'visual') and hasattr(geom.visual, 'uv'):
                        has_uvs = has_uvs and geom.visual.uv is not None

                bounds = mesh.bounds
                bbox_size = tuple(bounds[1] - bounds[0]) if bounds is not None else (0, 0, 0)

                return MeshStats(
                    vertex_count=total_verts,
                    face_count=total_faces,
                    edge_count=total_edges,
                    component_count=len(mesh.geometry),
                    has_normals=has_normals,
                    has_uvs=has_uvs,
                    bounding_box_size=bbox_size,
                )
            else:
                # Single mesh
                bounds = mesh.bounds if hasattr(mesh, 'bounds') else None
                bbox_size = tuple(bounds[1] - bounds[0]) if bounds is not None else (0, 0, 0)

                return MeshStats(
                    vertex_count=len(mesh.vertices) if hasattr(mesh, 'vertices') else 0,
                    face_count=len(mesh.faces) if hasattr(mesh, 'faces') else 0,
                    edge_count=len(mesh.edges) if hasattr(mesh, 'edges') else 0,
                    component_count=1,
                    has_normals=hasattr(mesh, 'vertex_normals') and mesh.vertex_normals is not None,
                    has_uvs=hasattr(mesh, 'visual') and hasattr(mesh.visual, 'uv') and mesh.visual.uv is not None,
                    is_watertight=mesh.is_watertight if hasattr(mesh, 'is_watertight') else False,
                    bounding_box_size=bbox_size,
                    surface_area=mesh.area if hasattr(mesh, 'area') else 0,
                    volume=mesh.volume if hasattr(mesh, 'volume') else 0,
                )
        except Exception as e:
            logger.warning(f"Could not get mesh stats: {e}")
            return MeshStats()


# Convenience functions
async def validate_mesh(mesh_path: Path) -> ValidationResult:
    """Validate a mesh file"""
    optimizer = MeshOptimizer()
    return await optimizer.validate(mesh_path)


async def optimize_mesh(
    input_path: Path,
    output_path: Optional[Path] = None,
    **kwargs,
) -> OptimizationResult:
    """Optimize a mesh file"""
    optimizer = MeshOptimizer()
    return await optimizer.optimize(input_path, output_path, **kwargs)
