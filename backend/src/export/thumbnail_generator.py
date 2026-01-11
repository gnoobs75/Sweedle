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
        """Render using matplotlib (works headlessly on Windows)"""
        def do_render():
            try:
                import matplotlib
                matplotlib.use('Agg')  # Headless backend
                import matplotlib.pyplot as plt
                from mpl_toolkits.mplot3d import Axes3D
                from mpl_toolkits.mplot3d.art3d import Poly3DCollection
                import numpy as np

                mesh = trimesh.load(str(mesh_path))

                # Get vertices and faces from mesh or scene
                if hasattr(mesh, 'geometry') and mesh.geometry:
                    # It's a Scene - combine all geometries
                    all_vertices = []
                    all_faces = []
                    offset = 0
                    for geom in mesh.geometry.values():
                        if hasattr(geom, 'vertices') and hasattr(geom, 'faces'):
                            all_vertices.append(geom.vertices)
                            all_faces.append(geom.faces + offset)
                            offset += len(geom.vertices)
                    if all_vertices:
                        vertices = np.vstack(all_vertices)
                        faces = np.vstack(all_faces)
                    else:
                        raise ValueError("No geometry found")
                else:
                    vertices = mesh.vertices
                    faces = mesh.faces

                # Create figure
                fig = plt.figure(figsize=(settings.width/100, settings.height/100), dpi=100)
                ax = fig.add_subplot(111, projection='3d')

                # Set background color
                bg = settings.background_color[:3]
                ax.set_facecolor(bg)
                fig.patch.set_facecolor(bg)

                # Subsample faces for performance (max 5000 faces for thumbnail)
                max_faces = 5000
                if len(faces) > max_faces:
                    indices = np.random.choice(len(faces), max_faces, replace=False)
                    faces_sample = faces[indices]
                else:
                    faces_sample = faces

                # Create polygon collection
                poly3d = [[vertices[idx] for idx in face] for face in faces_sample]
                collection = Poly3DCollection(poly3d, alpha=0.9, linewidth=0.1, edgecolor='#333333')
                collection.set_facecolor('#6366f1')  # Indigo color
                ax.add_collection3d(collection)

                # Auto-scale
                max_range = np.array([
                    vertices[:, 0].max() - vertices[:, 0].min(),
                    vertices[:, 1].max() - vertices[:, 1].min(),
                    vertices[:, 2].max() - vertices[:, 2].min()
                ]).max() / 2.0

                mid_x = (vertices[:, 0].max() + vertices[:, 0].min()) * 0.5
                mid_y = (vertices[:, 1].max() + vertices[:, 1].min()) * 0.5
                mid_z = (vertices[:, 2].max() + vertices[:, 2].min()) * 0.5

                ax.set_xlim(mid_x - max_range, mid_x + max_range)
                ax.set_ylim(mid_y - max_range, mid_y + max_range)
                ax.set_zlim(mid_z - max_range, mid_z + max_range)

                # Set camera angle
                ax.view_init(elev=settings.camera_angle[0], azim=settings.camera_angle[1])

                # Hide axes
                ax.set_axis_off()

                # Remove padding
                plt.tight_layout(pad=0)

                # Render to image
                buf = io.BytesIO()
                fig.savefig(buf, format='png', facecolor=fig.get_facecolor(),
                           edgecolor='none', bbox_inches='tight', pad_inches=0)
                plt.close(fig)
                buf.seek(0)

                img = Image.open(buf).convert('RGBA')
                # Resize to exact dimensions
                img = img.resize((settings.width, settings.height), Image.Resampling.LANCZOS)
                return img

            except Exception as e:
                logger.warning(f"Matplotlib rendering failed: {e}, using placeholder")
                return self._create_placeholder(mesh_path, settings)

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, do_render)

    def _create_placeholder(
        self,
        mesh_path: Path,
        settings: ThumbnailSettings,
    ) -> Image.Image:
        """Create a simple placeholder thumbnail with mesh info"""
        img = Image.new('RGBA', (settings.width, settings.height),
                      tuple(int(c * 255) for c in settings.background_color))

        try:
            mesh = trimesh.load(str(mesh_path))
            if hasattr(mesh, 'geometry'):
                vertex_count = sum(len(g.vertices) for g in mesh.geometry.values() if hasattr(g, 'vertices'))
                face_count = sum(len(g.faces) for g in mesh.geometry.values() if hasattr(g, 'faces'))
            else:
                vertex_count = len(mesh.vertices) if hasattr(mesh, 'vertices') else 0
                face_count = len(mesh.faces) if hasattr(mesh, 'faces') else 0

            from PIL import ImageDraw
            draw = ImageDraw.Draw(img)

            # Draw a simple 3D box icon
            cx, cy = settings.width // 2, settings.height // 2
            size = min(settings.width, settings.height) // 4

            # Box vertices (isometric projection)
            points = [
                (cx, cy - size),  # top
                (cx + size, cy - size//2),  # right top
                (cx + size, cy + size//2),  # right bottom
                (cx, cy + size),  # bottom
                (cx - size, cy + size//2),  # left bottom
                (cx - size, cy - size//2),  # left top
            ]

            # Draw box faces
            draw.polygon(points, fill=(99, 102, 241, 200), outline=(255, 255, 255, 150))

            # Draw text
            text = f"{vertex_count:,} verts\n{face_count:,} faces"
            draw.text((10, settings.height - 50), text, fill=(255, 255, 255, 200))

        except Exception as e:
            logger.warning(f"Placeholder creation failed: {e}")

        return img


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
