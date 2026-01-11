"""Pipeline management service for VRAM control."""

import gc
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class PipelineService:
    """Service for managing ML pipeline loading/unloading and VRAM."""

    def __init__(self):
        self._shape_loaded = False
        self._texture_loaded = False

    def get_vram_info(self) -> dict:
        """Get current VRAM information."""
        try:
            import torch
            if torch.cuda.is_available():
                device = torch.cuda.current_device()
                allocated = torch.cuda.memory_allocated(device) / (1024**3)
                reserved = torch.cuda.memory_reserved(device) / (1024**3)
                total = torch.cuda.get_device_properties(device).total_memory / (1024**3)
                free = total - allocated
                return {
                    "allocated_gb": round(allocated, 2),
                    "reserved_gb": round(reserved, 2),
                    "free_gb": round(free, 2),
                    "total_gb": round(total, 2),
                }
        except ImportError:
            pass

        return {
            "allocated_gb": 0,
            "reserved_gb": 0,
            "free_gb": 24,  # Default assumption
            "total_gb": 24,
        }

    def get_status(self) -> dict:
        """Get current pipeline status."""
        from src.inference.pipeline import get_pipeline

        pipeline = get_pipeline()
        vram = self.get_vram_info()

        # Check what's loaded
        shape_loaded = (
            pipeline._shape_pipeline is not None
            if hasattr(pipeline, '_shape_pipeline')
            else False
        )
        texture_loaded = (
            pipeline._texture_pipeline is not None
            if hasattr(pipeline, '_texture_pipeline')
            else False
        )

        # Determine ready stage
        if not shape_loaded and not texture_loaded:
            ready_stage = "upload"  # Ready to load shape for mesh gen
        elif shape_loaded and not texture_loaded:
            ready_stage = "mesh"  # Ready for mesh generation
        elif texture_loaded and not shape_loaded:
            ready_stage = "texture"  # Ready for texture generation
        else:
            ready_stage = "unknown"

        return {
            "shape_loaded": shape_loaded,
            "texture_loaded": texture_loaded,
            "vram_allocated_gb": vram["allocated_gb"],
            "vram_free_gb": vram["free_gb"],
            "vram_total_gb": vram["total_gb"],
            "ready_for_stage": ready_stage,
        }

    async def prepare_for_stage(self, stage: str) -> dict:
        """Prepare VRAM for a specific workflow stage.

        Args:
            stage: The stage to prepare for (mesh, texture, rigging, export)

        Returns:
            Result dict with success status and details
        """
        from src.inference.pipeline import get_pipeline
        from src.inference.vram_manager import (
            unload_shape_pipeline,
            prepare_for_texture,
            clear_cuda_cache,
        )

        pipeline = get_pipeline()
        freed_gb = 0.0
        loaded_pipeline = None

        try:
            if stage == "mesh":
                # Need shape pipeline loaded
                # First unload texture if loaded
                if hasattr(pipeline, '_texture_pipeline') and pipeline._texture_pipeline is not None:
                    logger.info("Unloading texture pipeline for mesh stage")
                    # Move texture to CPU
                    try:
                        pipeline._texture_pipeline.to("cpu")
                    except Exception:
                        pass
                    clear_cuda_cache()
                    freed_gb = 18.0  # Approximate

                # Ensure shape is loaded
                if not pipeline.is_initialized:
                    await pipeline.initialize()
                loaded_pipeline = "shape"

            elif stage == "texture":
                # Need texture pipeline loaded, shape unloaded
                if hasattr(pipeline, '_shape_pipeline') and pipeline._shape_pipeline is not None:
                    logger.info("Unloading shape pipeline for texture stage")
                    result = unload_shape_pipeline(pipeline._shape_pipeline)
                    freed_gb = result.get("freed_gb", 0)
                    pipeline._shape_pipeline = None

                # Ensure texture pipeline is ready (moved to GPU happens during generation)
                loaded_pipeline = "texture"

            elif stage == "rigging":
                # Rigging uses minimal VRAM - unload both pipelines
                logger.info("Unloading pipelines for rigging stage")
                if hasattr(pipeline, '_shape_pipeline') and pipeline._shape_pipeline is not None:
                    result = unload_shape_pipeline(pipeline._shape_pipeline)
                    freed_gb += result.get("freed_gb", 0)
                    pipeline._shape_pipeline = None

                if hasattr(pipeline, '_texture_pipeline') and pipeline._texture_pipeline is not None:
                    try:
                        pipeline._texture_pipeline.to("cpu")
                    except Exception:
                        pass
                    freed_gb += 18.0

                clear_cuda_cache()
                loaded_pipeline = None

            elif stage == "export":
                # Export needs no GPU - unload everything
                logger.info("Unloading all pipelines for export stage")
                await self.unload_all()
                freed_gb = self.get_vram_info()["allocated_gb"]
                loaded_pipeline = None

            else:
                return {
                    "success": False,
                    "message": f"Unknown stage: {stage}",
                    "freed_gb": 0,
                    "loaded_pipeline": None,
                }

            # Broadcast pipeline status update via WebSocket
            from src.core.websocket_manager import get_websocket_manager
            ws = get_websocket_manager()
            status = self.get_status()
            await ws.send_pipeline_status(
                shape_loaded=status["shape_loaded"],
                texture_loaded=status["texture_loaded"],
                vram_allocated_gb=status["vram_allocated_gb"],
                vram_free_gb=status["vram_free_gb"],
            )

            return {
                "success": True,
                "message": f"Prepared for {stage} stage",
                "freed_gb": freed_gb,
                "loaded_pipeline": loaded_pipeline,
            }

        except Exception as e:
            logger.exception(f"Error preparing for stage {stage}: {e}")
            return {
                "success": False,
                "message": str(e),
                "freed_gb": 0,
                "loaded_pipeline": None,
            }

    async def unload_all(self) -> dict:
        """Unload all pipelines to free VRAM."""
        from src.inference.pipeline import get_pipeline
        from src.inference.vram_manager import unload_shape_pipeline, clear_cuda_cache

        pipeline = get_pipeline()
        freed_gb = 0.0

        try:
            # Unload shape pipeline
            if hasattr(pipeline, '_shape_pipeline') and pipeline._shape_pipeline is not None:
                result = unload_shape_pipeline(pipeline._shape_pipeline)
                freed_gb += result.get("freed_gb", 0)
                pipeline._shape_pipeline = None

            # Unload texture pipeline
            if hasattr(pipeline, '_texture_pipeline') and pipeline._texture_pipeline is not None:
                try:
                    pipeline._texture_pipeline.to("cpu")
                except Exception:
                    pass
                del pipeline._texture_pipeline
                pipeline._texture_pipeline = None
                freed_gb += 18.0

            # Aggressive cleanup
            gc.collect()
            gc.collect()
            clear_cuda_cache()

            # Broadcast pipeline status
            from src.core.websocket_manager import get_websocket_manager
            ws = get_websocket_manager()
            status = self.get_status()
            await ws.send_pipeline_status(
                shape_loaded=status["shape_loaded"],
                texture_loaded=status["texture_loaded"],
                vram_allocated_gb=status["vram_allocated_gb"],
                vram_free_gb=status["vram_free_gb"],
            )

            return {
                "success": True,
                "message": "All pipelines unloaded",
                "freed_gb": freed_gb,
            }

        except Exception as e:
            logger.exception(f"Error unloading pipelines: {e}")
            return {
                "success": False,
                "message": str(e),
                "freed_gb": 0,
            }


# Global instance
_service: Optional[PipelineService] = None


def get_pipeline_service() -> PipelineService:
    """Get or create the global pipeline service."""
    global _service
    if _service is None:
        _service = PipelineService()
    return _service
