"""Hunyuan3D-2.1 inference pipeline wrapper."""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Union

from PIL import Image

from src.config import settings
from src.inference.config import GenerationConfig, OutputFormat
from src.inference.preprocessor import ImagePreprocessor

logger = logging.getLogger(__name__)

# Type alias for progress callback
ProgressCallback = Callable[[float, str], None]


@dataclass
class GenerationResult:
    """Result from 3D generation."""
    success: bool
    mesh_path: Optional[Path] = None
    thumbnail_path: Optional[Path] = None
    vertex_count: int = 0
    face_count: int = 0
    generation_time: float = 0.0
    parameters: Optional[dict] = None
    error: Optional[str] = None


class Hunyuan3DPipeline:
    """Wrapper for Hunyuan3D-2.1 shape and texture generation.

    Provides async interface with progress callbacks for integration
    with the job queue and WebSocket updates.
    """

    def __init__(
        self,
        model_path: str = None,
        subfolder: str = None,
        device: str = None,
        low_vram_mode: bool = None,
    ):
        """Initialize pipeline.

        Args:
            model_path: HuggingFace model path or local path
            subfolder: Model subfolder
            device: Device to use (cuda, cpu)
            low_vram_mode: Enable memory optimizations
        """
        self.model_path = model_path or settings.HUNYUAN_MODEL_PATH
        self.subfolder = subfolder or settings.HUNYUAN_SUBFOLDER
        self.device = device or settings.DEVICE
        self.low_vram_mode = low_vram_mode if low_vram_mode is not None else settings.LOW_VRAM_MODE

        self._shape_pipeline = None
        self._texture_pipeline = None
        self._preprocessor = ImagePreprocessor()
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._initialized = False
        self._torch_available = False
        self._lock = asyncio.Lock()

    @property
    def is_initialized(self) -> bool:
        """Check if pipeline is initialized."""
        return self._initialized

    async def initialize(self) -> None:
        """Load models into GPU memory."""
        async with self._lock:
            if self._initialized:
                return

            logger.info("Initializing Hunyuan3D pipeline...")

            # Load synchronously to avoid threading issues
            # The ThreadPoolExecutor was causing the pipeline object to not be visible
            # after the executor returned
            self._load_models()

            self._initialized = True
            logger.info(f"Hunyuan3D pipeline initialized - pipeline is None: {self._shape_pipeline is None}, id(self): {id(self)}")

    def _load_models(self) -> None:
        """Synchronous model loading."""
        try:
            import torch
            self._torch_available = True

            # Try to import Hunyuan3D
            try:
                from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline

                dtype = torch.float16 if self.low_vram_mode else torch.float32

                # Try loading - hy3dgen will auto-download and handle model files
                try:
                    self._shape_pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
                        self.model_path,
                        subfolder=self.subfolder,
                        torch_dtype=dtype,
                        use_safetensors=False,  # Use .ckpt file instead
                    )
                except (FileNotFoundError, TypeError) as e:
                    logger.warning(f"First load attempt failed: {e}, trying alternative...")
                    # Try without subfolder or safetensors param
                    self._shape_pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
                        self.model_path,
                        torch_dtype=dtype,
                    )

                if self.device == "cuda" and torch.cuda.is_available():
                    # Note: Don't reassign - hy3dgen's .to() returns None instead of self
                    self._shape_pipeline.to(self.device)
                    logger.info(f"Shape model loaded on CUDA device")

                logger.info(f"Loaded shape pipeline from {self.model_path}")

                # Try to load texture pipeline
                # Note: Texture models are in Hunyuan3D-2 repo, not Hunyuan3D-2.1
                try:
                    from hy3dgen.texgen import Hunyuan3DPaintPipeline
                    texture_model_path = "tencent/Hunyuan3D-2"
                    self._texture_pipeline = Hunyuan3DPaintPipeline.from_pretrained(
                        texture_model_path,
                        subfolder='hunyuan3d-paint-v2-0-turbo'
                    )
                    logger.info("Loaded texture pipeline (Hunyuan3D-Paint) from tencent/Hunyuan3D-2")
                except ImportError as e:
                    logger.warning(f"Texture pipeline import failed: {e}. Texture generation disabled.")
                    self._texture_pipeline = None
                except Exception as e:
                    logger.warning(f"Failed to load texture pipeline: {e}. Texture generation disabled.")
                    self._texture_pipeline = None

                logger.info(f"_load_models END - shape pipeline: {self._shape_pipeline is not None}, texture pipeline: {self._texture_pipeline is not None}")
                return

            except ImportError:
                logger.warning(
                    "Hunyuan3D (hy3dgen) not installed. "
                    "Running in mock mode for development."
                )
                self._shape_pipeline = None

            except FileNotFoundError as e:
                logger.warning(
                    f"Hunyuan3D model files not found: {e}. "
                    "Running in mock mode. Download model from Hugging Face."
                )
                self._shape_pipeline = None

            except Exception as e:
                logger.warning(
                    f"Failed to load Hunyuan3D model: {e}. "
                    "Running in mock mode for development."
                )
                self._shape_pipeline = None

        except ImportError:
            logger.warning(
                "PyTorch not installed. Running in mock mode for development. "
                "Install torch for actual 3D generation."
            )
            self._torch_available = False
            self._shape_pipeline = None

        except Exception as e:
            logger.error(f"Unexpected error loading models: {e}")
            self._shape_pipeline = None

    async def generate(
        self,
        image: Union[str, Path, Image.Image],
        config: GenerationConfig,
        output_dir: Path,
        asset_id: str,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> GenerationResult:
        """Generate 3D model from image.

        Args:
            image: Input image path or PIL Image
            config: Generation configuration
            output_dir: Directory to save outputs
            asset_id: Unique asset identifier
            progress_callback: Optional callback for progress updates

        Returns:
            GenerationResult with paths and metadata
        """
        logger.info(f"generate() called - initialized: {self._initialized}, pipeline is None: {self._shape_pipeline is None}, id(self): {id(self)}")
        start_time = time.time()

        def update_progress(progress: float, message: str):
            if progress_callback:
                try:
                    progress_callback(progress, message)
                except Exception as e:
                    logger.warning(f"Progress callback failed: {e}")

        try:
            # Ensure initialized
            if not self._initialized:
                update_progress(0.0, "Loading models...")
                await self.initialize()

            # Create output directory
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Step 1: Preprocess image (5-15%)
            update_progress(0.05, "Preprocessing image...")

            if isinstance(image, (str, Path)):
                processed_image = await self._preprocessor.prepare_image(
                    image,
                    target_size=512,
                    remove_bg=True,
                )
                # Save processed image
                processed_path = output_dir / "input_processed.png"
                await self._preprocessor.save_processed(processed_image, processed_path)
            else:
                processed_image = image
                processed_path = None

            update_progress(0.15, "Image preprocessed")

            # Step 2: Generate shape (15-70%)
            update_progress(0.15, "Generating 3D shape...")

            loop = asyncio.get_event_loop()
            mesh = await loop.run_in_executor(
                self._executor,
                self._generate_shape,
                processed_image,
                config,
                lambda p, m: update_progress(0.15 + p * 0.55, m),
            )

            update_progress(0.70, "Shape generated")

            # Step 3: Generate texture if enabled (70-90%)
            if config.texture.enabled and mesh is not None:
                update_progress(0.70, "Generating texture...")

                mesh = await loop.run_in_executor(
                    self._executor,
                    self._generate_texture,
                    mesh,
                    processed_image,
                    config,
                    lambda p, m: update_progress(0.70 + p * 0.20, m),
                )

                update_progress(0.90, "Texture generated")
            else:
                update_progress(0.90, "Skipping texture")

            # Step 4: Post-process and save (90-100%)
            update_progress(0.90, "Saving mesh...")

            output_path = output_dir / f"{asset_id}.{config.output_format.value}"
            thumbnail_path = output_dir / "thumbnail.png"

            vertex_count, face_count = await loop.run_in_executor(
                self._executor,
                self._save_mesh,
                mesh,
                output_path,
                thumbnail_path,
                config,
            )

            generation_time = time.time() - start_time
            update_progress(1.0, "Complete")

            return GenerationResult(
                success=True,
                mesh_path=output_path,
                thumbnail_path=thumbnail_path if thumbnail_path.exists() else None,
                vertex_count=vertex_count,
                face_count=face_count,
                generation_time=generation_time,
                parameters=config.to_dict(),
            )

        except Exception as e:
            logger.exception(f"Generation failed: {e}")
            return GenerationResult(
                success=False,
                error=str(e),
                generation_time=time.time() - start_time,
                parameters=config.to_dict(),
            )

    def _generate_shape(
        self,
        image: Image.Image,
        config: GenerationConfig,
        progress_callback: Optional[Callable] = None,
    ):
        """Synchronous shape generation."""
        logger.info(f"_generate_shape called - pipeline is None: {self._shape_pipeline is None}, initialized: {self._initialized}, id(self): {id(self)}")
        if self._shape_pipeline is None:
            # Mock mode - create a simple placeholder mesh
            logger.warning("Using mock mesh generation")
            return self._create_mock_mesh()

        try:
            import torch

            generator = None
            if config.seed is not None:
                generator = torch.Generator(device=self.device)
                generator.manual_seed(config.seed)

            # Run shape generation
            result = self._shape_pipeline(
                image=image,
                num_inference_steps=config.inference_steps,
                guidance_scale=config.guidance_scale,
                octree_resolution=config.octree_resolution,
                generator=generator,
                output_type='trimesh',
            )

            mesh = result[0] if isinstance(result, (list, tuple)) else result

            if progress_callback:
                progress_callback(1.0, "Shape complete")

            return mesh

        except Exception as e:
            logger.error(f"Shape generation failed: {e}")
            raise

    def _generate_texture(
        self,
        mesh,
        image: Image.Image,
        config: GenerationConfig,
        progress_callback: Optional[Callable] = None,
    ):
        """Synchronous texture generation using Hunyuan3D-Paint."""
        if self._texture_pipeline is None:
            logger.info("Texture pipeline not available - returning untextured mesh")
            if progress_callback:
                progress_callback(1.0, "Skipping texture (pipeline not loaded)")
            return mesh

        try:
            logger.info("Starting texture generation with Hunyuan3D-Paint...")
            if progress_callback:
                progress_callback(0.1, "Preparing texture generation...")

            # Run texture generation
            # The paint pipeline takes mesh and image, returns textured mesh
            textured_mesh = self._texture_pipeline(
                mesh=mesh,
                image=image,
            )

            if progress_callback:
                progress_callback(1.0, "Texture generation complete")

            logger.info("Texture generation completed successfully")
            return textured_mesh

        except Exception as e:
            logger.error(f"Texture generation failed: {e}")
            import traceback
            traceback.print_exc()
            if progress_callback:
                progress_callback(1.0, f"Texture failed: {str(e)[:50]}")
            # Return original mesh without texture on failure
            return mesh

    def _save_mesh(
        self,
        mesh,
        output_path: Path,
        thumbnail_path: Path,
        config: GenerationConfig,
    ) -> tuple[int, int]:
        """Save mesh to file and generate thumbnail."""
        try:
            import trimesh
        except ImportError:
            logger.error("trimesh not installed, cannot save mesh")
            return 0, 0

        if mesh is None:
            mesh = self._create_mock_mesh()

        if mesh is None:
            logger.error("No mesh to save")
            return 0, 0

        # Apply face count limit if specified
        if config.face_count and hasattr(mesh, 'faces'):
            if len(mesh.faces) > config.face_count:
                try:
                    mesh = mesh.simplify_quadric_decimation(config.face_count)
                    logger.info(f"Simplified mesh to {config.face_count} faces")
                except Exception as e:
                    logger.warning(f"Simplification failed: {e}")

        # Get counts
        vertex_count = len(mesh.vertices) if hasattr(mesh, 'vertices') else 0
        face_count = len(mesh.faces) if hasattr(mesh, 'faces') else 0

        # Save mesh
        output_path.parent.mkdir(parents=True, exist_ok=True)
        mesh.export(str(output_path))
        logger.info(f"Saved mesh to {output_path}")

        # Generate thumbnail
        try:
            scene = mesh.scene() if hasattr(mesh, 'scene') else trimesh.Scene(mesh)
            png_data = scene.save_image(resolution=(256, 256))
            if png_data:
                with open(thumbnail_path, 'wb') as f:
                    f.write(png_data)
                logger.info(f"Saved thumbnail to {thumbnail_path}")
        except Exception as e:
            logger.warning(f"Thumbnail generation failed: {e}")

        return vertex_count, face_count

    def _create_mock_mesh(self):
        """Create a mock mesh for testing without GPU."""
        try:
            import trimesh
            # Create a simple cube for testing
            mesh = trimesh.creation.box(extents=[1, 1, 1])
            logger.info("Created mock cube mesh for testing")
            return mesh
        except ImportError:
            logger.warning("trimesh not installed, returning None")
            return None

    async def cleanup(self) -> None:
        """Release GPU memory."""
        async with self._lock:
            if self._shape_pipeline is not None:
                del self._shape_pipeline
                self._shape_pipeline = None

            if self._texture_pipeline is not None:
                del self._texture_pipeline
                self._texture_pipeline = None

            # Clear CUDA cache
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except (ImportError, Exception):
                pass

            self._initialized = False
            if self._preprocessor:
                self._preprocessor.cleanup()
            if self._executor:
                self._executor.shutdown(wait=False)

            logger.info("Hunyuan3D pipeline cleaned up")


# Global pipeline instance (singleton)
_pipeline: Optional[Hunyuan3DPipeline] = None


def get_pipeline() -> Hunyuan3DPipeline:
    """Get or create the global pipeline instance."""
    global _pipeline
    if _pipeline is None:
        _pipeline = Hunyuan3DPipeline()
        logger.info(f"Created new pipeline instance id(pipeline): {id(_pipeline)}")
    else:
        logger.info(f"Returning existing pipeline instance id(pipeline): {id(_pipeline)}")
    return _pipeline


async def initialize_pipeline() -> Hunyuan3DPipeline:
    """Initialize and return the global pipeline."""
    pipeline = get_pipeline()
    await pipeline.initialize()
    return pipeline
