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
        """
        import torch

        vram_before = self._get_vram_info()["used_gb"]
        logger.info(f"Full unload starting. VRAM before: {vram_before:.2f}GB")

        await self._broadcast_status("Unloading pipelines...", 0.1)
        if progress_callback:
            progress_callback(0.1, "Unloading pipelines...")

        # Unload shape pipeline
        if self._shape_pipeline is not None:
            self._shape_state = PipelineState.UNLOADING
            await self._broadcast_status("Unloading shape model...", 0.15)

            try:
                # Try to free model hooks if available
                if hasattr(self._shape_pipeline, 'maybe_free_model_hooks'):
                    self._shape_pipeline.maybe_free_model_hooks()
            except Exception as e:
                logger.warning(f"Error freeing shape model hooks: {e}")

            # Delete the pipeline
            del self._shape_pipeline
            self._shape_pipeline = None
            self._shape_state = PipelineState.UNLOADED
            logger.info("Shape pipeline deleted")

        # Unload texture pipeline
        if self._texture_pipeline is not None:
            self._texture_state = PipelineState.UNLOADING
            await self._broadcast_status("Unloading texture model...", 0.2)

            try:
                if hasattr(self._texture_pipeline, 'maybe_free_model_hooks'):
                    self._texture_pipeline.maybe_free_model_hooks()
            except Exception as e:
                logger.warning(f"Error freeing texture model hooks: {e}")

            del self._texture_pipeline
            self._texture_pipeline = None
            self._texture_state = PipelineState.UNLOADED
            logger.info("Texture pipeline deleted")

        await self._broadcast_status("Clearing GPU memory...", 0.25)
        if progress_callback:
            progress_callback(0.25, "Clearing GPU memory...")

        # Aggressive garbage collection
        gc.collect()
        gc.collect()
        gc.collect()

        # Clear CUDA cache
        if torch.cuda.is_available():
            torch.cuda.synchronize()
            torch.cuda.empty_cache()

            # IPC collect if available
            if hasattr(torch.cuda, 'ipc_collect'):
                torch.cuda.ipc_collect()

            torch.cuda.synchronize()

        # Final garbage collection
        gc.collect()

        vram_after = self._get_vram_info()["used_gb"]
        freed = vram_before - vram_after

        logger.info(f"Full unload complete. VRAM: {vram_before:.2f}GB -> {vram_after:.2f}GB (freed {freed:.2f}GB)")

        await self._broadcast_status(f"VRAM cleared: {vram_after:.1f}GB used", 0.3)
        if progress_callback:
            progress_callback(0.3, f"VRAM cleared: {vram_after:.1f}GB used")

    async def _load_shape_pipeline(self, progress_callback: Optional[ProgressCallback] = None) -> dict:
        """Load the shape generation pipeline (Hunyuan3D-2.1)."""
        import torch
        from src.config import get_inference_dtype

        self._shape_state = PipelineState.LOADING
        await self._broadcast_status("Loading shape model (21GB)...", 0.35)
        if progress_callback:
            progress_callback(0.35, "Loading shape model (21GB)...")

        logger.info("Loading shape pipeline from Hunyuan3D-2.1...")

        try:
            # Import the pipeline class
            await self._broadcast_status("Importing Hunyuan3D...", 0.4)
            if progress_callback:
                progress_callback(0.4, "Importing Hunyuan3D...")

            from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline

            # Get optimal dtype
            dtype = get_inference_dtype()
            if dtype is None:
                dtype = torch.bfloat16

            await self._broadcast_status("Downloading/loading model weights...", 0.45)
            if progress_callback:
                progress_callback(0.45, "Downloading/loading model weights...")

            # Load the model (this takes time - downloads if not cached)
            self._shape_pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
                self._shape_model_path,
                subfolder="hunyuan3d-dit-v2-1",
                torch_dtype=dtype,
                use_safetensors=False,
            )

            await self._broadcast_status("Moving model to GPU...", 0.8)
            if progress_callback:
                progress_callback(0.8, "Moving model to GPU...")

            # Move to GPU
            if torch.cuda.is_available():
                self._shape_pipeline.to("cuda")

            self._shape_state = PipelineState.READY
            vram = self._get_vram_info()

            await self._broadcast_status(f"Shape model ready ({vram['used_gb']:.1f}GB)", 1.0)
            if progress_callback:
                progress_callback(1.0, f"Shape model ready ({vram['used_gb']:.1f}GB)")

            logger.info(f"Shape pipeline loaded. VRAM: {vram['used_gb']:.2f}GB")

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

        self._texture_state = PipelineState.LOADING
        await self._broadcast_status("Loading texture model (18GB)...", 0.35)
        if progress_callback:
            progress_callback(0.35, "Loading texture model (18GB)...")

        logger.info("Loading texture pipeline from Hunyuan3D-2...")

        try:
            await self._broadcast_status("Importing Hunyuan3D Paint...", 0.4)
            if progress_callback:
                progress_callback(0.4, "Importing Hunyuan3D Paint...")

            from hy3dgen.texgen import Hunyuan3DPaintPipeline

            await self._broadcast_status("Downloading/loading texture weights...", 0.45)
            if progress_callback:
                progress_callback(0.45, "Downloading/loading texture weights...")

            # Load the texture pipeline
            # Note: Hunyuan3DPaintPipeline doesn't have a .to() method like the shape pipeline
            # It handles device management internally and loads to GPU automatically
            self._texture_pipeline = Hunyuan3DPaintPipeline.from_pretrained(
                self._texture_model_path,
                subfolder=self._texture_subfolder,
            )

            await self._broadcast_status("Texture model loaded", 0.9)
            if progress_callback:
                progress_callback(0.9, "Texture model loaded")

            self._texture_state = PipelineState.READY
            vram = self._get_vram_info()

            await self._broadcast_status(f"Texture model ready ({vram['used_gb']:.1f}GB)", 1.0)
            if progress_callback:
                progress_callback(1.0, f"Texture model ready ({vram['used_gb']:.1f}GB)")

            logger.info(f"Texture pipeline loaded. VRAM: {vram['used_gb']:.2f}GB")

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
