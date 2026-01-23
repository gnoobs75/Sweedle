"""
Stage-Based Pipeline Manager for Sweedle

Manages lazy loading and full unloading of ML pipelines between workflow stages.
Ensures only one large model is on GPU at a time to prevent VRAM overflow.

Pipeline VRAM Requirements:
- Shape (Hunyuan3D-2.1): ~21GB
- Texture (Hunyuan3D-2 Paint): ~18GB
- Rigging: ~0GB (CPU-based)
- Animation: ~0GB (CPU-based)

RTX 4090 (24GB) can handle each stage individually, but NOT simultaneously.
"""

import asyncio
import gc
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class PipelineStage(str, Enum):
    """Workflow stages that may require pipeline loading."""
    IDLE = "idle"
    MESH = "mesh"
    TEXTURE = "texture"
    RIGGING = "rigging"
    ANIMATION = "animation"
    EXPORT = "export"


class PipelineState(str, Enum):
    """Current state of a pipeline."""
    UNLOADED = "unloaded"
    LOADING = "loading"
    READY = "ready"
    UNLOADING = "unloading"
    ERROR = "error"


@dataclass
class PipelineStatus:
    """Current status of the pipeline manager."""
    current_stage: PipelineStage
    shape_state: PipelineState
    texture_state: PipelineState
    vram_used_gb: float
    vram_total_gb: float
    vram_free_gb: float
    last_heartbeat: float
    is_healthy: bool
    status_message: str
    loading_progress: float  # 0.0 - 1.0 during loading


# Progress callback type
ProgressCallback = Callable[[float, str], None]


