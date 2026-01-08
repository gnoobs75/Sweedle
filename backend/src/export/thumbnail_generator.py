"""
Thumbnail Generator - Generate preview thumbnails for 3D assets

Uses headless rendering with pyrender or trimesh to create thumbnails.
"""

import asyncio
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Tuple
import io
import math

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

try:
    import pyrender
    import numpy as np
    HAS_PYRENDER = True
except ImportError:
    HAS_PYRENDER = False

logger = logging.getLogger(__name__)


@dataclass
class ThumbnailResult:
    """Result of thumbnail generation"""
    success: bool
    source_path: Path
    thumbnail_path: Optional[Path] = None
    width: int = 0
    height: int = 0
    file_size_bytes: int = 0
    error: Optional[str] = None


@dataclass
class ThumbnailSettings:
    """Settings for thumbnail generation"""
    width: int = 512
    height: int = 512
    background_color: Tuple[float, float, float, float] = (0.1, 0.1, 0.1, 1.0)
    camera_distance_factor: float = 2.0  # Multiplier for auto camera distance
    camera_angle: Tuple[float, float] = (30, 45)  # Pitch, yaw in degrees
    ambient_light: float = 0.3
    directional_light: float = 0.7
    format: str = "png"  # png, jpg, webp
    quality: int = 90  # For jpg/webp

    @classmethod
    def high_quality(cls) -> "ThumbnailSettings":
        """High quality settings"""
        return cls(width=1024, height=1024, quality=95)

    @classmethod
    def preview(cls) -> "ThumbnailSettings":
        """Quick preview settings"""
        return cls(width=256, height=256, quality=80)


