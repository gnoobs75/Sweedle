"""Hunyuan3D-2.1 inference pipeline wrapper."""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Union

from PIL import Image

from src.config import settings, get_inference_dtype
from src.core.device import DeviceManager, get_default_device
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
            device: Device to use (cuda, mps, cpu, or auto)
            low_vram_mode: Enable memory optimizations
        """
        self.model_path = model_path or settings.HUNYUAN_MODEL_PATH
        self.subfolder = subfolder or settings.HUNYUAN_SUBFOLDER

        # Use device manager for cross-platform support
        device_pref = device or settings.DEVICE
        if device_pref == "auto":
            self.device = get_default_device()
        else:
            self.device = device_pref

        self.low_vram_mode = low_vram_mode if low_vram_mode is not None else settings.LOW_VRAM_MODE

        # Initialize device manager for utility methods
        self._device_manager = DeviceManager()

        self._shape_pipeline = None
        self._texture_pipeline = None
        self._preprocessor = ImagePreprocessor()
        self._executor = ThreadPoolExecutor(max_workers=settings.PREPROCESSING_WORKERS)
        self._initialized = False
        self._torch_available = False
        self._lock = asyncio.Lock()

        logger.info(f"Pipeline configured for device: {self.device}")

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

            # Run model warmup to avoid cold start penalty
            if settings.ENABLE_MODEL_WARMUP and self._shape_pipeline is not None:
                logger.info("Running model warmup...")
                self._warmup_model()
                logger.info("Model warmup complete")

            self._initialized = True
            logger.info(f"Hunyuan3D pipeline initialized on {self.device} - pipeline is None: {self._shape_pipeline is None}")

    def _load_models(self) -> None:
        """Synchronous model loading."""
        try:
            import torch
            self._torch_available = True

            # Determine dtype based on config settings (optimized for GPU)
            # Priority: config INFERENCE_DTYPE > low_vram_mode > device default
            if self.device == "mps":
                # MPS works better with float32 in PyTorch 2.x
                dtype = torch.float32
            else:
                # Use optimized dtype from config (bf16 for RTX 40 series)
                dtype = get_inference_dtype()
                if dtype is None:
                    dtype = torch.float16 if self.low_vram_mode else torch.float32

            logger.info(f"Loading models with dtype: {dtype}")

            # Try to import Hunyuan3D
            try:
                from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline

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

                # Move model to device (CUDA or MPS)
                if self.device in ("cuda", "mps"):
                    device_available = (
                        (self.device == "cuda" and torch.cuda.is_available()) or
                        (self.device == "mps" and hasattr(torch.backends, "mps") and torch.backends.mps.is_available())
                    )

                    if device_available:
                        # Note: Don't reassign - hy3dgen's .to() returns None instead of self
                        self._shape_pipeline.to(self.device)
                        logger.info(f"Model loaded on {self.device.upper()} device")
                    else:
                        logger.warning(f"{self.device.upper()} requested but not available, using CPU")
                        self.device = "cpu"

                logger.info(f"Loaded shape pipeline from {self.model_path} (dtype: {dtype})")

                # Try to load texture pipeline (optional, controlled by config)
                # Note: Texture models are in Hunyuan3D-2 repo, not Hunyuan3D-2.1
                if settings.ENABLE_TEXTURE_PIPELINE:
                    try:
                        from hy3dgen.texgen import Hunyuan3DPaintPipeline
                        texture_model_path = "tencent/Hunyuan3D-2"
                        logger.info("Loading texture pipeline (18GB)...")
                        self._texture_pipeline = Hunyuan3DPaintPipeline.from_pretrained(
                            texture_model_path,
                            subfolder='hunyuan3d-paint-v2-0-turbo'
                        )
                        # Keep texture pipeline on CPU at startup to save VRAM
                        # It will be moved to GPU on-demand during texture generation
                        # after shape pipeline is offloaded to CPU
                        logger.info("Loaded texture pipeline (Hunyuan3D-Paint) from tencent/Hunyuan3D-2 (kept on CPU)")
                    except ImportError as e:
                        logger.warning(f"Texture pipeline import failed: {e}. Texture generation disabled.")
                        self._texture_pipeline = None
                    except Exception as e:
                        logger.warning(f"Failed to load texture pipeline: {e}. Texture generation disabled.")
                        self._texture_pipeline = None
                else:
                    logger.info("Texture pipeline disabled by config (ENABLE_TEXTURE_PIPELINE=False)")
                    self._texture_pipeline = None

                logger.info(f"_load_models END - shape pipeline: {self._shape_pipeline is not None}, texture pipeline: {self._texture_pipeline is not None}")
                # Return early to avoid any exception handlers resetting the pipeline
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

    def _warmup_model(self) -> None:
        """Run a quick warmup inference to avoid cold start penalty.

        The first inference after model loading is slower due to:
        - CUDA kernel compilation
        - Memory allocation
        - Model optimization

        Running a minimal warmup pass eliminates this penalty for real jobs.
        """
        if self._shape_pipeline is None:
            return

        try:
            import torch
            import numpy as np

            # Create a small dummy image
            dummy_image = Image.new('RGBA', (512, 512), (128, 128, 128, 255))

            # Use minimal settings for fast warmup
            generator = None
            if self.device != "cpu":
                # MPS doesn't support Generator with device parameter
                gen_device = "cpu" if self.device == "mps" else self.device
                generator = torch.Generator(device=gen_device)
                generator.manual_seed(42)

            # Run a quick inference (minimal steps)
            _ = self._shape_pipeline(
                image=dummy_image,
                num_inference_steps=1,  # Minimal steps for warmup
                guidance_scale=5.5,
                octree_resolution=128,  # Low resolution for speed
                generator=generator,
                output_type='trimesh',
            )

            # Clear the warmup result from memory
            self._device_manager.empty_cache()

            logger.info("Model warmup completed successfully")

        except Exception as e:
            logger.warning(f"Model warmup failed (non-fatal): {e}")
            # Warmup failure is not critical, continue anyway

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
                update_progress(0.70, "Offloading shape model to RAM...")

                # Use VRAM manager for proper cleanup
                from src.inference.vram_manager import prepare_for_texture, get_vram_info

                shape_unloaded = False
                if self._shape_pipeline is not None and self.device == "cuda":
                    try:
                        # Prepare VRAM for texture generation
                        unload_result = prepare_for_texture(self._shape_pipeline)

                        # Check if we have enough VRAM
                        vram_info = get_vram_info()
                        if vram_info['free_gb'] < 16.0:
                            logger.warning(f"Low VRAM ({vram_info['free_gb']:.1f}GB free). Deleting shape pipeline...")
                            self._shape_pipeline_deleted = True
                            del self._shape_pipeline
                            self._shape_pipeline = None

                            # Force cleanup after deletion
                            import gc
                            import torch
                            gc.collect()
                            gc.collect()
                            torch.cuda.empty_cache()
                            torch.cuda.synchronize()

                            vram_info = get_vram_info()
                            logger.info(f"After deletion: {vram_info['free_gb']:.1f}GB free")

                        shape_unloaded = True

                    except Exception as e:
                        logger.warning(f"Could not prepare VRAM for texture: {e}")
                        import traceback
                        traceback.print_exc()

                update_progress(0.71, "Generating texture...")

                mesh = await loop.run_in_executor(
                    self._executor,
                    self._generate_texture,
                    mesh,
                    processed_image,
                    config,
                    lambda p, m: update_progress(0.70 + p * 0.20, m),
                )

                update_progress(0.89, "Texture generated")

                # Move texture pipeline back to CPU to free VRAM for shape pipeline
                if self._texture_pipeline is not None and self.device == "cuda":
                    try:
                        import torch
                        import gc
                        self._texture_pipeline.to("cpu")
                        gc.collect()
                        torch.cuda.empty_cache()
                        logger.info("Texture pipeline moved back to CPU")
                    except Exception as e:
                        logger.warning(f"Could not move texture pipeline to CPU: {e}")

                # Restore shape pipeline for next generation
                if shape_unloaded:
                    try:
                        import torch
                        import gc
                        gc.collect()
                        torch.cuda.empty_cache()

                        if self._shape_pipeline is None and getattr(self, '_shape_pipeline_deleted', False):
                            # Pipeline was deleted - need to reload it
                            logger.info("Reloading shape pipeline...")
                            from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline
                            dtype = get_inference_dtype() or torch.bfloat16
                            self._shape_pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
                                self.model_path,
                                subfolder=self.subfolder,
                                torch_dtype=dtype,
                                use_safetensors=False,
                            )
                            self._shape_pipeline.to(self.device)
                            self._shape_pipeline_deleted = False
                            logger.info("Shape pipeline reloaded to GPU")
                        elif self._shape_pipeline is not None:
                            # Pipeline was moved to CPU - move back to GPU
                            self._shape_pipeline.to(self.device)
                            logger.info("Shape pipeline restored to GPU")
                    except Exception as e:
                        logger.warning(f"Could not restore shape pipeline: {e}")

                update_progress(0.90, "Processing complete")
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
        """Synchronous shape generation with GPU optimizations."""
        logger.info(f"_generate_shape called - pipeline is None: {self._shape_pipeline is None}, initialized: {self._initialized}, id(self): {id(self)}")
        if self._shape_pipeline is None:
            # Shape pipeline was unloaded (e.g., for texture generation)
            # Reload it before generating
            logger.info("Shape pipeline is None - reloading...")
            if progress_callback:
                progress_callback(0.05, "Reloading shape pipeline...")
            self._reload_shape_pipeline()

            if self._shape_pipeline is None:
                # Still None after reload attempt - use mock
                logger.warning("Failed to reload shape pipeline, using mock mesh generation")
                return self._create_mock_mesh()

        try:
            import torch

            generator = None
            if config.seed is not None:
                # MPS doesn't support Generator with device parameter
                # Use CPU generator for MPS, which still provides deterministic results
                gen_device = "cpu" if self.device == "mps" else self.device
                generator = torch.Generator(device=gen_device)
                generator.manual_seed(config.seed)

            # Use inference_mode for optimal performance (faster than no_grad)
            # This disables gradient computation and view tracking
            with torch.inference_mode():
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

            # Force mesh to be CPU-only by converting to trimesh properly
            # This ensures no GPU tensors are attached to the mesh
            try:
                if hasattr(mesh, 'vertices') and hasattr(mesh.vertices, 'cpu'):
                    # If vertices are tensors, convert to numpy
                    import numpy as np
                    vertices = mesh.vertices.cpu().numpy() if hasattr(mesh.vertices, 'cpu') else np.array(mesh.vertices)
                    faces = mesh.faces.cpu().numpy() if hasattr(mesh.faces, 'cpu') else np.array(mesh.faces)

                    import trimesh
                    mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
                    logger.info("Converted mesh to CPU-only trimesh")
            except Exception as e:
                logger.warning(f"Could not convert mesh to CPU: {e}")

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
        """Synchronous texture generation using Hunyuan3D-Paint with GPU optimizations."""
        if self._texture_pipeline is None:
            logger.info("Texture pipeline not available - returning untextured mesh")
            if progress_callback:
                progress_callback(1.0, "Skipping texture (pipeline not loaded)")
            return mesh

        try:
            import torch

            logger.info("Starting texture generation with Hunyuan3D-Paint...")

            # Log VRAM status before texture generation
            if torch.cuda.is_available():
                allocated = torch.cuda.memory_allocated(0) / 1e9
                reserved = torch.cuda.memory_reserved(0) / 1e9
                total = torch.cuda.get_device_properties(0).total_memory / 1e9
                free_vram = total - allocated
                logger.info(f"VRAM before texture: {allocated:.2f}GB allocated, {reserved:.2f}GB reserved, {free_vram:.2f}GB free")

                # Texture pipeline needs ~18GB, warn if not enough
                if free_vram < 16.0:
                    logger.warning(f"Only {free_vram:.2f}GB VRAM free - texture pipeline needs ~18GB!")
                    logger.warning("Texture generation may fail due to insufficient VRAM")
                    logger.warning("Consider disabling texture or restarting backend for clean VRAM state")

            # Debug: log texture pipeline state
            logger.info(f"Texture pipeline check: device={self.device}, pipeline is None={self._texture_pipeline is None}, has 'to'={hasattr(self._texture_pipeline, 'to') if self._texture_pipeline else 'N/A'}")

            # Ensure texture pipeline is on GPU
            if self.device == "cuda" and self._texture_pipeline is not None and hasattr(self._texture_pipeline, 'to'):
                try:
                    # Log before moving
                    logger.info("Moving texture pipeline to CUDA...")
                    self._texture_pipeline.to("cuda")

                    # Log VRAM after moving
                    if torch.cuda.is_available():
                        allocated_after = torch.cuda.memory_allocated(0) / 1e9
                        logger.info(f"Texture pipeline on CUDA. VRAM now: {allocated_after:.2f}GB allocated")
                except RuntimeError as e:
                    if "out of memory" in str(e).lower():
                        logger.error(f"CUDA OOM when loading texture pipeline: {e}")
                        logger.error("Texture generation disabled - returning untextured mesh")
                        if progress_callback:
                            progress_callback(1.0, "Texture skipped (VRAM full)")
                        return mesh
                    raise
                except Exception as e:
                    logger.warning(f"Could not move texture pipeline to CUDA: {e}")

            if progress_callback:
                progress_callback(0.1, "Preparing texture generation...")

            # Use inference_mode for optimal performance
            # Final check before calling texture pipeline
            if self._texture_pipeline is None:
                logger.error("Texture pipeline is None - cannot generate texture")
                if progress_callback:
                    progress_callback(1.0, "Texture skipped (pipeline not available)")
                return mesh

            logger.info(f"Calling texture pipeline... (type: {type(self._texture_pipeline).__name__})")

            # Log mesh stats before texture generation
            mesh_vertices = len(mesh.vertices) if hasattr(mesh, 'vertices') else 0
            mesh_faces = len(mesh.faces) if hasattr(mesh, 'faces') else 0
            logger.info(f"Mesh stats: {mesh_vertices:,} vertices, {mesh_faces:,} faces")

            # For high-poly meshes, simplify before texture to prevent hangs
            # The texture pipeline (Hunyuan3DPaintPipeline) struggles with complex meshes
            MAX_TEXTURE_FACES = 30000  # Safe limit for texture generation
            if mesh_faces > MAX_TEXTURE_FACES and hasattr(mesh, 'simplify_quadric_decimation'):
                logger.info(f"Simplifying mesh from {mesh_faces:,} to {MAX_TEXTURE_FACES:,} faces for texture generation")
                try:
                    # Create a simplified copy for texture, keep original for final output
                    # Use face_count parameter (not percent) for target face count
                    texture_mesh = mesh.simplify_quadric_decimation(face_count=MAX_TEXTURE_FACES)
                    simplified_faces = len(texture_mesh.faces) if hasattr(texture_mesh, 'faces') else 0
                    logger.info(f"Simplified mesh for texture: {simplified_faces:,} faces")
                    # Use simplified mesh for texture generation
                    mesh_for_texture = texture_mesh
                except Exception as e:
                    logger.warning(f"Mesh simplification failed: {e}, using original mesh")
                    mesh_for_texture = mesh
            else:
                mesh_for_texture = mesh

            # For high-poly meshes, warn that texture might be slow
            if mesh_faces > 50000:
                logger.warning(f"High face count ({mesh_faces:,}) - texture may be slow")
                logger.warning("Consider using Fast quality or lower octree resolution")

            try:
                with torch.inference_mode():
                    # Log VRAM right before the call
                    if torch.cuda.is_available():
                        allocated = torch.cuda.memory_allocated(0) / 1e9
                        logger.info(f"VRAM right before texture call: {allocated:.2f}GB")

                    # Run texture generation with progress logging
                    # The paint pipeline takes mesh and image, returns textured mesh
                    logger.info("Executing texture pipeline now...")

                    # Use a simple approach - call directly but add periodic heartbeat via thread
                    import threading
                    import time as time_module

                    texture_start = time_module.time()
                    texture_done = threading.Event()
                    progress_count = [0]  # Mutable counter for progress updates

                    def heartbeat_with_progress():
                        """Send periodic progress updates during texture generation."""
                        # Texture typically takes 60-180 seconds
                        # We'll estimate progress based on elapsed time
                        ESTIMATED_TOTAL_SECONDS = 120.0  # Rough estimate
                        UPDATE_INTERVAL = 5  # Update every 5 seconds for smooth progress

                        while not texture_done.is_set():
                            elapsed = time_module.time() - texture_start
                            progress_count[0] += 1

                            # Calculate estimated progress (cap at 0.95 to leave room for completion)
                            estimated_progress = min(0.95, elapsed / ESTIMATED_TOTAL_SECONDS)

                            # Build status message with elapsed time
                            minutes = int(elapsed // 60)
                            seconds = int(elapsed % 60)
                            if minutes > 0:
                                time_str = f"{minutes}m {seconds}s"
                            else:
                                time_str = f"{seconds}s"

                            if torch.cuda.is_available():
                                try:
                                    allocated = torch.cuda.memory_allocated(0) / 1e9
                                    status_msg = f"Generating texture... {time_str} (VRAM: {allocated:.1f}GB)"
                                except:
                                    status_msg = f"Generating texture... {time_str}"
                            else:
                                status_msg = f"Generating texture... {time_str}"

                            logger.info(status_msg)

                            # Send progress callback if available
                            if progress_callback:
                                try:
                                    # Map to 0.1-0.95 range (leaving room for start/end)
                                    callback_progress = 0.1 + (estimated_progress * 0.85)
                                    progress_callback(callback_progress, status_msg)
                                except Exception as e:
                                    logger.warning(f"Progress callback failed: {e}")

                            texture_done.wait(timeout=UPDATE_INTERVAL)

                    # Start heartbeat thread
                    heartbeat_thread = threading.Thread(target=heartbeat_with_progress, daemon=True)
                    heartbeat_thread.start()

                    try:
                        textured_mesh = self._texture_pipeline(
                            mesh=mesh_for_texture,
                            image=image,
                        )
                    finally:
                        texture_done.set()
                        heartbeat_thread.join(timeout=1)

                    texture_elapsed = time_module.time() - texture_start
                    logger.info(f"Texture pipeline returned after {texture_elapsed:.1f}s")

                    # Force CUDA sync to catch any async errors
                    if torch.cuda.is_available():
                        torch.cuda.synchronize()
                        logger.info("CUDA synchronized after texture")
                logger.info("Texture pipeline call completed")
            except RuntimeError as cuda_error:
                if "out of memory" in str(cuda_error).lower():
                    logger.error(f"CUDA OOM during texture generation: {cuda_error}")
                    # Log memory state
                    if torch.cuda.is_available():
                        allocated = torch.cuda.memory_allocated(0) / 1e9
                        reserved = torch.cuda.memory_reserved(0) / 1e9
                        total = torch.cuda.get_device_properties(0).total_memory / 1e9
                        logger.error(f"VRAM state: {allocated:.2f}GB/{total:.2f}GB allocated, {reserved:.2f}GB reserved")
                raise

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

        # Log mesh type for debugging
        logger.info(f"Mesh type: {type(mesh).__name__}")

        # Convert Scene to single mesh if needed for decimation
        working_mesh = mesh
        is_scene = isinstance(mesh, trimesh.Scene)

        if is_scene:
            # Combine all geometries into single mesh for decimation
            try:
                geometries = list(mesh.geometry.values())
                if geometries:
                    working_mesh = trimesh.util.concatenate(geometries)
                    logger.info(f"Combined {len(geometries)} geometries into single mesh")
            except Exception as e:
                logger.warning(f"Could not combine scene geometries: {e}")
                # Try to get the first geometry
                if mesh.geometry:
                    working_mesh = list(mesh.geometry.values())[0]

        # Get initial counts
        initial_faces = len(working_mesh.faces) if hasattr(working_mesh, 'faces') else 0
        logger.info(f"Initial mesh: {initial_faces:,} faces, target: {config.face_count or 'none'}")

        # Apply face count limit if specified
        if config.face_count and hasattr(working_mesh, 'faces'):
            current_faces = len(working_mesh.faces)
            if current_faces > config.face_count:
                try:
                    # Calculate reduction ratio (fraction to REDUCE by, not keep)
                    # e.g., going from 77k to 10k = reduce by 87% = 0.87
                    target_reduction = 1.0 - (config.face_count / current_faces)
                    target_reduction = max(0.01, min(0.99, target_reduction))  # Clamp to valid range
                    logger.info(f"Decimating: {current_faces:,} -> ~{config.face_count:,} faces (reducing by {target_reduction:.1%})")

                    # Use target_reduction parameter (fraction to reduce BY)
                    working_mesh = working_mesh.simplify_quadric_decimation(target_reduction)

                    final_faces = len(working_mesh.faces) if hasattr(working_mesh, 'faces') else 0
                    logger.info(f"Decimated mesh: {current_faces:,} -> {final_faces:,} faces")
                    # Use decimated mesh for saving
                    mesh = working_mesh
                except Exception as e:
                    logger.warning(f"Decimation failed: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                logger.info(f"No decimation needed: {current_faces:,} faces <= {config.face_count:,} target")

        # Get final counts from the mesh we'll save
        if hasattr(mesh, 'vertices'):
            vertex_count = len(mesh.vertices)
        elif isinstance(mesh, trimesh.Scene):
            vertex_count = sum(len(g.vertices) for g in mesh.geometry.values() if hasattr(g, 'vertices'))
        else:
            vertex_count = 0

        if hasattr(mesh, 'faces'):
            face_count = len(mesh.faces)
        elif isinstance(mesh, trimesh.Scene):
            face_count = sum(len(g.faces) for g in mesh.geometry.values() if hasattr(g, 'faces'))
        else:
            face_count = 0

        logger.info(f"Final mesh: {vertex_count:,} vertices, {face_count:,} faces")

        # Save mesh
        output_path.parent.mkdir(parents=True, exist_ok=True)
        mesh.export(str(output_path))
        logger.info(f"Saved mesh to {output_path}")

        # Generate thumbnail using matplotlib-based renderer (works headlessly)
        try:
            self._generate_thumbnail_matplotlib(mesh, thumbnail_path)
        except Exception as e:
            logger.warning(f"Thumbnail generation failed: {e}")

        return vertex_count, face_count

    def _generate_thumbnail_matplotlib(
        self,
        mesh,
        thumbnail_path: Path,
        width: int = 256,
        height: int = 256,
    ) -> None:
        """Generate thumbnail using matplotlib (works headlessly on Windows)."""
        try:
            import matplotlib
            matplotlib.use('Agg')  # Headless backend
            import matplotlib.pyplot as plt
            from mpl_toolkits.mplot3d.art3d import Poly3DCollection
            import numpy as np
            from PIL import Image
            import io

            # Get vertices and faces
            if hasattr(mesh, 'geometry') and mesh.geometry:
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
                    logger.warning("No geometry found for thumbnail")
                    return
            else:
                vertices = mesh.vertices
                faces = mesh.faces

            # Create figure
            fig = plt.figure(figsize=(width/100, height/100), dpi=100)
            ax = fig.add_subplot(111, projection='3d')

            # Dark background
            bg_color = (0.1, 0.1, 0.12)
            ax.set_facecolor(bg_color)
            fig.patch.set_facecolor(bg_color)

            # Subsample faces for performance
            max_faces = 5000
            if len(faces) > max_faces:
                indices = np.random.choice(len(faces), max_faces, replace=False)
                faces_sample = faces[indices]
            else:
                faces_sample = faces

            # Create polygon collection
            poly3d = [[vertices[idx] for idx in face] for face in faces_sample]
            collection = Poly3DCollection(poly3d, alpha=0.9, linewidth=0.1, edgecolor='#444444')
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

            # Set camera angle (30 degrees pitch, 45 degrees yaw)
            ax.view_init(elev=30, azim=45)

            # Hide axes
            ax.set_axis_off()

            # Render to file
            thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(str(thumbnail_path), format='png', facecolor=fig.get_facecolor(),
                       edgecolor='none', bbox_inches='tight', pad_inches=0, dpi=100)
            plt.close(fig)

            # Resize to exact dimensions
            img = Image.open(thumbnail_path)
            img = img.resize((width, height), Image.Resampling.LANCZOS)
            img.save(thumbnail_path)

            logger.info(f"Generated thumbnail: {thumbnail_path}")

        except Exception as e:
            logger.warning(f"Matplotlib thumbnail failed: {e}")

    def _reload_shape_pipeline(self) -> None:
        """Reload the shape pipeline after it was unloaded for VRAM management.

        This is called when a new generation is requested but the shape pipeline
        was deleted to make room for texture generation in a previous run.
        """
        logger.info("Reloading shape pipeline...")

        try:
            import torch
            import gc

            # Ensure VRAM is clean before reload
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()

                # Log VRAM state
                allocated = torch.cuda.memory_allocated(0) / 1e9
                total = torch.cuda.get_device_properties(0).total_memory / 1e9
                logger.info(f"VRAM before reload: {allocated:.1f}GB / {total:.1f}GB")

            # Get dtype
            dtype = get_inference_dtype()
            if dtype is None:
                dtype = torch.bfloat16 if self.device == "cuda" else torch.float32

            logger.info(f"Loading shape pipeline with dtype: {dtype}")

            # Import and load
            from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline

            try:
                self._shape_pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
                    self.model_path,
                    subfolder=self.subfolder,
                    torch_dtype=dtype,
                    use_safetensors=False,
                )
            except (FileNotFoundError, TypeError) as e:
                logger.warning(f"First reload attempt failed: {e}, trying alternative...")
                self._shape_pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
                    self.model_path,
                    torch_dtype=dtype,
                )

            # Move to device
            if self.device in ("cuda", "mps"):
                device_available = (
                    (self.device == "cuda" and torch.cuda.is_available()) or
                    (self.device == "mps" and hasattr(torch.backends, "mps") and torch.backends.mps.is_available())
                )

                if device_available:
                    self._shape_pipeline.to(self.device)
                    logger.info(f"Shape pipeline reloaded on {self.device.upper()}")
                else:
                    logger.warning(f"{self.device.upper()} not available, using CPU")
                    self.device = "cpu"

            # Clear the deleted flag
            self._shape_pipeline_deleted = False

            # Log success
            if torch.cuda.is_available():
                allocated = torch.cuda.memory_allocated(0) / 1e9
                logger.info(f"VRAM after reload: {allocated:.1f}GB")

            logger.info("Shape pipeline reload complete")

        except ImportError as e:
            logger.error(f"Failed to import hy3dgen for reload: {e}")
            self._shape_pipeline = None

        except Exception as e:
            logger.error(f"Shape pipeline reload failed: {e}")
            import traceback
            traceback.print_exc()
            self._shape_pipeline = None

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

            # Clear GPU cache (CUDA or MPS)
            self._device_manager.empty_cache()

            self._initialized = False
            if self._preprocessor:
                self._preprocessor.cleanup()
            if self._executor:
                self._executor.shutdown(wait=False)

            logger.info(f"Hunyuan3D pipeline cleaned up (device: {self.device})")


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


# =============================================================================
# Standalone functions for PipelineManager integration
# =============================================================================
# These functions work with pre-loaded pipelines from PipelineManager,
# enabling clean stage-based VRAM management.


async def generate_mesh(
    pipeline,
    image: Image.Image,
    config: GenerationConfig,
    output_dir: Path,
    asset_id: str,
    progress_callback: Optional[ProgressCallback] = None,
) -> GenerationResult:
    """
    Generate a 3D mesh from an image using a pre-loaded shape pipeline.

    This is a standalone function that works with PipelineManager - the pipeline
    should already be loaded and on GPU before calling this function.

    Args:
        pipeline: Pre-loaded shape pipeline (Hunyuan3DDiTFlowMatchingPipeline)
        image: Preprocessed PIL Image (background already removed)
        config: Generation configuration
        output_dir: Directory to save output files
        asset_id: Asset ID for naming
        progress_callback: Optional callback for progress updates

    Returns:
        GenerationResult with mesh path and statistics
    """
    import torch
    import trimesh
    from concurrent.futures import ThreadPoolExecutor

    start_time = time.time()
    executor = ThreadPoolExecutor(max_workers=2)
    loop = asyncio.get_running_loop()

    def update_progress(progress: float, stage: str):
        if progress_callback:
            progress_callback(progress, stage)

    try:
        update_progress(0.0, "Starting mesh generation...")

        # Step 1: Run shape generation
        update_progress(0.05, "Generating 3D shape...")

        # Create a holder for tqdm progress that can be shared with the executor
        tqdm_progress_holder = {"stage": "", "percent": 0.0, "current": 0, "total": 0}

        def run_shape_generation():
            """Synchronous shape generation with tqdm capture."""
            from src.core.tqdm_capture import capture_tqdm_progress

            generator = None
            if config.seed is not None:
                gen_device = "cuda" if torch.cuda.is_available() else "cpu"
                generator = torch.Generator(device=gen_device)
                generator.manual_seed(config.seed)

            # Callback for tqdm progress - updates the holder
            def on_tqdm_progress(stage: str, percent: float, current: int, total: int):
                tqdm_progress_holder["stage"] = stage
                tqdm_progress_holder["percent"] = percent
                tqdm_progress_holder["current"] = current
                tqdm_progress_holder["total"] = total
                # Map tqdm stages to overall progress (5% to 70%)
                # Diffusion Sampling is 5-50%, Volume Decoding is 50-70%
                if "Diffusion" in stage:
                    overall = 0.05 + percent * 0.45
                elif "Volume" in stage or "Decod" in stage:
                    overall = 0.50 + percent * 0.20
                else:
                    overall = 0.05 + percent * 0.60
                # Call the progress callback with detailed stage info
                if progress_callback:
                    progress_callback(overall, f"{stage}: {current}/{total}")

            with torch.inference_mode():
                # Capture tqdm output during inference
                with capture_tqdm_progress(on_tqdm_progress, min_update_interval=0.3):
                    result = pipeline(
                        image=image,
                        num_inference_steps=config.inference_steps,
                        guidance_scale=config.guidance_scale,
                        octree_resolution=config.octree_resolution,
                        generator=generator,
                        output_type='trimesh',
                    )

            mesh = result[0] if isinstance(result, (list, tuple)) else result

            # Convert to CPU-only trimesh
            try:
                if hasattr(mesh, 'vertices') and hasattr(mesh.vertices, 'cpu'):
                    import numpy as np
                    vertices = mesh.vertices.cpu().numpy() if hasattr(mesh.vertices, 'cpu') else np.array(mesh.vertices)
                    faces = mesh.faces.cpu().numpy() if hasattr(mesh.faces, 'cpu') else np.array(mesh.faces)
                    mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
            except Exception as e:
                logger.warning(f"Could not convert mesh to CPU: {e}")

            return mesh

        mesh = await loop.run_in_executor(executor, run_shape_generation)
        update_progress(0.70, "Shape generated")

        # Step 2: Post-process - decimation if needed
        if config.face_count and hasattr(mesh, 'faces'):
            current_faces = len(mesh.faces)
            if current_faces > config.face_count:
                update_progress(0.75, f"Decimating mesh ({current_faces:,} -> {config.face_count:,} faces)...")

                def decimate():
                    target_faces = config.face_count
                    logger.info(f"Decimating: {current_faces:,} -> {target_faces:,} faces")
                    # Use face_count parameter (not percent) for target face count
                    return mesh.simplify_quadric_decimation(face_count=target_faces)

                mesh = await loop.run_in_executor(executor, decimate)
                logger.info(f"Decimated to {len(mesh.faces):,} faces")

        update_progress(0.85, "Saving mesh...")

        # Step 3: Save mesh
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{asset_id}.{config.output_format.value}"

        def save_mesh():
            mesh.export(str(output_path))
            return len(mesh.vertices), len(mesh.faces)

        vertex_count, face_count = await loop.run_in_executor(executor, save_mesh)
        logger.info(f"Saved mesh: {vertex_count:,} vertices, {face_count:,} faces")

        # Step 4: Generate thumbnail
        update_progress(0.92, "Generating thumbnail...")
        thumbnail_path = output_dir / "thumbnail.png"

        def generate_thumbnail():
            try:
                import matplotlib
                matplotlib.use('Agg')
                import matplotlib.pyplot as plt
                from mpl_toolkits.mplot3d.art3d import Poly3DCollection
                import numpy as np

                fig = plt.figure(figsize=(2.56, 2.56), facecolor='#1a1a2e')
                ax = fig.add_subplot(111, projection='3d', facecolor='#1a1a2e')

                vertices = np.array(mesh.vertices)
                faces = np.array(mesh.faces)

                # Sample faces for performance
                if len(faces) > 5000:
                    indices = np.random.choice(len(faces), 5000, replace=False)
                    faces_sample = faces[indices]
                else:
                    faces_sample = faces

                poly = Poly3DCollection(
                    vertices[faces_sample],
                    alpha=1.0,
                    facecolor='#4a90d9',
                    edgecolor='#2d5a87',
                    linewidth=0.1,
                )
                ax.add_collection3d(poly)

                # Set limits
                center = vertices.mean(axis=0)
                max_range = np.abs(vertices - center).max() * 1.2
                ax.set_xlim([center[0] - max_range, center[0] + max_range])
                ax.set_ylim([center[1] - max_range, center[1] + max_range])
                ax.set_zlim([center[2] - max_range, center[2] + max_range])
                ax.set_axis_off()
                ax.view_init(elev=20, azim=45)

                thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
                fig.savefig(str(thumbnail_path), format='png', facecolor=fig.get_facecolor(),
                           bbox_inches='tight', pad_inches=0, dpi=100)
                plt.close(fig)

                # Resize
                from PIL import Image as PILImage
                img = PILImage.open(thumbnail_path)
                img = img.resize((256, 256), PILImage.Resampling.LANCZOS)
                img.save(thumbnail_path)

                return True
            except Exception as e:
                logger.warning(f"Thumbnail failed: {e}")
                return False

        await loop.run_in_executor(executor, generate_thumbnail)

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
        logger.exception(f"Mesh generation failed: {e}")
        return GenerationResult(
            success=False,
            error=str(e),
            generation_time=time.time() - start_time,
            parameters=config.to_dict(),
        )
    finally:
        executor.shutdown(wait=False)


async def generate_texture_on_mesh(
    pipeline,
    mesh,
    image: Image.Image,
    output_path: Path,
    progress_callback: Optional[ProgressCallback] = None,
) -> tuple[bool, Optional[str]]:
    """
    Add texture to an existing mesh using a pre-loaded texture pipeline.

    This is a standalone function that works with PipelineManager - the texture
    pipeline should already be loaded and on GPU before calling this function.

    Args:
        pipeline: Pre-loaded texture pipeline (Hunyuan3DPaintPipeline)
        mesh: Trimesh mesh to texture
        image: Source image for texture generation
        output_path: Path to save textured mesh
        progress_callback: Optional callback for progress updates

    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    import torch
    import threading
    import time as time_module

    loop = asyncio.get_running_loop()

    def update_progress(progress: float, stage: str):
        if progress_callback:
            progress_callback(progress, stage)

    try:
        logger.info("generate_texture_on_mesh called")
        update_progress(0.0, "Starting texture generation...")

        if pipeline is None:
            logger.error("Texture pipeline is None!")
            return False, "Texture pipeline not loaded"

        logger.info(f"Pipeline type: {type(pipeline)}")
        logger.info(f"Mesh type: {type(mesh)}, vertices: {len(mesh.vertices) if hasattr(mesh, 'vertices') else 'N/A'}")
        logger.info(f"Image type: {type(image)}, size: {image.size if hasattr(image, 'size') else 'N/A'}")

        # Log VRAM before texture and verify we have enough headroom
        if torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated(0) / 1e9
            total = torch.cuda.get_device_properties(0).total_memory / 1e9
            free_vram = total - allocated
            logger.info(f"VRAM before texture: {allocated:.2f}GB allocated, {free_vram:.2f}GB free")

            # Verify we have enough VRAM for texture generation
            # Texture needs ~10GB additional headroom during inference
            MIN_FREE_VRAM = 8.0
            if free_vram < MIN_FREE_VRAM:
                error_msg = (
                    f"Insufficient VRAM for texture: {free_vram:.1f}GB free (need {MIN_FREE_VRAM}GB). "
                    f"Try clearing other GPU applications or reducing mesh complexity."
                )
                logger.error(error_msg)
                return False, error_msg

        # Simplify mesh if too complex for texture
        # Conservative limit for stability - can increase once stable
        MAX_TEXTURE_FACES = 15000  # Reduced from 30000 for stability
        mesh_for_texture = mesh
        if hasattr(mesh, 'faces') and len(mesh.faces) > MAX_TEXTURE_FACES:
            update_progress(0.1, f"Simplifying mesh for texture ({len(mesh.faces):,} -> {MAX_TEXTURE_FACES:,} faces)...")
            try:
                mesh_for_texture = mesh.simplify_quadric_decimation(face_count=MAX_TEXTURE_FACES)
                logger.info(f"Simplified to {len(mesh_for_texture.faces):,} faces for texture")
            except Exception as e:
                logger.warning(f"Simplification failed: {e}, using original mesh")

        logger.info(f"Mesh for texture: {len(mesh_for_texture.faces):,} faces")
        update_progress(0.2, "Generating texture...")

        # Use a heartbeat thread to show progress while texture generates
        texture_done = threading.Event()
        texture_start = time_module.time()

        def heartbeat_with_progress():
            """Background thread to log progress during texture generation."""
            UPDATE_INTERVAL = 5.0
            while not texture_done.is_set():
                elapsed = time_module.time() - texture_start
                # Log VRAM during generation
                vram_str = ""
                if torch.cuda.is_available():
                    try:
                        allocated = torch.cuda.memory_allocated(0) / 1e9
                        vram_str = f" (VRAM: {allocated:.1f}GB)"
                    except:
                        pass
                logger.info(f"Texture generation in progress... {elapsed:.1f}s elapsed{vram_str}")
                if progress_callback:
                    estimated_progress = min(0.9, 0.2 + (elapsed / 60.0) * 0.7)
                    try:
                        progress_callback(estimated_progress, f"Generating texture ({elapsed:.0f}s)...")
                    except Exception:
                        pass
                texture_done.wait(timeout=UPDATE_INTERVAL)

        heartbeat_thread = threading.Thread(target=heartbeat_with_progress, daemon=True)
        heartbeat_thread.start()

        # Run texture generation in thread pool (like the working version)
        # The hy3dgen library handles CUDA context properly within its own threads
        def run_texture_sync():
            """Synchronous texture generation to run in executor."""
            logger.info("run_texture_sync: starting texture pipeline call...")
            try:
                with torch.inference_mode():
                    result = pipeline(
                        mesh=mesh_for_texture,
                        image=image,
                    )
                logger.info(f"run_texture_sync: pipeline returned, type={type(result)}")
                return result
            except Exception as e:
                logger.exception(f"run_texture_sync: exception during pipeline call: {e}")
                raise

        try:
            logger.info("Calling texture pipeline via run_in_executor...")

            # Timeout protection: 90 seconds for texture generation with CPU offloading
            # With CPU offloading and 512px/2 views, should complete in ~30-60s
            # This prevents hanging forever if CUDA kernel stalls
            TEXTURE_TIMEOUT_SECONDS = 90

            try:
                textured_mesh = await asyncio.wait_for(
                    loop.run_in_executor(None, run_texture_sync),
                    timeout=TEXTURE_TIMEOUT_SECONDS
                )
                logger.info(f"Texture pipeline returned successfully")
            except asyncio.TimeoutError:
                texture_elapsed = time_module.time() - texture_start
                # Get VRAM state for debugging
                vram_info = ""
                if torch.cuda.is_available():
                    try:
                        allocated = torch.cuda.memory_allocated(0) / 1e9
                        vram_info = f" (VRAM at timeout: {allocated:.1f}GB)"
                    except:
                        pass
                error_msg = (
                    f"Texture generation timed out after {texture_elapsed:.0f}s.{vram_info} "
                    f"Try simplifying the mesh or reducing texture resolution."
                )
                logger.error(error_msg)
                return False, error_msg

        finally:
            texture_done.set()
            heartbeat_thread.join(timeout=1)

        texture_elapsed = time_module.time() - texture_start
        logger.info(f"Texture generation complete in {texture_elapsed:.1f}s")

        # Force CUDA sync to catch any async errors
        if torch.cuda.is_available():
            torch.cuda.synchronize()
            logger.info("CUDA synchronized after texture")

        update_progress(0.9, "Saving textured mesh...")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        textured_mesh.export(str(output_path))

        update_progress(1.0, "Texture complete")
        logger.info(f"Saved textured mesh to {output_path}")

        return True, None

    except Exception as e:
        logger.exception(f"Texture generation failed: {e}")
        return False, str(e)