class PipelineManager:
    """
    Manages lazy loading and full unloading of ML pipelines.

    Key principles:
    1. Only ONE large model on GPU at a time
    2. Full unload between stages (not just .to("cpu"))
    3. Lazy loading - load only when needed
    4. Detailed progress callbacks for UI feedback
    5. Health checks to detect hangs
    """

    def __init__(self):
        self._shape_pipeline = None
        self._texture_pipeline = None
        self._current_stage = PipelineStage.IDLE
        self._shape_state = PipelineState.UNLOADED
        self._texture_state = PipelineState.UNLOADED
        self._loading_progress = 0.0
        self._status_message = "Idle"
        self._last_heartbeat = time.time()
        self._lock = asyncio.Lock()
        self._ws_manager = None  # Set by set_websocket_manager

        # Configuration
        self._shape_model_path = "tencent/Hunyuan3D-2.1"
        self._texture_model_path = "tencent/Hunyuan3D-2"
        self._texture_subfolder = "hunyuan3d-paint-v2-0-turbo"

    def set_websocket_manager(self, ws_manager) -> None:
        """Set the WebSocket manager for broadcasting status updates."""
        self._ws_manager = ws_manager

    def _update_heartbeat(self) -> None:
        """Update heartbeat timestamp."""
        self._last_heartbeat = time.time()

    def _get_vram_info(self) -> dict:
        """Get current VRAM information."""
        try:
            import torch
            if torch.cuda.is_available():
                allocated = torch.cuda.memory_allocated(0) / 1e9
                total = torch.cuda.get_device_properties(0).total_memory / 1e9
                return {
                    "used_gb": round(allocated, 2),
                    "total_gb": round(total, 2),
                    "free_gb": round(total - allocated, 2),
                }
        except Exception:
            pass
        return {"used_gb": 0, "total_gb": 24, "free_gb": 24}

    def get_status(self) -> PipelineStatus:
        """Get current pipeline manager status."""
        vram = self._get_vram_info()
        time_since_heartbeat = time.time() - self._last_heartbeat

        return PipelineStatus(
            current_stage=self._current_stage,
            shape_state=self._shape_state,
            texture_state=self._texture_state,
            vram_used_gb=vram["used_gb"],
            vram_total_gb=vram["total_gb"],
            vram_free_gb=vram["free_gb"],
            last_heartbeat=self._last_heartbeat,
            is_healthy=time_since_heartbeat < 60,  # Unhealthy if no heartbeat for 60s
            status_message=self._status_message,
            loading_progress=self._loading_progress,
        )

    async def _broadcast_status(self, message: str, progress: float = None) -> None:
        """Broadcast status update via WebSocket."""
        self._status_message = message
        if progress is not None:
            self._loading_progress = progress
        self._update_heartbeat()

        if self._ws_manager:
            status = self.get_status()
            await self._ws_manager.broadcast({
                "type": "pipeline_status",
                "stage": status.current_stage.value,
                "shape_state": status.shape_state.value,
                "texture_state": status.texture_state.value,
                "vram_used_gb": status.vram_used_gb,
                "vram_free_gb": status.vram_free_gb,
                "vram_total_gb": status.vram_total_gb,
                "message": message,
                "progress": self._loading_progress,
                "is_healthy": status.is_healthy,
                "timestamp": time.time(),
            })

    async def prepare_for_stage(
        self,
        stage: PipelineStage,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> dict:
        """
        Prepare VRAM for a specific workflow stage.

        This is the main entry point. It will:
        1. Fully unload any currently loaded pipelines
        2. Load the required pipeline for the stage
        3. Return status information

        Args:
            stage: The stage to prepare for
            progress_callback: Optional callback for progress updates

        Returns:
            Dict with success status and details
        """
        async with self._lock:
            self._current_stage = stage
            start_time = time.time()

            logger.info(f"Preparing for stage: {stage.value}")
            await self._broadcast_status(f"Preparing for {stage.value}...", 0.0)

            if progress_callback:
                progress_callback(0.0, f"Preparing for {stage.value}...")

            try:
                # Step 1: Full unload of everything
                await self._full_unload(progress_callback)

                # Step 2: Load required pipeline for stage
                if stage == PipelineStage.MESH:
                    result = await self._load_shape_pipeline(progress_callback)
                elif stage == PipelineStage.TEXTURE:
                    result = await self._load_texture_pipeline(progress_callback)
                elif stage in (PipelineStage.RIGGING, PipelineStage.ANIMATION, PipelineStage.EXPORT):
                    # These stages don't need GPU pipelines
                    result = {"success": True, "vram_used_gb": 0, "message": "No GPU model needed"}
                    await self._broadcast_status(f"Ready for {stage.value}", 1.0)
                    if progress_callback:
                        progress_callback(1.0, f"Ready for {stage.value}")
                else:
                    result = {"success": True, "vram_used_gb": 0}

                elapsed = time.time() - start_time
                result["elapsed_seconds"] = elapsed
                result["stage"] = stage.value

                logger.info(f"Stage preparation complete: {stage.value} in {elapsed:.1f}s")
                return result

            except Exception as e:
                logger.exception(f"Failed to prepare for stage {stage.value}: {e}")
                self._shape_state = PipelineState.ERROR
                self._texture_state = PipelineState.ERROR
                await self._broadcast_status(f"Error: {str(e)[:50]}", 0.0)
                return {
                    "success": False,
                    "error": str(e),
                    "stage": stage.value,
                }

    async def _full_unload(self, progress_callback: Optional[ProgressCallback] = None) -> None:
        """
        Completely unload ALL pipelines and free ALL VRAM.

        This is aggressive cleanup - we delete everything and force garbage collection.
        Uses deep cleanup to ensure VRAM is in a clean state before loading new pipelines.
        """
        import torch

        vram_before = self._get_vram_info()["used_gb"]
        logger.info(f"===== FULL UNLOAD STARTING =====")
        logger.info(f"VRAM before unload: {vram_before:.2f}GB")
        logger.info(f"Shape pipeline loaded: {self._shape_pipeline is not None}")
        logger.info(f"Texture pipeline loaded: {self._texture_pipeline is not None}")

        await self._broadcast_status("Unloading pipelines...", 0.1)
        if progress_callback:
            progress_callback(0.1, "Unloading pipelines...")

        # Unload shape pipeline with deep cleanup
        if self._shape_pipeline is not None:
            self._shape_state = PipelineState.UNLOADING
            logger.info("--- Unloading SHAPE pipeline ---")
            await self._broadcast_status("Unloading shape model...", 0.15)

            try:
                # Deep cleanup: Move components to CPU first before deletion
                # This ensures GPU tensors are properly released
                logger.info("Running deep cleanup on shape pipeline...")
                self._deep_cleanup_pipeline(self._shape_pipeline, "shape")
                vram_after_cleanup = self._get_vram_info()["used_gb"]
                logger.info(f"Shape deep cleanup done. VRAM now: {vram_after_cleanup:.2f}GB")
            except Exception as e:
                logger.warning(f"Error during shape pipeline cleanup: {e}")

            try:
                # Try to free model hooks if available
                if hasattr(self._shape_pipeline, 'maybe_free_model_hooks'):
                    logger.info("Freeing shape model hooks...")
                    self._shape_pipeline.maybe_free_model_hooks()
                    logger.info("Shape model hooks freed")
            except Exception as e:
                logger.warning(f"Error freeing shape model hooks: {e}")

            # Delete the pipeline
            logger.info("Deleting shape pipeline reference...")
            del self._shape_pipeline
            self._shape_pipeline = None
            self._shape_state = PipelineState.UNLOADED
            logger.info("Shape pipeline deleted and set to None")

        # Unload texture pipeline with deep cleanup
        if self._texture_pipeline is not None:
            self._texture_state = PipelineState.UNLOADING
            logger.info("--- Unloading TEXTURE pipeline ---")
            await self._broadcast_status("Unloading texture model...", 0.2)

            try:
                # Deep cleanup for texture pipeline
                logger.info("Running deep cleanup on texture pipeline...")
                self._deep_cleanup_pipeline(self._texture_pipeline, "texture")
                vram_after_cleanup = self._get_vram_info()["used_gb"]
                logger.info(f"Texture deep cleanup done. VRAM now: {vram_after_cleanup:.2f}GB")
            except Exception as e:
                logger.warning(f"Error during texture pipeline cleanup: {e}")

            try:
                if hasattr(self._texture_pipeline, 'maybe_free_model_hooks'):
                    logger.info("Freeing texture model hooks...")
                    self._texture_pipeline.maybe_free_model_hooks()
                    logger.info("Texture model hooks freed")
            except Exception as e:
                logger.warning(f"Error freeing texture model hooks: {e}")

            logger.info("Deleting texture pipeline reference...")
            del self._texture_pipeline
            self._texture_pipeline = None
            self._texture_state = PipelineState.UNLOADED
            logger.info("Texture pipeline deleted and set to None")

        await self._broadcast_status("Clearing GPU memory...", 0.25)
        if progress_callback:
            progress_callback(0.25, "Clearing GPU memory...")

        # Aggressive garbage collection (run before CUDA cleanup)
        logger.info("--- Running garbage collection (3 passes) ---")
        gc.collect()
        logger.info("GC pass 1 complete")
        gc.collect()
        logger.info("GC pass 2 complete")
        gc.collect()
        logger.info("GC pass 3 complete")

        # Clear CUDA cache with full synchronization
        if torch.cuda.is_available():
            logger.info("--- Clearing CUDA cache ---")
            # Sync to ensure all pending CUDA operations complete
            logger.info("Synchronizing CUDA (waiting for pending ops)...")
            torch.cuda.synchronize()
            logger.info("CUDA synchronized")

            # Empty the cache
            logger.info("Emptying CUDA cache...")
            torch.cuda.empty_cache()
            vram_after_cache = self._get_vram_info()["used_gb"]
            logger.info(f"CUDA cache emptied. VRAM now: {vram_after_cache:.2f}GB")

            # IPC collect if available (helps with multiprocess scenarios)
            if hasattr(torch.cuda, 'ipc_collect'):
                logger.info("Running CUDA IPC collect...")
                torch.cuda.ipc_collect()
                logger.info("CUDA IPC collect done")

            # Reset memory stats for clean tracking
            try:
                logger.info("Resetting CUDA peak memory stats...")
                torch.cuda.reset_peak_memory_stats()
                logger.info("Peak memory stats reset")
            except Exception:
                pass

            # Final sync
            logger.info("Final CUDA synchronization...")
            torch.cuda.synchronize()
            logger.info("Final sync complete")

        # Final garbage collection
        logger.info("Final garbage collection pass...")
        gc.collect()
        logger.info("Final GC complete")

        vram_after = self._get_vram_info()["used_gb"]
        freed = vram_before - vram_after

        logger.info(f"===== FULL UNLOAD COMPLETE =====")
        logger.info(f"VRAM: {vram_before:.2f}GB -> {vram_after:.2f}GB (freed {freed:.2f}GB)")

        # Verify VRAM is in a clean state (< 2GB should be just driver overhead)
        if vram_after > 2.0:
            logger.warning(f"VRAM not fully cleared: {vram_after:.2f}GB still in use. "
                          f"This may indicate leaked tensors or driver overhead.")
            # Try one more aggressive cleanup
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.synchronize()
                torch.cuda.empty_cache()
            gc.collect()
            vram_final = self._get_vram_info()["used_gb"]
            if vram_final < vram_after:
                logger.info(f"Additional cleanup freed {vram_after - vram_final:.2f}GB -> {vram_final:.2f}GB")
                vram_after = vram_final

        await self._broadcast_status(f"VRAM cleared: {vram_after:.1f}GB used", 0.3)
        if progress_callback:
            progress_callback(0.3, f"VRAM cleared: {vram_after:.1f}GB used")

    def _deep_cleanup_pipeline(self, pipeline, name: str) -> None:
        """
        Deep cleanup of a pipeline to ensure all GPU tensors are released.

        Moves components to CPU before deletion to ensure proper VRAM release.
        """
        import torch

        if pipeline is None:
            logger.info(f"Deep cleanup skipped: {name} pipeline is None")
            return

        logger.info(f"Deep cleanup starting for {name} pipeline...")
        components_moved = 0
        components_failed = 0

        # Common pipeline components that may hold GPU tensors
        components_to_move = [
            'model', 'conditioner', 'vae', 'scheduler',
            'text_encoder', 'image_encoder', 'unet',
            'denoiser', 'renderer', 'encoder', 'decoder'
        ]

        for comp_name in components_to_move:
            if hasattr(pipeline, comp_name):
                comp = getattr(pipeline, comp_name)
                if comp is not None:
                    try:
                        if hasattr(comp, 'to'):
                            comp.to('cpu')
                            logger.info(f"  Moved {name}.{comp_name} to CPU")
                            components_moved += 1
                    except Exception as e:
                        logger.warning(f"  Could not move {name}.{comp_name} to CPU: {e}")
                        components_failed += 1

        # Check for components dict (hy3dgen style)
        if hasattr(pipeline, 'components') and isinstance(pipeline.components, dict):
            logger.info(f"Processing {name}.components dict ({len(pipeline.components)} items)...")
            for comp_name, comp in pipeline.components.items():
                if comp is not None and hasattr(comp, 'to'):
                    try:
                        comp.to('cpu')
                        logger.info(f"  Moved {name}.components.{comp_name} to CPU")
                        components_moved += 1
                    except Exception as e:
                        logger.warning(f"  Could not move {name}.components.{comp_name} to CPU: {e}")
                        components_failed += 1

        # Handle VAE's surface extractor specially (can have cached GPU tensors)
        if hasattr(pipeline, 'vae') and pipeline.vae is not None:
            vae = pipeline.vae
            if hasattr(vae, 'surface_extractor'):
                se = vae.surface_extractor
                logger.info(f"Cleaning up {name}.vae.surface_extractor...")
                # DMCSurfaceExtractor caches self.dmc on GPU
                if hasattr(se, 'dmc') and se.dmc is not None:
                    try:
                        if hasattr(se.dmc, 'to'):
                            se.dmc.to('cpu')
                            logger.info(f"  Moved {name}.vae.surface_extractor.dmc to CPU")
                        else:
                            del se.dmc
                            se.dmc = None
                            logger.info(f"  Deleted {name}.vae.surface_extractor.dmc")
                        components_moved += 1
                    except Exception as e:
                        logger.warning(f"  Could not clean up {name}.vae.surface_extractor.dmc: {e}")
                        components_failed += 1

        logger.info(f"Deep cleanup complete for {name}: {components_moved} moved, {components_failed} failed")

    async def _load_shape_pipeline(self, progress_callback: Optional[ProgressCallback] = None) -> dict:
        """Load the shape generation pipeline (Hunyuan3D-2.1)."""
        import torch
        from src.config import get_inference_dtype

        logger.info("===== LOADING SHAPE PIPELINE =====")
        logger.info(f"Model path: {self._shape_model_path}")
        logger.info(f"Subfolder: hunyuan3d-dit-v2-1")

        self._shape_state = PipelineState.LOADING
        await self._broadcast_status("Loading shape model (21GB)...", 0.35)
        if progress_callback:
            progress_callback(0.35, "Loading shape model (21GB)...")

        vram_start = self._get_vram_info()
        logger.info(f"VRAM before load: {vram_start['used_gb']:.2f}GB")

        try:
            # Import the pipeline class
            logger.info("Importing Hunyuan3DDiTFlowMatchingPipeline...")
            await self._broadcast_status("Importing Hunyuan3D...", 0.4)
            if progress_callback:
                progress_callback(0.4, "Importing Hunyuan3D...")

            from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline
            logger.info("Import successful")

            # Get optimal dtype
            dtype = get_inference_dtype()
            if dtype is None:
                dtype = torch.bfloat16
            logger.info(f"Using dtype: {dtype}")

            await self._broadcast_status("Downloading/loading model weights...", 0.45)
            if progress_callback:
                progress_callback(0.45, "Downloading/loading model weights...")

            # Load the model (this takes time - downloads if not cached)
            logger.info("Loading model from pretrained (this may take a while)...")
            logger.info("  - Checking HuggingFace cache...")
            load_start = time.time()

            self._shape_pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
                self._shape_model_path,
                subfolder="hunyuan3d-dit-v2-1",
                torch_dtype=dtype,
                use_safetensors=False,
            )

            load_time = time.time() - load_start
            logger.info(f"Model loaded from pretrained in {load_time:.1f}s")
            vram_after_load = self._get_vram_info()
            logger.info(f"VRAM after load (before GPU move): {vram_after_load['used_gb']:.2f}GB")

            await self._broadcast_status("Moving model to GPU...", 0.8)
            if progress_callback:
                progress_callback(0.8, "Moving model to GPU...")

            # Move to GPU
            if torch.cuda.is_available():
                logger.info("Moving shape pipeline to CUDA...")
                move_start = time.time()
                self._shape_pipeline.to("cuda")
                move_time = time.time() - move_start
                logger.info(f"Model moved to CUDA in {move_time:.1f}s")
            else:
                logger.warning("CUDA not available - model staying on CPU")

            self._shape_state = PipelineState.READY
            vram = self._get_vram_info()

            await self._broadcast_status(f"Shape model ready ({vram['used_gb']:.1f}GB)", 1.0)
            if progress_callback:
                progress_callback(1.0, f"Shape model ready ({vram['used_gb']:.1f}GB)")

            logger.info("===== SHAPE PIPELINE READY =====")
            logger.info(f"VRAM used: {vram['used_gb']:.2f}GB (loaded {vram['used_gb'] - vram_start['used_gb']:.2f}GB)")

            return {
                "success": True,
                "pipeline": "shape",
                "vram_used_gb": vram["used_gb"],
                "message": "Shape pipeline ready",
            }

        except Exception as e:
            self._shape_state = PipelineState.ERROR
            logger.exception(f"Failed to load shape pipeline: {e}")
            await self._broadcast_status(f"Error loading shape model: {str(e)[:50]}", 0.0)
            raise

    async def _load_texture_pipeline(self, progress_callback: Optional[ProgressCallback] = None) -> dict:
        """Load the texture generation pipeline (Hunyuan3D-2 Paint)."""
        import torch

        logger.info("===== LOADING TEXTURE PIPELINE =====")
        logger.info(f"Model path: {self._texture_model_path}")
        logger.info(f"Subfolder: {self._texture_subfolder}")

        self._texture_state = PipelineState.LOADING
        await self._broadcast_status("Loading texture model (18GB)...", 0.35)
        if progress_callback:
            progress_callback(0.35, "Loading texture model (18GB)...")

        vram_start = self._get_vram_info()
        logger.info(f"VRAM before load: {vram_start['used_gb']:.2f}GB")

        try:
            logger.info("Importing Hunyuan3DPaintPipeline...")
            await self._broadcast_status("Importing Hunyuan3D Paint...", 0.4)
            if progress_callback:
                progress_callback(0.4, "Importing Hunyuan3D Paint...")

            from hy3dgen.texgen import Hunyuan3DPaintPipeline
            logger.info("Import successful")

            await self._broadcast_status("Downloading/loading texture weights...", 0.45)
            if progress_callback:
                progress_callback(0.45, "Downloading/loading texture weights...")

            # Load the texture pipeline
            # Note: Hunyuan3DPaintPipeline is NOT an nn.Module - it doesn't have .to()
            # It loads its internal models to CUDA automatically in load_models()
            logger.info("Loading texture model from pretrained (this may take a while)...")
            logger.info("  - Checking HuggingFace cache...")
            load_start = time.time()

            self._texture_pipeline = Hunyuan3DPaintPipeline.from_pretrained(
                self._texture_model_path,
                subfolder=self._texture_subfolder,
            )

            load_time = time.time() - load_start
            logger.info(f"Texture model loaded from pretrained in {load_time:.1f}s")
            vram_after_load = self._get_vram_info()
            logger.info(f"VRAM after load: {vram_after_load['used_gb']:.2f}GB")

            # CRITICAL: Enable CPU offloading to prevent VRAM spike
            # This keeps models on CPU and only loads them to GPU when needed
            # Without this, all models load to GPU at once causing 17GB+ VRAM usage
            logger.info("Enabling CPU offloading for texture pipeline...")
            if hasattr(self._texture_pipeline, 'enable_model_cpu_offload'):
                try:
                    self._texture_pipeline.enable_model_cpu_offload()
                    logger.info("CPU offloading ENABLED - models will move to GPU only when needed")
                    logger.info("This prevents VRAM spike from 17GB+ to ~10-12GB peak")
                except Exception as e:
                    logger.warning(f"Could not enable CPU offloading: {e}")
                    logger.warning("WARNING: Without CPU offloading, texture may use 17GB+ VRAM!")
            else:
                logger.warning("Texture pipeline does not support enable_model_cpu_offload()")
                logger.warning("WARNING: Texture generation may use excessive VRAM!")

            vram_after_offload = self._get_vram_info()
            logger.info(f"VRAM after offload config: {vram_after_offload['used_gb']:.2f}GB")

            # Texture quality settings for Godot game-ready assets
            # 1024px with 4 views provides good quality without excessive VRAM
            # CPU offloading keeps peak VRAM manageable
            TARGET_RESOLUTION = 1024  # Game-quality textures
            logger.info(f"Configuring texture settings: target resolution = {TARGET_RESOLUTION}px")

            if hasattr(self._texture_pipeline, 'render'):
                render = self._texture_pipeline.render
                old_render = getattr(render, 'default_resolution', 2048)
                old_texture = getattr(render, 'texture_size', 2048)
                # Use proper setter methods to update the render object
                if hasattr(render, 'set_default_render_resolution'):
                    render.set_default_render_resolution(TARGET_RESOLUTION)
                    logger.info(f"  Render resolution: {old_render} -> {TARGET_RESOLUTION}")
                if hasattr(render, 'set_default_texture_resolution'):
                    render.set_default_texture_resolution(TARGET_RESOLUTION)
                    logger.info(f"  Texture resolution: {old_texture} -> {TARGET_RESOLUTION}")
            else:
                logger.warning("Texture pipeline has no 'render' attribute - using defaults")

            # Use 4 camera views for good coverage (front, right, back, left)
            # This provides full horizontal coverage for game-ready textures
            if hasattr(self._texture_pipeline, 'config'):
                config = self._texture_pipeline.config
                old_views = len(getattr(config, 'candidate_camera_azims', []))
                # 4 horizontal views for game-quality textures
                config.candidate_camera_azims = [0, 90, 180, 270]  # Front, right, back, left
                config.candidate_camera_elevs = [0, 0, 0, 0]
                config.candidate_view_weights = [1.0, 0.5, 0.5, 0.5]  # Front weighted higher
                config.render_size = TARGET_RESOLUTION
                config.texture_size = TARGET_RESOLUTION
                logger.info(f"  Camera views: {old_views} -> 4 (front, right, back, left)")
                logger.info(f"  View weights: [1.0, 0.5, 0.5, 0.5] (front emphasized)")
            else:
                logger.warning("Texture pipeline has no 'config' attribute - using default views")

            await self._broadcast_status("Texture model loaded", 0.9)
            if progress_callback:
                progress_callback(0.9, "Texture model loaded")

            self._texture_state = PipelineState.READY
            vram = self._get_vram_info()

            await self._broadcast_status(f"Texture model ready ({vram['used_gb']:.1f}GB)", 1.0)
            if progress_callback:
                progress_callback(1.0, f"Texture model ready ({vram['used_gb']:.1f}GB)")

            logger.info("===== TEXTURE PIPELINE READY =====")
            logger.info(f"VRAM used: {vram['used_gb']:.2f}GB (loaded {vram['used_gb'] - vram_start['used_gb']:.2f}GB)")

            return {
                "success": True,
                "pipeline": "texture",
                "vram_used_gb": vram["used_gb"],
                "message": "Texture pipeline ready",
            }

        except Exception as e:
            self._texture_state = PipelineState.ERROR
            logger.exception(f"Failed to load texture pipeline: {e}")
            await self._broadcast_status(f"Error loading texture model: {str(e)[:50]}", 0.0)
            raise

    @property
    def shape_pipeline(self):
        """Get the shape pipeline (may be None if not loaded)."""
        return self._shape_pipeline

    @property
    def texture_pipeline(self):
        """Get the texture pipeline (may be None if not loaded)."""
        return self._texture_pipeline

    @property
    def is_shape_ready(self) -> bool:
        """Check if shape pipeline is loaded and ready."""
        return self._shape_state == PipelineState.READY and self._shape_pipeline is not None

    @property
    def is_texture_ready(self) -> bool:
        """Check if texture pipeline is loaded and ready."""
        return self._texture_state == PipelineState.READY and self._texture_pipeline is not None

    async def health_check(self) -> dict:
        """
        Perform a health check on the pipeline manager.

        Returns status information for monitoring.
        """
        self._update_heartbeat()

        status = self.get_status()

        # Check for CUDA availability
        cuda_ok = False
        try:
            import torch
            cuda_ok = torch.cuda.is_available()
        except Exception:
            pass

        return {
            "healthy": status.is_healthy,
            "cuda_available": cuda_ok,
            "current_stage": status.current_stage.value,
            "shape_state": status.shape_state.value,
            "texture_state": status.texture_state.value,
            "vram_used_gb": status.vram_used_gb,
            "vram_free_gb": status.vram_free_gb,
            "last_heartbeat_seconds_ago": time.time() - status.last_heartbeat,
            "status_message": status.status_message,
        }


# Global instance
_pipeline_manager: Optional[PipelineManager] = None


def get_pipeline_manager() -> PipelineManager:
    """Get or create the global pipeline manager instance."""
    global _pipeline_manager
    if _pipeline_manager is None:
        _pipeline_manager = PipelineManager()
        logger.info("Created new PipelineManager instance")
    return _pipeline_manager