class ThumbnailGenerator:
    """
    Generates preview thumbnails for 3D mesh files.

    Uses pyrender for high-quality rendering when available,
    falls back to trimesh's built-in rendering.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir

        if not HAS_TRIMESH:
            raise ImportError("trimesh is required for thumbnail generation")

        if not HAS_PIL:
            raise ImportError("Pillow is required for thumbnail generation")

    async def generate(
        self,
        mesh_path: Path,
        output_path: Optional[Path] = None,
        settings: Optional[ThumbnailSettings] = None,
    ) -> ThumbnailResult:
        """
        Generate a thumbnail for a 3D mesh file.

        Args:
            mesh_path: Path to the mesh file (GLB, GLTF, OBJ, etc.)
            output_path: Path for output thumbnail (auto-generated if None)
            settings: Thumbnail generation settings

        Returns:
            ThumbnailResult with generated thumbnail info
        """
        settings = settings or ThumbnailSettings()
        output_path = output_path or self._get_output_path(mesh_path, settings)

        try:
            if HAS_PYRENDER:
                image = await self._render_with_pyrender(mesh_path, settings)
            else:
                image = await self._render_with_trimesh(mesh_path, settings)

            if image is None:
                return ThumbnailResult(
                    success=False,
                    source_path=mesh_path,
                    error="Failed to render thumbnail",
                )

            # Save image
            output_path.parent.mkdir(parents=True, exist_ok=True)

            if settings.format.lower() == "jpg":
                image = image.convert("RGB")
                image.save(output_path, "JPEG", quality=settings.quality)
            elif settings.format.lower() == "webp":
                image.save(output_path, "WEBP", quality=settings.quality)
            else:
                image.save(output_path, "PNG")

            return ThumbnailResult(
                success=True,
                source_path=mesh_path,
                thumbnail_path=output_path,
                width=image.width,
                height=image.height,
                file_size_bytes=output_path.stat().st_size,
            )

        except Exception as e:
            logger.error(f"Thumbnail generation failed: {e}")
            return ThumbnailResult(
                success=False,
                source_path=mesh_path,
                error=str(e),
            )

    def _get_output_path(self, mesh_path: Path, settings: ThumbnailSettings) -> Path:
        """Generate output path for thumbnail"""
        output_dir = self.output_dir or mesh_path.parent
        ext = settings.format.lower()
        if ext == "jpg":
            ext = "jpeg"
        return output_dir / f"{mesh_path.stem}_thumb.{ext}"

    async def _render_with_pyrender(
        self,
        mesh_path: Path,
        settings: ThumbnailSettings,
    ) -> Optional[Image.Image]:
        """Render using pyrender (high quality)"""
        def do_render():
            # Load mesh
            mesh = trimesh.load(str(mesh_path))

            # Create scene
            scene = pyrender.Scene(
                bg_color=settings.background_color,
                ambient_light=np.array([settings.ambient_light] * 3),
            )

            # Add mesh(es) to scene
            if hasattr(mesh, 'geometry'):
                for geom in mesh.geometry.values():
                    if hasattr(geom, 'vertices'):
                        py_mesh = pyrender.Mesh.from_trimesh(geom)
                        scene.add(py_mesh)
            else:
                py_mesh = pyrender.Mesh.from_trimesh(mesh)
                scene.add(py_mesh)

            # Calculate camera position
            bounds = mesh.bounds
            center = (bounds[0] + bounds[1]) / 2
            size = np.linalg.norm(bounds[1] - bounds[0])
            distance = size * settings.camera_distance_factor

            # Camera angles
            pitch = math.radians(settings.camera_angle[0])
            yaw = math.radians(settings.camera_angle[1])

            # Calculate camera position
            cam_x = center[0] + distance * math.cos(pitch) * math.sin(yaw)
            cam_y = center[1] + distance * math.sin(pitch)
            cam_z = center[2] + distance * math.cos(pitch) * math.cos(yaw)

            # Create camera
            camera = pyrender.PerspectiveCamera(yfov=np.pi / 4.0)
            camera_pose = np.eye(4)
            camera_pose[:3, 3] = [cam_x, cam_y, cam_z]

            # Look at center
            forward = center - np.array([cam_x, cam_y, cam_z])
            forward = forward / np.linalg.norm(forward)
            right = np.cross(np.array([0, 1, 0]), forward)
            right = right / np.linalg.norm(right)
            up = np.cross(forward, right)

            camera_pose[:3, 0] = right
            camera_pose[:3, 1] = up
            camera_pose[:3, 2] = -forward

            scene.add(camera, pose=camera_pose)

            # Add directional light
            light = pyrender.DirectionalLight(
                color=np.ones(3),
                intensity=settings.directional_light,
            )
            light_pose = np.eye(4)
            light_pose[:3, 3] = [cam_x, cam_y + distance, cam_z]
            scene.add(light, pose=light_pose)

            # Render
            renderer = pyrender.OffscreenRenderer(settings.width, settings.height)
            color, _ = renderer.render(scene)
            renderer.delete()

            return Image.fromarray(color)

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, do_render)

    async def _render_with_trimesh(
        self,
        mesh_path: Path,
        settings: ThumbnailSettings,
    ) -> Optional[Image.Image]:
        """Render using trimesh's built-in viewer (fallback)"""
        def do_render():
            mesh = trimesh.load(str(mesh_path))

            # Use trimesh's scene rendering
            scene = mesh if hasattr(mesh, 'geometry') else trimesh.Scene(mesh)

            # Calculate camera transform
            bounds = scene.bounds
            center = (bounds[0] + bounds[1]) / 2
            size = np.linalg.norm(bounds[1] - bounds[0])
            distance = size * settings.camera_distance_factor

            pitch = math.radians(settings.camera_angle[0])
            yaw = math.radians(settings.camera_angle[1])

            cam_x = center[0] + distance * math.cos(pitch) * math.sin(yaw)
            cam_y = center[1] + distance * math.sin(pitch)
            cam_z = center[2] + distance * math.cos(pitch) * math.cos(yaw)

            # Set camera
            camera_transform = trimesh.transformations.look_at(
                eye=[cam_x, cam_y, cam_z],
                target=center,
                up=[0, 1, 0],
            )

            scene.camera_transform = camera_transform

            # Render to PNG bytes
            png_bytes = scene.save_image(
                resolution=(settings.width, settings.height),
                visible=False,
            )

            return Image.open(io.BytesIO(png_bytes))

        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, do_render)
        except Exception as e:
            logger.warning(f"Trimesh rendering failed: {e}, trying simple approach")
            return await self._render_simple(mesh_path, settings)

    async def _render_simple(
        self,
        mesh_path: Path,
        settings: ThumbnailSettings,
    ) -> Optional[Image.Image]:
        """Simple placeholder thumbnail when rendering fails"""
        def do_render():
            # Create a simple placeholder with mesh info
            img = Image.new('RGBA', (settings.width, settings.height),
                          tuple(int(c * 255) for c in settings.background_color))

            # Try to get mesh info
            try:
                mesh = trimesh.load(str(mesh_path))
                if hasattr(mesh, 'geometry'):
                    vertex_count = sum(len(g.vertices) for g in mesh.geometry.values() if hasattr(g, 'vertices'))
                    face_count = sum(len(g.faces) for g in mesh.geometry.values() if hasattr(g, 'faces'))
                else:
                    vertex_count = len(mesh.vertices) if hasattr(mesh, 'vertices') else 0
                    face_count = len(mesh.faces) if hasattr(mesh, 'faces') else 0

                # Draw text info (if we have PIL ImageDraw)
                try:
                    from PIL import ImageDraw
                    draw = ImageDraw.Draw(img)
                    text = f"3D Model\n{vertex_count:,} verts\n{face_count:,} faces"
                    draw.text((10, 10), text, fill=(255, 255, 255, 200))
                except:
                    pass
            except:
                pass

            return img

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, do_render)


async def generate_batch_thumbnails(
    mesh_paths: list[Path],
    output_dir: Optional[Path] = None,
    settings: Optional[ThumbnailSettings] = None,
    max_concurrent: int = 4,
) -> list[ThumbnailResult]:
    """
    Generate thumbnails for multiple meshes concurrently.

    Args:
        mesh_paths: List of mesh file paths
        output_dir: Directory for output thumbnails
        settings: Thumbnail settings
        max_concurrent: Maximum concurrent generations

    Returns:
        List of ThumbnailResults
    """
    generator = ThumbnailGenerator(output_dir)
    settings = settings or ThumbnailSettings()

    semaphore = asyncio.Semaphore(max_concurrent)

    async def generate_one(path: Path) -> ThumbnailResult:
        async with semaphore:
            return await generator.generate(path, settings=settings)

    tasks = [generate_one(path) for path in mesh_paths]
    return await asyncio.gather(*tasks)


# Convenience function
async def generate_thumbnail(
    mesh_path: Path,
    output_path: Optional[Path] = None,
    width: int = 512,
    height: int = 512,
) -> ThumbnailResult:
    """Generate a thumbnail for a mesh file"""
    generator = ThumbnailGenerator()
    settings = ThumbnailSettings(width=width, height=height)
    return await generator.generate(mesh_path, output_path, settings)
