"""Image preprocessing for 3D generation."""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional, Union

from PIL import Image

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """Handles image preprocessing for 3D generation.

    Includes background removal using rembg and image normalization.
    """

    def __init__(self, model_name: str = "u2net"):
        """Initialize preprocessor.

        Args:
            model_name: rembg model to use. Options: u2net, u2netp, isnet-general-use
        """
        self._model_name = model_name
        self._session = None
        self._executor = ThreadPoolExecutor(max_workers=4)  # Increased for parallelism
        self._initialized = False

    async def initialize(self) -> None:
        """Eagerly initialize the rembg session.

        Call this at startup to avoid the first-image delay.
        The rembg model (U2Net ~170MB) will be loaded into memory.
        """
        if self._initialized:
            return

        logger.info("Initializing rembg session (eager load)...")

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self._executor, self._get_session)

        if self._session is not None:
            logger.info(f"rembg session initialized with model: {self._model_name}")
            self._initialized = True
        else:
            logger.warning("rembg session initialization failed (background removal will be skipped)")

    def _get_session(self):
        """Lazy initialization of rembg session."""
        if self._session is None:
            try:
                from rembg import new_session
                self._session = new_session(self._model_name)
                self._initialized = True
                logger.info(f"Initialized rembg session with model: {self._model_name}")
            except ImportError:
                logger.warning("rembg not installed. Background removal will be skipped.")
                self._initialized = False
        return self._session

    async def remove_background(
        self,
        image_path: Union[str, Path],
        alpha_matting: bool = True,
        foreground_threshold: int = 240,
        background_threshold: int = 10,
    ) -> Image.Image:
        """Remove background from image asynchronously.

        Args:
            image_path: Path to input image
            alpha_matting: Use alpha matting for smoother edges
            foreground_threshold: Threshold for foreground detection
            background_threshold: Threshold for background detection

        Returns:
            PIL Image with transparent background (RGBA)
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self._remove_background_sync,
            Path(image_path),
            alpha_matting,
            foreground_threshold,
            background_threshold,
        )

    def _remove_background_sync(
        self,
        image_path: Path,
        alpha_matting: bool,
        foreground_threshold: int,
        background_threshold: int,
    ) -> Image.Image:
        """Synchronous background removal."""
        input_image = Image.open(image_path)

        # Convert to RGB if needed
        if input_image.mode not in ("RGB", "RGBA"):
            input_image = input_image.convert("RGB")

        session = self._get_session()

        if session is None:
            # rembg not available, return original with alpha channel
            logger.warning("Background removal skipped - rembg not available")
            if input_image.mode != "RGBA":
                input_image = input_image.convert("RGBA")
            return input_image

        try:
            from rembg import remove

            output_image = remove(
                input_image,
                session=session,
                alpha_matting=alpha_matting,
                alpha_matting_foreground_threshold=foreground_threshold,
                alpha_matting_background_threshold=background_threshold,
            )

            logger.debug(f"Background removed from {image_path}")
            return output_image

        except Exception as e:
            logger.error(f"Background removal failed: {e}")
            # Return original image with alpha
            if input_image.mode != "RGBA":
                input_image = input_image.convert("RGBA")
            return input_image

    async def prepare_image(
        self,
        image_path: Union[str, Path],
        target_size: int = 512,
        remove_bg: bool = True,
        center_crop: bool = True,
    ) -> Image.Image:
        """Prepare image for 3D generation.

        Args:
            image_path: Path to input image
            target_size: Target size (square)
            remove_bg: Whether to remove background
            center_crop: Whether to center crop to square

        Returns:
            Prepared PIL Image (RGBA, square)
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self._prepare_image_sync,
            Path(image_path),
            target_size,
            remove_bg,
            center_crop,
        )

    def _prepare_image_sync(
        self,
        image_path: Path,
        target_size: int,
        remove_bg: bool,
        center_crop: bool,
    ) -> Image.Image:
        """Synchronous image preparation."""
        # Load image
        image = Image.open(image_path)

        # Remove background if requested
        if remove_bg:
            image = self._remove_background_sync(
                image_path,
                alpha_matting=True,
                foreground_threshold=240,
                background_threshold=10,
            )
        elif image.mode != "RGBA":
            image = image.convert("RGBA")

        # Center crop to square if needed
        if center_crop and image.width != image.height:
            size = min(image.width, image.height)
            left = (image.width - size) // 2
            top = (image.height - size) // 2
            image = image.crop((left, top, left + size, top + size))

        # Resize to target size
        if image.width != target_size or image.height != target_size:
            image = image.resize((target_size, target_size), Image.LANCZOS)

        return image

    async def save_processed(
        self,
        image: Image.Image,
        output_path: Union[str, Path],
    ) -> Path:
        """Save processed image.

        Args:
            image: PIL Image to save
            output_path: Output path

        Returns:
            Path to saved image
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self._executor,
            image.save,
            str(output_path),
            "PNG",
        )

        logger.debug(f"Saved processed image to {output_path}")
        return output_path

    def cleanup(self):
        """Release resources."""
        self._session = None
        self._executor.shutdown(wait=False)
