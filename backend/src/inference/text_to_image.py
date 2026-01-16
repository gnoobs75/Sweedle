"""Stable Diffusion XL pipeline for text-to-image generation.

This module provides a wrapper around the SDXL model for generating
images from text prompts, which can then be used with the Hunyuan3D
image-to-3D pipeline.
"""

import asyncio
import gc
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from PIL import Image

from src.config import settings, get_inference_dtype
from src.inference.style_presets import build_prompt, get_preset

logger = logging.getLogger(__name__)

# Type alias for progress callback
ProgressCallback = Callable[[float, str], None]


@dataclass
class TextToImageConfig:
    """Configuration for text-to-image generation."""
    prompt: str
    style_preset: str = "game_asset"
    negative_prompt: Optional[str] = None
    seed: Optional[int] = None
    num_inference_steps: int = 30
    guidance_scale: float = 7.5
    width: int = 1024
    height: int = 1024


@dataclass
class TextToImageResult:
    """Result from text-to-image generation."""
    success: bool
    image_path: Optional[Path] = None
    image: Optional[Image.Image] = None
    generation_time: float = 0.0
    seed_used: int = 0
    prompt_used: str = ""
    error: Optional[str] = None


class SDXLPipeline:
    """Wrapper for Stable Diffusion XL text-to-image generation.

    This pipeline manages VRAM carefully to coexist with Hunyuan3D:
    - Loads to GPU only when generating
    - Unloads to CPU after generation
    - Can be fully cleaned up to free all VRAM
    """

    MODEL_ID = "stabilityai/stable-diffusion-xl-base-1.0"
    REFINER_ID = "stabilityai/stable-diffusion-xl-refiner-1.0"

    def __init__(
        self,
        model_id: str = None,
        device: str = None,
        use_refiner: bool = False,
    ):
        """Initialize SDXL pipeline.

        Args:
            model_id: HuggingFace model ID (default: SDXL base)
            device: Device to use (cuda, mps, cpu, or auto)
            use_refiner: Whether to use the SDXL refiner for higher quality
        """
        self.model_id = model_id or self.MODEL_ID
        self.use_refiner = use_refiner

        # Determine device
        if device is None or device == "auto":
            self.device = settings.compute_device
        else:
            self.device = device

        self._pipeline = None
        self._refiner = None
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._initialized = False
        self._on_gpu = False
        self._lock = asyncio.Lock()

        logger.info(f"SDXL pipeline configured for device: {self.device}")

    @property
    def is_initialized(self) -> bool:
        """Check if pipeline is initialized (model loaded)."""
        return self._initialized

    @property
    def is_on_gpu(self) -> bool:
        """Check if model is currently on GPU."""
        return self._on_gpu

    def _load_pipeline(self) -> None:
        """Load the SDXL pipeline (runs in thread)."""
        try:
            import torch
            from diffusers import StableDiffusionXLPipeline, DPMSolverMultistepScheduler

            logger.info(f"Loading SDXL from {self.model_id}...")
            start_time = time.time()

            # Get inference dtype
            dtype = get_inference_dtype() or torch.float16

            # Load the pipeline
            self._pipeline = StableDiffusionXLPipeline.from_pretrained(
                self.model_id,
                torch_dtype=dtype,
                variant="fp16",
                use_safetensors=True,
            )

            # Use faster scheduler
            self._pipeline.scheduler = DPMSolverMultistepScheduler.from_config(
                self._pipeline.scheduler.config
            )

            # Enable memory optimizations
            if hasattr(self._pipeline, "enable_attention_slicing"):
                self._pipeline.enable_attention_slicing()

            if settings.ENABLE_MEMORY_EFFICIENT_ATTENTION:
                try:
                    self._pipeline.enable_xformers_memory_efficient_attention()
                    logger.info("Enabled xformers memory-efficient attention")
                except Exception:
                    pass  # xformers not available

            # Move to GPU
            self._pipeline.to(self.device)
            self._on_gpu = True

            load_time = time.time() - start_time
            logger.info(f"SDXL loaded in {load_time:.1f}s")

            self._initialized = True

        except Exception as e:
            logger.error(f"Failed to load SDXL: {e}")
            raise

    async def initialize(self) -> None:
        """Initialize the pipeline (load models)."""
        async with self._lock:
            if self._initialized:
                return

            loop = asyncio.get_running_loop()
            await loop.run_in_executor(self._executor, self._load_pipeline)

    def _move_to_gpu(self) -> None:
        """Move pipeline to GPU."""
        if self._pipeline is not None and not self._on_gpu:
            logger.info("Moving SDXL to GPU...")
            self._pipeline.to(self.device)
            self._on_gpu = True

    def _move_to_cpu(self) -> None:
        """Move pipeline to CPU to free VRAM."""
        if self._pipeline is not None and self._on_gpu:
            logger.info("Moving SDXL to CPU...")
            self._pipeline.to("cpu")
            self._on_gpu = False

            # Clear CUDA cache
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    gc.collect()
            except Exception:
                pass

    async def unload(self) -> None:
        """Unload pipeline from GPU to CPU."""
        async with self._lock:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(self._executor, self._move_to_cpu)

    async def cleanup(self) -> None:
        """Fully cleanup the pipeline and free all memory."""
        async with self._lock:
            if self._pipeline is not None:
                logger.info("Cleaning up SDXL pipeline...")

                # Delete pipeline
                del self._pipeline
                self._pipeline = None

                if self._refiner is not None:
                    del self._refiner
                    self._refiner = None

                self._initialized = False
                self._on_gpu = False

                # Force garbage collection
                gc.collect()

                try:
                    import torch
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                except Exception:
                    pass

                logger.info("SDXL pipeline cleaned up")

    def _generate_sync(
        self,
        config: TextToImageConfig,
        output_path: Path,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> TextToImageResult:
        """Synchronous generation (runs in thread)."""
        import torch

        start_time = time.time()

        try:
            # Ensure on GPU
            if not self._on_gpu:
                self._move_to_gpu()

            if progress_callback:
                progress_callback(0.1, "Building prompt...")

            # Build prompt with style preset
            preset = get_preset(config.style_preset)
            full_prompt, base_negative = build_prompt(config.prompt, config.style_preset)

            # Combine negative prompts
            negative_prompt = config.negative_prompt or base_negative
            if config.negative_prompt and base_negative:
                negative_prompt = f"{base_negative}, {config.negative_prompt}"

            # Get guidance scale (preset override or config)
            guidance = preset.guidance_scale or config.guidance_scale

            # Get steps (preset override or config)
            steps = preset.steps or config.num_inference_steps

            # Setup generator for reproducibility
            generator = None
            seed = config.seed
            if seed is None:
                seed = torch.randint(0, 2**32 - 1, (1,)).item()

            generator = torch.Generator(device=self.device)
            generator.manual_seed(seed)

            if progress_callback:
                progress_callback(0.2, "Generating image...")

            # Progress callback for diffusion steps
            def step_callback(pipe, step, timestep, callback_kwargs):
                if progress_callback:
                    # Map step progress from 0.2 to 0.9
                    step_progress = step / steps
                    overall_progress = 0.2 + (step_progress * 0.7)
                    progress_callback(overall_progress, f"Step {step + 1}/{steps}")
                return callback_kwargs

            # Generate
            with torch.inference_mode():
                result = self._pipeline(
                    prompt=full_prompt,
                    negative_prompt=negative_prompt,
                    width=config.width,
                    height=config.height,
                    num_inference_steps=steps,
                    guidance_scale=guidance,
                    generator=generator,
                    callback_on_step_end=step_callback,
                )

            image = result.images[0]

            if progress_callback:
                progress_callback(0.95, "Saving image...")

            # Save image
            output_path.parent.mkdir(parents=True, exist_ok=True)
            image.save(output_path, "PNG")

            if progress_callback:
                progress_callback(1.0, "Complete")

            generation_time = time.time() - start_time

            return TextToImageResult(
                success=True,
                image_path=output_path,
                image=image,
                generation_time=generation_time,
                seed_used=seed,
                prompt_used=full_prompt,
            )

        except Exception as e:
            logger.error(f"SDXL generation failed: {e}")
            return TextToImageResult(
                success=False,
                error=str(e),
                generation_time=time.time() - start_time,
            )

    async def generate(
        self,
        config: TextToImageConfig,
        output_path: Path,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> TextToImageResult:
        """Generate an image from text prompt.

        Args:
            config: Generation configuration
            output_path: Where to save the generated image
            progress_callback: Optional callback for progress updates

        Returns:
            TextToImageResult with the generated image
        """
        async with self._lock:
            # Ensure initialized
            if not self._initialized:
                if progress_callback:
                    progress_callback(0.0, "Loading SDXL model...")
                await self.initialize()

            # Run generation in thread
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                self._executor,
                self._generate_sync,
                config,
                output_path,
                progress_callback,
            )

            return result

    async def generate_and_unload(
        self,
        config: TextToImageConfig,
        output_path: Path,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> TextToImageResult:
        """Generate an image and then unload from GPU.

        Use this when you need to free VRAM for another pipeline
        (like Hunyuan3D) after generation.
        """
        result = await self.generate(config, output_path, progress_callback)

        # Unload to free VRAM
        await self.unload()

        return result


# Global singleton instance
_sdxl_pipeline: Optional[SDXLPipeline] = None


def get_sdxl_pipeline() -> SDXLPipeline:
    """Get the global SDXL pipeline instance."""
    global _sdxl_pipeline
    if _sdxl_pipeline is None:
        _sdxl_pipeline = SDXLPipeline()
    return _sdxl_pipeline


async def cleanup_sdxl_pipeline() -> None:
    """Cleanup the global SDXL pipeline."""
    global _sdxl_pipeline
    if _sdxl_pipeline is not None:
        await _sdxl_pipeline.cleanup()
        _sdxl_pipeline = None
