"""
Draco Compressor - Compress 3D meshes with Google Draco

Provides Draco compression for GLB/GLTF files for web optimization.
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
    import DracoPy
    HAS_DRACOPY = True
except ImportError:
    HAS_DRACOPY = False

try:
    import trimesh
    import numpy as np
    HAS_TRIMESH = True
except ImportError:
    HAS_TRIMESH = False

logger = logging.getLogger(__name__)


@dataclass
class CompressionResult:
    """Result of Draco compression"""
    success: bool
    input_path: Path
    output_path: Optional[Path] = None
    original_size_bytes: int = 0
    compressed_size_bytes: int = 0
    compression_ratio: float = 0.0
    error: Optional[str] = None

    @property
    def size_reduction_percent(self) -> float:
        """Calculate size reduction percentage"""
        if self.original_size_bytes == 0:
            return 0.0
        return (1 - self.compressed_size_bytes / self.original_size_bytes) * 100


@dataclass
class DracoSettings:
    """Settings for Draco compression"""
    # Quantization bits (higher = better quality, larger files)
    position_quantization: int = 14  # Position: 11-14 bits typical
    normal_quantization: int = 10    # Normals: 8-10 bits typical
    uv_quantization: int = 12        # UVs: 10-12 bits typical
    color_quantization: int = 8      # Colors: 8 bits typical
    generic_quantization: int = 12   # Other attributes

    # Compression level (0-10, higher = slower but better compression)
    compression_level: int = 7

    @classmethod
    def high_quality(cls) -> "DracoSettings":
        """Settings prioritizing quality over compression"""
        return cls(
            position_quantization=16,
            normal_quantization=12,
            uv_quantization=14,
            color_quantization=10,
            compression_level=5,
        )

    @classmethod
    def balanced(cls) -> "DracoSettings":
        """Balanced settings (default)"""
        return cls()

    @classmethod
    def high_compression(cls) -> "DracoSettings":
        """Settings prioritizing compression over quality"""
        return cls(
            position_quantization=11,
            normal_quantization=8,
            uv_quantization=10,
            color_quantization=8,
            compression_level=10,
        )


class DracoCompressor:
    """
    Compresses 3D mesh data using Google Draco.

    Supports:
    - GLB/GLTF files (via gltf-transform or gltfpack)
    - Raw mesh data (via DracoPy)
    """

    def __init__(
        self,
        gltf_transform_path: Optional[str] = None,
        gltfpack_path: Optional[str] = None,
    ):
        self.gltf_transform_path = gltf_transform_path or self._find_gltf_transform()
        self.gltfpack_path = gltfpack_path or self._find_gltfpack()

    def _find_gltf_transform(self) -> Optional[str]:
        """Locate gltf-transform CLI"""
        candidates = [
            "gltf-transform",
            "npx gltf-transform",
        ]
        for candidate in candidates:
            if shutil.which(candidate.split()[0]):
                return candidate
        return None

    def _find_gltfpack(self) -> Optional[str]:
        """Locate gltfpack executable"""
        candidates = [
            "gltfpack",
            "gltfpack.exe",
        ]
        for candidate in candidates:
            if shutil.which(candidate):
                return candidate
        return None

    async def compress(
        self,
        input_path: Path,
        output_path: Optional[Path] = None,
        settings: Optional[DracoSettings] = None,
    ) -> CompressionResult:
        """
        Compress a GLB/GLTF file with Draco.

        Args:
            input_path: Input file path
            output_path: Output file path (default: adds _draco suffix)
            settings: Compression settings

        Returns:
            CompressionResult with compression stats
        """
        settings = settings or DracoSettings.balanced()
        output_path = output_path or input_path.with_stem(f"{input_path.stem}_draco")

        original_size = input_path.stat().st_size

        try:
            if self.gltfpack_path:
                success = await self._compress_with_gltfpack(
                    input_path, output_path, settings
                )
            elif self.gltf_transform_path:
                success = await self._compress_with_gltf_transform(
                    input_path, output_path, settings
                )
            else:
                logger.error("No Draco compression backend available")
                return CompressionResult(
                    success=False,
                    input_path=input_path,
                    error="No Draco compression tool available (install gltfpack or gltf-transform)",
                )

            if success and output_path.exists():
                compressed_size = output_path.stat().st_size
                ratio = original_size / compressed_size if compressed_size > 0 else 0

                return CompressionResult(
                    success=True,
                    input_path=input_path,
                    output_path=output_path,
                    original_size_bytes=original_size,
                    compressed_size_bytes=compressed_size,
                    compression_ratio=ratio,
                )
            else:
                return CompressionResult(
                    success=False,
                    input_path=input_path,
                    original_size_bytes=original_size,
                    error="Compression failed to produce output file",
                )

        except Exception as e:
            logger.error(f"Draco compression failed: {e}")
            return CompressionResult(
                success=False,
                input_path=input_path,
                original_size_bytes=original_size,
                error=str(e),
            )

    async def _compress_with_gltfpack(
        self,
        input_path: Path,
        output_path: Path,
        settings: DracoSettings,
    ) -> bool:
        """Use gltfpack for Draco compression"""
        try:
            cmd = [
                self.gltfpack_path,
                "-i", str(input_path),
                "-o", str(output_path),
                "-cc",  # Enable compression
                f"-vp", str(settings.position_quantization),
                f"-vn", str(settings.normal_quantization),
                f"-vt", str(settings.uv_quantization),
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                logger.error(f"gltfpack compression failed: {stderr.decode()}")
                return False

            return output_path.exists()

        except Exception as e:
            logger.error(f"gltfpack error: {e}")
            return False

    async def _compress_with_gltf_transform(
        self,
        input_path: Path,
        output_path: Path,
        settings: DracoSettings,
    ) -> bool:
        """Use gltf-transform for Draco compression"""
        try:
            # Build command (npx gltf-transform draco input output [options])
            if self.gltf_transform_path.startswith("npx"):
                cmd = ["npx", "gltf-transform", "draco"]
            else:
                cmd = [self.gltf_transform_path, "draco"]

            cmd.extend([
                str(input_path),
                str(output_path),
                "--quantize-position", str(settings.position_quantization),
                "--quantize-normal", str(settings.normal_quantization),
                "--quantize-texcoord", str(settings.uv_quantization),
                "--quantize-color", str(settings.color_quantization),
            ])

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                logger.error(f"gltf-transform compression failed: {stderr.decode()}")
                return False

            return output_path.exists()

        except Exception as e:
            logger.error(f"gltf-transform error: {e}")
            return False

    async def compress_raw_mesh(
        self,
        vertices: "np.ndarray",
        faces: "np.ndarray",
        normals: Optional["np.ndarray"] = None,
        uvs: Optional["np.ndarray"] = None,
        settings: Optional[DracoSettings] = None,
    ) -> Optional[bytes]:
        """
        Compress raw mesh data to Draco format.

        Args:
            vertices: Nx3 array of vertex positions
            faces: Mx3 array of face indices
            normals: Optional Nx3 array of vertex normals
            uvs: Optional Nx2 array of UV coordinates
            settings: Compression settings

        Returns:
            Compressed Draco bytes, or None on failure
        """
        if not HAS_DRACOPY:
            logger.error("DracoPy not available for raw mesh compression")
            return None

        settings = settings or DracoSettings.balanced()

        try:
            def do_compress():
                # Encode mesh with DracoPy
                encoder = DracoPy.encode(
                    vertices.flatten().tolist(),
                    faces.flatten().tolist(),
                    quantization_bits=settings.position_quantization,
                    compression_level=settings.compression_level,
                )
                return encoder

            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, do_compress)

        except Exception as e:
            logger.error(f"DracoPy compression failed: {e}")
            return None


# Convenience function
async def compress_glb(
    input_path: Path,
    output_path: Optional[Path] = None,
    quality: str = "balanced",
) -> CompressionResult:
    """
    Compress a GLB file with Draco.

    Args:
        input_path: Input GLB file
        output_path: Output path (default: adds _draco suffix)
        quality: Quality preset ("high_quality", "balanced", "high_compression")

    Returns:
        CompressionResult
    """
    compressor = DracoCompressor()

    if quality == "high_quality":
        settings = DracoSettings.high_quality()
    elif quality == "high_compression":
        settings = DracoSettings.high_compression()
    else:
        settings = DracoSettings.balanced()

    return await compressor.compress(input_path, output_path, settings)
