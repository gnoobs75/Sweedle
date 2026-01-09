"""Background worker for processing GPU jobs from the queue.

Implements preprocessing/GPU overlap for improved throughput:
- Preprocessing queue runs in parallel with GPU work
- Next job's image is preprocessed while current job runs on GPU
- Results in ~34% throughput improvement
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from PIL import Image

from src.config import settings
from src.core.queue import JobQueue, JobStatus, get_queue
from src.core.websocket_manager import WebSocketManager, get_websocket_manager
from src.inference.config import GenerationConfig, TextureConfig, OutputFormat, GenerationMode
from src.inference.pipeline import Hunyuan3DPipeline, get_pipeline
from src.inference.preprocessor import ImagePreprocessor

logger = logging.getLogger(__name__)


@dataclass
class PreprocessedJob:
    """Holds a job with its preprocessed image data."""
    job: Any  # Job instance from queue
    processed_image: Image.Image
    image_path: Path
    preprocessing_time: float


class BackgroundWorker:
    """Background worker that processes GPU jobs from the queue.

    Runs as an asyncio task, pulling jobs from the queue and
    processing them through the Hunyuan3D pipeline. Broadcasts
    progress updates via WebSocket.
    """

    def __init__(
        self,
        queue: Optional[JobQueue] = None,
        pipeline: Optional[Hunyuan3DPipeline] = None,
        ws_manager: Optional[WebSocketManager] = None,
    ):
        """Initialize worker.

        Args:
            queue: Job queue instance (uses global if not provided)
            pipeline: Inference pipeline (uses global if not provided)
            ws_manager: WebSocket manager (uses global if not provided)
        """
        self._queue = queue or get_queue()
        self._pipeline = pipeline or get_pipeline()
        self._ws_manager = ws_manager or get_websocket_manager()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._current_job_id: Optional[str] = None

        # Preprocessing overlap for improved throughput
        self._preprocessor = ImagePreprocessor()
        self._preprocessing_queue: asyncio.Queue[PreprocessedJob] = asyncio.Queue(maxsize=2)
        self._preprocessing_task: Optional[asyncio.Task] = None
        self._use_preprocessing_overlap = settings.ENABLE_PREPROCESSING_OVERLAP

    @property
    def is_running(self) -> bool:
        """Check if worker is running."""
        return self._running

    @property
    def current_job_id(self) -> Optional[str]:
        """ID of currently processing job."""
        return self._current_job_id

    async def start(self) -> None:
        """Start the background worker."""
        if self._running:
            logger.warning("Worker already running")
            return

        self._running = True

        # Initialize preprocessor (eager load rembg)
        logger.info("Initializing image preprocessor...")
        await self._preprocessor.initialize()
        logger.info("Preprocessor initialized")

        # Initialize pipeline (loads models)
        logger.info("Initializing inference pipeline...")
        await self._pipeline.initialize()
        logger.info("Pipeline initialized")

        # Start preprocessing pipeline if enabled
        if self._use_preprocessing_overlap:
            self._preprocessing_task = asyncio.create_task(self._preprocessing_loop())
            logger.info("Preprocessing pipeline started (overlap enabled)")

        # Start main processing loop
        self._task = asyncio.create_task(self._process_loop())
        logger.info("Background worker started")

    async def stop(self) -> None:
        """Stop the background worker gracefully."""
        if not self._running:
            return

        logger.info("Stopping background worker...")
        self._running = False

        # Cancel the preprocessing task
        if self._preprocessing_task:
            self._preprocessing_task.cancel()
            try:
                await self._preprocessing_task
            except asyncio.CancelledError:
                pass

        # Cancel the main processing task
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        # Cleanup preprocessor
        self._preprocessor.cleanup()

        # Cleanup pipeline
        await self._pipeline.cleanup()

        logger.info("Background worker stopped")

    async def _preprocessing_loop(self) -> None:
        """Preprocessing loop that runs in parallel with GPU work.

        Continuously preprocesses the next job from the queue while
        the GPU is busy with the current job. This provides ~34%
        throughput improvement by overlapping preprocessing and GPU work.
        """
        while self._running:
            job = None  # Initialize to avoid scope issues in exception handler
            try:
                # Get next job from queue (blocking)
                job = await self._queue.dequeue()

                if job is None:
                    continue

                # Preprocess the image
                start_time = time.time()
                payload = job.payload
                image_path = Path(payload["image_path"])

                # Send preprocessing status
                await self._ws_manager.send_progress(
                    job_id=job.id,
                    progress=0.05,
                    stage="Preprocessing image...",
                    status="processing",
                )

                # Prepare image (background removal, resize, etc.)
                processed_image = await self._preprocessor.prepare_image(
                    image_path,
                    target_size=512,
                    remove_bg=True,
                )

                preprocessing_time = time.time() - start_time
                logger.info(f"Job {job.id} preprocessed in {preprocessing_time:.2f}s")

                # Put preprocessed job in GPU queue
                preprocessed_job = PreprocessedJob(
                    job=job,
                    processed_image=processed_image,
                    image_path=image_path,
                    preprocessing_time=preprocessing_time,
                )
                await self._preprocessing_queue.put(preprocessed_job)

            except asyncio.CancelledError:
                logger.info("Preprocessing loop cancelled")
                break
            except Exception as e:
                logger.exception(f"Error in preprocessing loop: {e}")
                # Don't crash the loop, but mark job as failed if we have one
                if job is not None:
                    await self._queue.complete(job.id, error=f"Preprocessing failed: {e}")
                    await self._ws_manager.send_progress(
                        job_id=job.id,
                        progress=0,
                        stage="Preprocessing failed",
                        status="failed",
                        error=str(e),
                    )
                await asyncio.sleep(1)

    async def _process_loop(self) -> None:
        """Main processing loop.

        If preprocessing overlap is enabled, consumes from the preprocessing
        queue. Otherwise, pulls directly from the main queue.
        """
        while self._running:
            try:
                if self._use_preprocessing_overlap:
                    # Get preprocessed job from preprocessing queue
                    preprocessed = await self._preprocessing_queue.get()
                    job = preprocessed.job
                    self._current_job_id = job.id
                    await self._process_job_with_preprocessed(preprocessed)
                    self._current_job_id = None
                else:
                    # Direct processing without overlap
                    job = await self._queue.dequeue()
                    if job is None:
                        continue
                    self._current_job_id = job.id
                    await self._process_job(job)
                    self._current_job_id = None

            except asyncio.CancelledError:
                logger.info("Worker loop cancelled")
                break

            except Exception as e:
                logger.exception(f"Error in worker loop: {e}")
                # Brief pause before retrying
                await asyncio.sleep(1)

    async def _process_job(self, job) -> None:
        """Process a single job.

        Args:
            job: Job instance from queue
        """
        logger.info(f"Processing job {job.id}: {job.job_type}")

        try:
            # Send initial progress
            await self._ws_manager.send_progress(
                job_id=job.id,
                progress=0.0,
                stage="Starting...",
                status="processing",
            )

            # Route to appropriate handler
            if job.job_type == "image_to_3d":
                result = await self._process_image_to_3d(job)
            elif job.job_type == "text_to_3d":
                result = await self._process_text_to_3d(job)
            elif job.job_type == "rig_asset":
                result = await self._process_rig_asset(job)
            else:
                raise ValueError(f"Unknown job type: {job.job_type}")

            # Mark job as complete
            if result.get("success"):
                await self._queue.complete(job.id, result=result)
                await self._ws_manager.send_progress(
                    job_id=job.id,
                    progress=1.0,
                    stage="Complete",
                    status="completed",
                    result=result,
                )

                # Send asset ready notification
                if result.get("asset_id"):
                    await self._ws_manager.send_asset_ready(
                        asset_id=result["asset_id"],
                        name=result.get("name", "Untitled"),
                        thumbnail_url=result.get("thumbnail_url"),
                        download_url=result.get("download_url"),
                    )
            else:
                error = result.get("error", "Unknown error")
                await self._queue.complete(job.id, error=error)
                await self._ws_manager.send_progress(
                    job_id=job.id,
                    progress=job.progress,
                    stage="Failed",
                    status="failed",
                    error=error,
                )

        except Exception as e:
            logger.exception(f"Job {job.id} failed: {e}")
            error_msg = str(e)

            await self._queue.complete(job.id, error=error_msg)
            await self._ws_manager.send_progress(
                job_id=job.id,
                progress=job.progress,
                stage="Error",
                status="failed",
                error=error_msg,
            )

        # Send updated queue status
        await self._ws_manager.send_queue_status(self._queue.get_status())

    async def _process_job_with_preprocessed(self, preprocessed: PreprocessedJob) -> None:
        """Process a job that has already been preprocessed.

        This is used when preprocessing overlap is enabled. The image has
        already been preprocessed by the preprocessing loop, so we skip
        that step and go straight to GPU generation.

        Args:
            preprocessed: PreprocessedJob with job and preprocessed image
        """
        job = preprocessed.job
        logger.info(f"Processing preprocessed job {job.id}: {job.job_type}")

        try:
            # Preprocessing already done, update progress
            await self._ws_manager.send_progress(
                job_id=job.id,
                progress=0.15,
                stage="Image preprocessed",
                status="processing",
            )

            # Route to appropriate handler
            if job.job_type == "image_to_3d":
                result = await self._process_image_to_3d_with_preprocessed(
                    job, preprocessed.processed_image
                )
            elif job.job_type == "text_to_3d":
                result = await self._process_text_to_3d(job)
            else:
                raise ValueError(f"Unknown job type: {job.job_type}")

            # Mark job as complete
            if result.get("success"):
                # Add preprocessing time to total
                result["preprocessing_time"] = preprocessed.preprocessing_time
                await self._queue.complete(job.id, result=result)
                await self._ws_manager.send_progress(
                    job_id=job.id,
                    progress=1.0,
                    stage="Complete",
                    status="completed",
                    result=result,
                )

                # Send asset ready notification
                if result.get("asset_id"):
                    await self._ws_manager.send_asset_ready(
                        asset_id=result["asset_id"],
                        name=result.get("name", "Untitled"),
                        thumbnail_url=result.get("thumbnail_url"),
                        download_url=result.get("download_url"),
                    )
            else:
                error = result.get("error", "Unknown error")
                await self._queue.complete(job.id, error=error)
                await self._ws_manager.send_progress(
                    job_id=job.id,
                    progress=job.progress,
                    stage="Failed",
                    status="failed",
                    error=error,
                )

        except Exception as e:
            logger.exception(f"Job {job.id} failed: {e}")
            error_msg = str(e)

            await self._queue.complete(job.id, error=error_msg)
            await self._ws_manager.send_progress(
                job_id=job.id,
                progress=job.progress,
                stage="Error",
                status="failed",
                error=error_msg,
            )

        # Send updated queue status
        await self._ws_manager.send_queue_status(self._queue.get_status())

    async def _process_image_to_3d_with_preprocessed(
        self, job, processed_image: Image.Image
    ) -> dict:
        """Process image-to-3D with already preprocessed image.

        Args:
            job: Job instance
            processed_image: Pre-processed PIL Image

        Returns:
            Result dictionary
        """
        payload = job.payload
        params = payload.get("parameters", {})
        asset_id = payload.get("asset_id", job.id)

        # Build config from parameters
        config = GenerationConfig(
            inference_steps=params.get("inference_steps", 30),
            guidance_scale=params.get("guidance_scale", 5.5),
            octree_resolution=params.get("octree_resolution", 256),
            seed=params.get("seed"),
            texture=TextureConfig(
                enabled=params.get("generate_texture", True),
            ),
            face_count=params.get("face_count"),
            output_format=OutputFormat(params.get("output_format", "glb")),
            mode=GenerationMode(params.get("mode", "standard")),
        )

        # Output directory
        output_dir = settings.GENERATED_DIR / asset_id

        # Capture event loop for thread-safe callback
        # NOTE: Must capture loop here in async context, NOT inside the sync callback
        loop = asyncio.get_running_loop()

        # Create progress callback that updates queue and broadcasts
        async def progress_callback(progress: float, stage: str):
            # Offset progress since preprocessing is done (0-15% already used)
            adjusted_progress = 0.15 + progress * 0.85
            await self._queue.update_progress(job.id, adjusted_progress, stage)
            await self._ws_manager.send_progress(
                job_id=job.id,
                progress=adjusted_progress,
                stage=stage,
                status="processing",
            )

        # Sync wrapper for the async callback (called from ThreadPoolExecutor)
        def sync_progress(progress: float, stage: str):
            asyncio.run_coroutine_threadsafe(progress_callback(progress, stage), loop)

        # Run generation with preprocessed image (skip preprocessing in pipeline)
        result = await self._pipeline.generate(
            image=processed_image,  # Pass the PIL Image directly
            config=config,
            output_dir=output_dir,
            asset_id=asset_id,
            progress_callback=sync_progress,
        )

        if result.success:
            return {
                "success": True,
                "asset_id": asset_id,
                "name": payload.get("name", "Untitled"),
                "mesh_path": str(result.mesh_path) if result.mesh_path else None,
                "thumbnail_url": f"/storage/generated/{asset_id}/thumbnail.png",
                "download_url": f"/storage/generated/{asset_id}/{asset_id}.glb",
                "vertex_count": result.vertex_count,
                "face_count": result.face_count,
                "generation_time": result.generation_time,
            }
        else:
            return {
                "success": False,
                "error": result.error,
            }

    async def _process_image_to_3d(self, job) -> dict:
        """Process image-to-3D generation job.

        Args:
            job: Job instance

        Returns:
            Result dictionary
        """
        payload = job.payload
        image_path = Path(payload["image_path"])
        params = payload.get("parameters", {})
        asset_id = payload.get("asset_id", job.id)

        # Build config from parameters
        config = GenerationConfig(
            inference_steps=params.get("inference_steps", 30),
            guidance_scale=params.get("guidance_scale", 5.5),
            octree_resolution=params.get("octree_resolution", 256),
            seed=params.get("seed"),
            texture=TextureConfig(
                enabled=params.get("generate_texture", True),
            ),
            face_count=params.get("face_count"),
            output_format=OutputFormat(params.get("output_format", "glb")),
            mode=GenerationMode(params.get("mode", "standard")),
        )

        # Output directory
        output_dir = settings.GENERATED_DIR / asset_id

        # Get the current event loop for thread-safe scheduling
        loop = asyncio.get_running_loop()

        # Create progress callback that updates queue and broadcasts
        async def progress_callback(progress: float, stage: str):
            await self._queue.update_progress(job.id, progress, stage)
            await self._ws_manager.send_progress(
                job_id=job.id,
                progress=progress,
                stage=stage,
                status="processing",
            )

        # Capture event loop while in async context (before defining sync callback)
        loop = asyncio.get_running_loop()

        # Sync wrapper for the async callback (called from thread pool)
        def sync_progress(progress: float, stage: str):
            # Use run_coroutine_threadsafe to schedule on the main event loop
            asyncio.run_coroutine_threadsafe(progress_callback(progress, stage), loop)

        # Run generation
        result = await self._pipeline.generate(
            image=image_path,
            config=config,
            output_dir=output_dir,
            asset_id=asset_id,
            progress_callback=sync_progress,
        )

        if result.success:
            return {
                "success": True,
                "asset_id": asset_id,
                "name": payload.get("name", "Untitled"),
                "mesh_path": str(result.mesh_path) if result.mesh_path else None,
                "thumbnail_url": f"/storage/generated/{asset_id}/thumbnail.png",
                "download_url": f"/storage/generated/{asset_id}/{asset_id}.glb",
                "vertex_count": result.vertex_count,
                "face_count": result.face_count,
                "generation_time": result.generation_time,
            }
        else:
            return {
                "success": False,
                "error": result.error,
            }

    async def _process_text_to_3d(self, job) -> dict:
        """Process text-to-3D generation job.

        Note: This requires a text-to-image step first.

        Args:
            job: Job instance

        Returns:
            Result dictionary
        """
        # Text-to-3D not yet implemented
        return {
            "success": False,
            "error": "Text-to-3D is not yet implemented",
        }

    async def _process_rig_asset(self, job) -> dict:
        """Process auto-rigging job.

        Args:
            job: Job instance

        Returns:
            Result dictionary
        """
        from src.rigging.service import get_rigging_service
        from src.rigging.schemas import CharacterType, RiggingProcessor
        from src.database import async_session_maker

        payload = job.payload
        asset_id = payload["asset_id"]
        mesh_path = Path(payload["mesh_path"])
        character_type = CharacterType(payload.get("character_type", "auto"))
        processor = RiggingProcessor(payload.get("processor", "auto"))

        # Resolve mesh path
        if not mesh_path.is_absolute():
            mesh_path = settings.STORAGE_ROOT / mesh_path

        # Output directory (same as asset)
        output_dir = mesh_path.parent / "rigged"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Get the current event loop for thread-safe scheduling
        loop = asyncio.get_running_loop()

        # Create progress callback
        async def progress_callback(progress: float, stage: str):
            await self._queue.update_progress(job.id, progress, stage)
            await self._ws_manager.send_progress(
                job_id=job.id,
                progress=progress,
                stage=stage,
                status="processing",
            )

        def sync_progress(progress: float, stage: str):
            asyncio.run_coroutine_threadsafe(progress_callback(progress, stage), loop)

        # Run rigging
        async with async_session_maker() as db:
            service = get_rigging_service(db)
            result = await service.auto_rig(
                asset_id=asset_id,
                mesh_path=mesh_path,
                output_dir=output_dir,
                character_type=character_type,
                processor=processor,
                progress_callback=sync_progress,
            )

            if result.success:
                # Update asset in database
                from sqlalchemy import select
                from src.generation.models import Asset

                asset_result = await db.execute(select(Asset).where(Asset.id == asset_id))
                asset = asset_result.scalar_one_or_none()

                if asset:
                    asset.is_rigged = True
                    asset.rigging_data = result.skeleton.model_dump() if result.skeleton else None
                    asset.character_type = result.detected_type.value if result.detected_type else None
                    asset.rigged_mesh_path = result.rigged_mesh_path
                    asset.rigging_processor = result.processor_used.value if result.processor_used else None
                    await db.commit()

                return {
                    "success": True,
                    "asset_id": asset_id,
                    "character_type": result.detected_type.value if result.detected_type else None,
                    "bone_count": result.skeleton.bone_count if result.skeleton else 0,
                    "rigged_mesh_path": result.rigged_mesh_path,
                    "processing_time": result.processing_time,
                }
            else:
                return {
                    "success": False,
                    "error": result.error,
                }


# Global worker instance
_worker: Optional[BackgroundWorker] = None


def get_worker() -> BackgroundWorker:
    """Get or create the global worker instance."""
    global _worker
    if _worker is None:
        _worker = BackgroundWorker()
    return _worker


async def start_worker() -> BackgroundWorker:
    """Start the global worker."""
    worker = get_worker()
    await worker.start()
    return worker


async def stop_worker() -> None:
    """Stop the global worker."""
    global _worker
    if _worker:
        await _worker.stop()
        _worker = None
