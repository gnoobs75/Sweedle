"""
LOD Generator - Level of Detail generation for 3D meshes

Uses gltfpack/meshoptimizer for efficient LOD generation.
Falls back to Open3D mesh simplification if gltfpack is unavailable.
"""

import asyncio
import subprocess
import shutil
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import tempfile

try:
    import open3d as o3d
    HAS_OPEN3D = True
except ImportError:
    HAS_OPEN3D = False

try:
    import trimesh
    HAS_TRIMESH = True
except ImportError:
    HAS_TRIMESH = False

logger = logging.getLogger(__name__)


@dataclass
class LODLevel:
    """Represents a single LOD level"""
    level: int
    ratio: float  # 1.0 = full detail, 0.1 = 10% of original
    file_path: Path
    vertex_count: int
    face_count: int
    file_size_bytes: int


@dataclass
class LODResult:
    """Result of LOD generation"""
    success: bool
    source_path: Path
    lod_levels: list[LODLevel]
    error: Optional[str] = None


class LODGenerator:
    """
    Generates Level of Detail (LOD) meshes for 3D assets.

    Default LOD ratios:
    - LOD0: 100% (original)
    - LOD1: 50%
    - LOD2: 25%
    - LOD3: 10%
    """

    DEFAULT_LOD_RATIOS = [1.0, 0.5, 0.25, 0.1]

    def __init__(
        self,
        gltfpack_path: Optional[str] = None,
        output_dir: Optional[Path] = None,
    ):
        self.gltfpack_path = gltfpack_path or self._find_gltfpack()
        self.output_dir = output_dir

    def _find_gltfpack(self) -> Optional[str]:
        """Locate gltfpack executable"""
        # Check common locations
        candidates = [
            "gltfpack",
            "gltfpack.exe",
            "/usr/local/bin/gltfpack",
            "C:/Program Files/gltfpack/gltfpack.exe",
        ]

        for candidate in candidates:
            if shutil.which(candidate):
                return candidate

        return None

    async def generate_lods(
        self,
        source_path: Path,
        ratios: Optional[list[float]] = None,
        output_dir: Optional[Path] = None,
    ) -> LODResult:
        """
        Generate LOD levels for a mesh file.

        Args:
            source_path: Path to source GLB/GLTF file
            ratios: List of decimation ratios (1.0 = full, 0.5 = 50%)
            output_dir: Directory for output files

        Returns:
            LODResult with generated LOD files
        """
        ratios = ratios or self.DEFAULT_LOD_RATIOS
        output_dir = output_dir or self.output_dir or source_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)

        lod_levels: list[LODLevel] = []

        try:
            # LOD0 is always the original
            source_stats = await self._get_mesh_stats(source_path)
            lod_levels.append(LODLevel(
                level=0,
                ratio=1.0,
                file_path=source_path,
                vertex_count=source_stats.get("vertices", 0),
                face_count=source_stats.get("faces", 0),
                file_size_bytes=source_path.stat().st_size,
            ))

            # Generate remaining LOD levels
            for i, ratio in enumerate(ratios[1:], start=1):
                lod_path = output_dir / f"{source_path.stem}_lod{i}{source_path.suffix}"

                success = await self._generate_single_lod(
                    source_path=source_path,
                    output_path=lod_path,
                    ratio=ratio,
                )

                if success and lod_path.exists():
                    stats = await self._get_mesh_stats(lod_path)
                    lod_levels.append(LODLevel(
                        level=i,
                        ratio=ratio,
                        file_path=lod_path,
                        vertex_count=stats.get("vertices", 0),
                        face_count=stats.get("faces", 0),
                        file_size_bytes=lod_path.stat().st_size,
                    ))
                else:
                    logger.warning(f"Failed to generate LOD{i} at ratio {ratio}")

            return LODResult(
                success=len(lod_levels) > 1,
                source_path=source_path,
                lod_levels=lod_levels,
            )

        except Exception as e:
            logger.error(f"LOD generation failed: {e}")
            return LODResult(
                success=False,
                source_path=source_path,
                lod_levels=lod_levels,
                error=str(e),
            )

    async def _generate_single_lod(
        self,
        source_path: Path,
        output_path: Path,
        ratio: float,
    ) -> bool:
        """Generate a single LOD level"""
        if self.gltfpack_path:
            return await self._generate_with_gltfpack(source_path, output_path, ratio)
        elif HAS_OPEN3D:
            return await self._generate_with_open3d(source_path, output_path, ratio)
        elif HAS_TRIMESH:
            return await self._generate_with_trimesh(source_path, output_path, ratio)
        else:
            logger.error("No LOD generation backend available")
            return False

    async def _generate_with_gltfpack(
        self,
        source_path: Path,
        output_path: Path,
        ratio: float,
    ) -> bool:
        """Use gltfpack for LOD generation (preferred method)"""
        try:
            # Calculate simplify ratio (gltfpack uses target ratio directly)
            simplify_ratio = ratio

            cmd = [
                self.gltfpack_path,
                "-i", str(source_path),
                "-o", str(output_path),
                "-si", str(simplify_ratio),  # Simplify ratio
                "-noq",  # Disable quantization for quality
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                logger.error(f"gltfpack failed: {stderr.decode()}")
                return False

            return output_path.exists()

        except Exception as e:
            logger.error(f"gltfpack error: {e}")
            return False

    async def _generate_with_open3d(
        self,
        source_path: Path,
        output_path: Path,
        ratio: float,
    ) -> bool:
        """Use Open3D for mesh simplification"""
        if not HAS_OPEN3D:
            return False

        try:
            def simplify():
                mesh = o3d.io.read_triangle_mesh(str(source_path))

                target_triangles = int(len(mesh.triangles) * ratio)
                target_triangles = max(target_triangles, 100)  # Minimum triangles

                simplified = mesh.simplify_quadric_decimation(
                    target_number_of_triangles=target_triangles
                )

                o3d.io.write_triangle_mesh(str(output_path), simplified)
                return output_path.exists()

            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, simplify)

        except Exception as e:
            logger.error(f"Open3D simplification error: {e}")
            return False

    async def _generate_with_trimesh(
        self,
        source_path: Path,
        output_path: Path,
        ratio: float,
    ) -> bool:
        """Use trimesh for mesh simplification"""
        if not HAS_TRIMESH:
            return False

        try:
            def simplify():
                mesh = trimesh.load(str(source_path))

                if hasattr(mesh, 'geometry'):
                    # Handle GLB with multiple meshes
                    for name, geom in mesh.geometry.items():
                        if hasattr(geom, 'faces'):
                            target_faces = int(len(geom.faces) * ratio)
                            target_faces = max(target_faces, 100)
                            geom = geom.simplify_quadric_decimation(target_faces)
                            mesh.geometry[name] = geom
                elif hasattr(mesh, 'faces'):
                    # Single mesh
                    target_faces = int(len(mesh.faces) * ratio)
                    target_faces = max(target_faces, 100)
                    mesh = mesh.simplify_quadric_decimation(target_faces)

                mesh.export(str(output_path))
                return output_path.exists()

            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, simplify)

        except Exception as e:
            logger.error(f"Trimesh simplification error: {e}")
            return False

    async def _get_mesh_stats(self, path: Path) -> dict:
        """Get vertex and face count from mesh file"""
        try:
            if HAS_TRIMESH:
                def get_stats():
                    mesh = trimesh.load(str(path))
                    if hasattr(mesh, 'geometry'):
                        vertices = sum(
                            len(g.vertices) for g in mesh.geometry.values()
                            if hasattr(g, 'vertices')
                        )
                        faces = sum(
                            len(g.faces) for g in mesh.geometry.values()
                            if hasattr(g, 'faces')
                        )
                    else:
                        vertices = len(mesh.vertices) if hasattr(mesh, 'vertices') else 0
                        faces = len(mesh.faces) if hasattr(mesh, 'faces') else 0
                    return {"vertices": vertices, "faces": faces}

                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, get_stats)
            elif HAS_OPEN3D:
                def get_stats():
                    mesh = o3d.io.read_triangle_mesh(str(path))
                    return {
                        "vertices": len(mesh.vertices),
                        "faces": len(mesh.triangles),
                    }

                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, get_stats)
        except Exception as e:
            logger.warning(f"Could not get mesh stats: {e}")

        return {"vertices": 0, "faces": 0}


# Convenience function
async def generate_lods(
    source_path: Path,
    ratios: Optional[list[float]] = None,
    output_dir: Optional[Path] = None,
) -> LODResult:
    """Generate LODs for a mesh file"""
    generator = LODGenerator()
    return await generator.generate_lods(source_path, ratios, output_dir)
