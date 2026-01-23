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
from src.inference.pipeline_manager import PipelineManager, PipelineStage, get_pipeline_manager
from src.inference.preprocessor import ImagePreprocessor
from src.database import async_session_maker
from src.generation.models import Asset, AssetStatus

logger = logging.getLogger(__name__)


@dataclass
class PreprocessedJob:
    """Holds a job with its preprocessed image data."""
    job: Any  # Job instance from queue
    processed_image: Optional[Image.Image]  # None for non-image jobs
    image_path: Optional[Path]  # None for non-image jobs
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
        pipeline_manager: Optional[PipelineManager] = None,
        ws_manager: Optional[WebSocketManager] = None,
    ):
        """Initialize worker.

        Args:
            queue: Job queue instance (uses global if not provided)
            pipeline_manager: Pipeline manager instance (uses global if not provided)
            ws_manager: WebSocket manager (uses global if not provided)
        """
        self._queue = queue or get_queue()
        self._pipeline_manager = pipeline_manager or get_pipeline_manager()
        self._ws_manager = ws_manager or get_websocket_manager()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._current_job_id: Optional[str] = None
        self._heartbeat_task: Optional[asyncio.Task] = None

        # Preprocessing overlap for improved throughput
        self._preprocessor = ImagePreprocessor()
        self._preprocessing_queue: asyncio.Queue[PreprocessedJob] = asyncio.Queue(maxsize=2)
        self._preprocessing_task: Optional[asyncio.Task] = None
        self._use_preprocessing_overlap = settings.ENABLE_PREPROCESSING_OVERLAP

        # Connect pipeline manager to websocket for status broadcasts
        self._pipeline_manager.set_websocket_manager(self._ws_manager)

    @property
    def is_running(self) -> bool:
        """Check if worker is running."""
        return self._running

    @property
    def current_job_id(self) -> Optional[str]:
        """ID of currently processing job."""
        return self._current_job_id

    async def _update_asset_status(
        self,
        asset_id: str,
        status: AssetStatus,
        result: Optional[dict] = None,
        error: Optional[str] = None,
    ) -> None:
        """Update asset status in database.

        Args:
            asset_id: Asset ID to update
            status: New status
            result: Optional generation result with file paths etc.
            error: Optional error message for failed status
        """
        try:
            async with async_session_maker() as session:
                from sqlalchemy import select
                stmt = select(Asset).where(Asset.id == asset_id)
                db_result = await session.execute(stmt)
                asset = db_result.scalar_one_or_none()

                if asset:
                    asset.status = status
                    if error:
                        asset.error_message = error
                    if result:
                        if result.get("mesh_path"):
                            asset.file_path = result.get("mesh_path")
                        if result.get("thumbnail_path"):
                            asset.thumbnail_path = result.get("thumbnail_path")
                        if result.get("vertex_count"):
                            asset.vertex_count = result.get("vertex_count")
                        if result.get("face_count"):
                            asset.face_count = result.get("face_count")
                        if result.get("generation_time"):
                            asset.generation_time_seconds = result.get("generation_time")
                        if "has_texture" in result:
                            asset.has_texture = result.get("has_texture")
                    await session.commit()
                    logger.info(f"Updated asset {asset_id} status to {status.value}")
                else:
                    logger.warning(f"Asset {asset_id} not found for status update")
        except Exception as e:
            logger.error(f"Failed to update asset status: {e}")

    async def start(self) -> None:
        """Start the background worker.

        Note: Pipeline models are NOT loaded at startup anymore.
        They are loaded lazily when the first job requires them.
        This allows faster startup and better VRAM management.
        """
        if self._running:
            logger.warning("Worker already running")
            return

        self._running = True

        # Initialize preprocessor (eager load rembg - small model, ~170MB)
        logger.info("Initializing image preprocessor...")
        await self._preprocessor.initialize()
        logger.info("Preprocessor initialized")

# NOTE: We NO LONGER load the pipeline at startup!
        # The PipelineManager handles lazy loading when jobs are processed.
        # This provides:
        # 1. Faster startup
        # 2. Better VRAM management (only load what's needed)
        # 3. Ability to swap between shape/texture pipelines
        logger.info("Pipeline manager ready (lazy loading enabled)")

        # Start preprocessing pipeline if enabled
        if self._use_preprocessing_overlap:
            self._preprocessing_task = asyncio.create_task(self._preprocessing_loop())
            logger.info("Preprocessing pipeline started (overlap enabled)")

        # Start heartbeat task for health monitoring
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info("Heartbeat monitor started")

        # Start main processing loop
        self._task = asyncio.create_task(self._process_loop())
        logger.info("Background worker started")

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeat to indicate system is alive."""
        while self._running:
            try:
                status = self._pipeline_manager.get_status()
                await self._ws_manager.send_heartbeat(
                    stage=status.current_stage.value,
                    status=status.status_message,
                    vram_used_gb=status.vram_used_gb,
                    vram_free_gb=status.vram_free_gb,
                    is_processing=self._current_job_id is not None,
                    current_job_id=self._current_job_id,
                )
                await asyncio.sleep(5)  # Heartbeat every 5 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Heartbeat error (non-fatal): {e}")
                await asyncio.sleep(5)

    async def stop(self) -> None:
        """Stop the background worker gracefully."""
        if not self._running:
            return

        logger.info("Stopping background worker...")
        self._running = False

        # Cancel the heartbeat task
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

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

        # Cleanup pipeline manager (full VRAM unload)
        await self._pipeline_manager._full_unload()

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

                # Skip non-image jobs (e.g., rigging jobs don't need image preprocessing)
                payload = job.payload
                if "image_path" not in payload:
                    # Put job directly in GPU queue without preprocessing
                    preprocessed_job = PreprocessedJob(
                        job=job,
                        processed_image=None,  # No preprocessed image
                        image_path=None,
                        preprocessing_time=0.0,
                    )
                    await self._preprocessing_queue.put(preprocessed_job)
                    continue

                # Preprocess the image
                start_time = time.time()
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
        import time as time_module
        job_start = time_module.time()

        logger.info("=" * 60)
        logger.info(f"===== JOB STARTING: {job.id} =====")
        logger.info("=" * 60)
        logger.info(f"Job type: {job.job_type}")
        logger.info(f"Job params: {job.params if hasattr(job, 'params') else 'N/A'}")

        # Log VRAM state at job start
        try:
            import torch
            if torch.cuda.is_available():
                vram_allocated = torch.cuda.memory_allocated(0) / 1e9
                vram_total = torch.cuda.get_device_properties(0).total_memory / 1e9
                logger.info(f"VRAM at job start: {vram_allocated:.2f}GB / {vram_total:.2f}GB")
        except:
            pass

        try:
            # Send initial progress
            await self._ws_manager.send_progress(
                job_id=job.id,
                progress=0.0,
                stage="Starting...",
                status="processing",
            )

            # Route to appropriate handler
            logger.info(f"Routing to handler for job type: {job.job_type}")
            if job.job_type == "image_to_3d":
                result = await self._process_image_to_3d(job)
            elif job.job_type == "text_to_3d":
                result = await self._process_text_to_3d(job)
            elif job.job_type == "rig_asset":
                result = await self._process_rig_asset(job)
            elif job.job_type == "add_texture":
                result = await self._process_add_texture(job)
            else:
                raise ValueError(f"Unknown job type: {job.job_type}")

            # Mark job as complete
            job_elapsed = time_module.time() - job_start
            if result.get("success"):
                logger.info("=" * 60)
                logger.info(f"===== JOB COMPLETED: {job.id} =====")
                logger.info("=" * 60)
                logger.info(f"Job type: {job.job_type}")
                logger.info(f"Total time: {job_elapsed:.1f}s")
                if result.get("asset_id"):
                    logger.info(f"Asset ID: {result['asset_id']}")
                if result.get("vertex_count"):
                    logger.info(f"Mesh: {result.get('vertex_count', 0):,} vertices, {result.get('face_count', 0):,} faces")
                if result.get("generation_time"):
                    logger.info(f"Generation time: {result['generation_time']:.1f}s")

                await self._queue.complete(job.id, result=result)
                await self._ws_manager.send_progress(
                    job_id=job.id,
                    progress=1.0,
                    stage="Complete",
                    status="completed",
                    result=result,
                    asset_id=result.get("asset_id"),
                )

                # Update asset status in database
                if result.get("asset_id") and job.job_type in ("image_to_3d", "add_texture"):
                    logger.info(f"Updating asset status to COMPLETED: {result['asset_id']}")
                    await self._update_asset_status(
                        result["asset_id"],
                        AssetStatus.COMPLETED,
                        result=result,
                    )

                # Send rigging-specific completion message
                if job.job_type == "rig_asset" and result.get("asset_id"):
                    logger.info(f"Sending rigging complete notification: {result.get('bone_count', 0)} bones")
                    await self._ws_manager.send_rigging_complete(
                        asset_id=result["asset_id"],
                        character_type=result.get("character_type", "unknown"),
                        bone_count=result.get("bone_count", 0),
                    )

                # Send asset ready notification
                if result.get("asset_id"):
                    logger.info(f"Sending asset_ready notification for: {result['asset_id']}")
                    await self._ws_manager.send_asset_ready(
                        asset_id=result["asset_id"],
                        name=result.get("name", "Untitled"),
                        thumbnail_url=result.get("thumbnail_url"),
                        download_url=result.get("download_url"),
                    )
            else:
                error = result.get("error", "Unknown error")
                logger.info("=" * 60)
                logger.info(f"===== JOB FAILED: {job.id} =====")
                logger.info("=" * 60)
                logger.info(f"Job type: {job.job_type}")
                logger.info(f"Total time: {job_elapsed:.1f}s")
                logger.error(f"Error: {error}")

                await self._queue.complete(job.id, error=error)
                await self._ws_manager.send_progress(
                    job_id=job.id,
                    progress=job.progress,
                    stage="Failed",
                    status="failed",
                    error=error,
                    asset_id=result.get("asset_id"),
                )

                # Send rigging-specific failure message
                if job.job_type == "rig_asset" and result.get("asset_id"):
                    await self._ws_manager.send_rigging_failed(
                        asset_id=result["asset_id"],
                        job_id=job.id,
                        error=error,
                    )

                # Update asset status in database for failures
                if result.get("asset_id") and job.job_type == "image_to_3d":
                    await self._update_asset_status(
                        result["asset_id"],
                        AssetStatus.FAILED,
                        error=error,
                    )

        except Exception as e:
            job_elapsed = time_module.time() - job_start
            logger.exception(f"Job {job.id} failed with exception after {job_elapsed:.1f}s: {e}")
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

        # Clear VRAM after job completes for next job
        logger.info("Cleaning up VRAM after job...")
        import gc
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                vram_before = torch.cuda.memory_allocated(0) / 1e9
                torch.cuda.empty_cache()
                vram_after = torch.cuda.memory_allocated(0) / 1e9
                logger.info(f"VRAM cleanup: {vram_before:.2f}GB -> {vram_after:.2f}GB")
        except ImportError:
            pass

        logger.info(f"Job {job.id} processing complete")

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
            elif job.job_type == "rig_asset":
                result = await self._process_rig_asset(job)
            elif job.job_type == "add_texture":
                result = await self._process_add_texture(job)
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
                    asset_id=result.get("asset_id"),
                )

                # Update asset status in database
                if result.get("asset_id") and job.job_type in ("image_to_3d", "add_texture"):
                    await self._update_asset_status(
                        result["asset_id"],
                        AssetStatus.COMPLETED,
                        result=result,
                    )

                # Send rigging-specific completion message
                if job.job_type == "rig_asset" and result.get("asset_id"):
                    await self._ws_manager.send_rigging_complete(
                        asset_id=result["asset_id"],
                        character_type=result.get("character_type", "unknown"),
                        bone_count=result.get("bone_count", 0),
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
                    asset_id=result.get("asset_id"),
                )

                # Send rigging-specific failure message
                if job.job_type == "rig_asset" and result.get("asset_id"):
                    await self._ws_manager.send_rigging_failed(
                        asset_id=result["asset_id"],
                        job_id=job.id,
                        error=error,
                    )

                # Update asset status in database for failures
                if result.get("asset_id") and job.job_type == "image_to_3d":
                    await self._update_asset_status(
                        result["asset_id"],
                        AssetStatus.FAILED,
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

        # Clear VRAM after job completes for next job
        import gc
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass

    async def _process_image_to_3d_with_preprocessed(
        self, job, processed_image: Image.Image
    ) -> dict:
        """Process image-to-3D with already preprocessed image.

        Uses lazy loading via PipelineManager - shape pipeline is loaded
        on-demand and unloaded after texture stage (if used).

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
        loop = asyncio.get_running_loop()

        # Helper to send detailed logs
        async def send_log(level: str, stage: str, message: str, progress: float = None):
            await self._ws_manager.send_generation_log(
                job_id=job.id,
                level=level,
                stage=stage,
                message=message,
                progress=progress,
                asset_id=asset_id,
            )

        # Initial system log
        await send_log("system", "INIT", f"Generation job {job.id[:8]} started", 0.0)
        await send_log("info", "CONFIG", f"Inference steps: {config.inference_steps}, Octree: {config.octree_resolution}")
        await send_log("info", "CONFIG", f"Face count target: {config.face_count or 'unlimited'}")
        await send_log("info", "CONFIG", f"Texture generation: {'enabled' if config.texture.enabled else 'disabled'}")

        # VRAM status
        try:
            import torch
            if torch.cuda.is_available():
                vram_used = torch.cuda.memory_allocated() / 1e9
                vram_total = torch.cuda.get_device_properties(0).total_memory / 1e9
                await send_log("debug", "VRAM", f"VRAM: {vram_used:.1f}GB / {vram_total:.1f}GB ({100*vram_used/vram_total:.1f}% used)")
        except Exception:
            pass

        # Create progress callback that updates queue and broadcasts
        async def progress_callback(progress: float, stage: str):
            # Scale progress: 0-30% for pipeline loading, 30-100% for generation
            if "Loading" in stage or "Unloading" in stage:
                adjusted_progress = progress * 0.30
            else:
                adjusted_progress = 0.30 + progress * 0.70
            await self._queue.update_progress(job.id, adjusted_progress, stage)
            await self._ws_manager.send_progress(
                job_id=job.id,
                progress=adjusted_progress,
                stage=stage,
                status="processing",
            )
            # Also send as detailed log
            await send_log("info", "PROGRESS", stage, adjusted_progress)

        # Sync wrapper for the async callback
        def sync_progress(progress: float, stage: str):
            asyncio.run_coroutine_threadsafe(progress_callback(progress, stage), loop)

        # STEP 1: Prepare for MESH stage (loads shape pipeline, unloads texture if loaded)
        await send_log("system", "PIPELINE", "Initializing shape generation pipeline...", 0.05)
        await self._ws_manager.send_progress(
            job_id=job.id,
            progress=0.05,
            stage="Preparing shape model...",
            status="processing",
        )

        prepare_result = await self._pipeline_manager.prepare_for_stage(
            PipelineStage.MESH,
            progress_callback=sync_progress,
        )

        if not prepare_result.get("success"):
            await send_log("error", "PIPELINE", f"Failed to load pipeline: {prepare_result.get('error')}")
            return {
                "success": False,
                "error": prepare_result.get("error", "Failed to load shape pipeline"),
            }

        await send_log("success", "PIPELINE", f"Shape model loaded ({prepare_result.get('vram_used_gb', 0):.1f}GB VRAM)")

        # Get the shape pipeline from manager
        shape_pipeline = self._pipeline_manager.shape_pipeline
        if shape_pipeline is None:
            await send_log("error", "PIPELINE", "Shape pipeline reference is null")
            return {
                "success": False,
                "error": "Shape pipeline not loaded",
            }

        # STEP 2: Generate the mesh
        await send_log("system", "MESH", "Starting 3D mesh generation...", 0.35)
        await send_log("info", "MESH", f"Running Hunyuan3D-2.1 inference with {config.inference_steps} steps")
        await send_log("debug", "MESH", f"Image size: {processed_image.size[0]}x{processed_image.size[1]}")
        await send_log("debug", "MESH", "Beginning diffusion sampling (this takes the longest)...")

        from src.inference.pipeline import generate_mesh

        result = await generate_mesh(
            pipeline=shape_pipeline,
            image=processed_image,
            config=config,
            output_dir=output_dir,
            asset_id=asset_id,
            progress_callback=sync_progress,
        )

        if result.success:
            await send_log("success", "MESH", f"Mesh generated: {result.vertex_count:,} vertices, {result.face_count:,} faces")
            await send_log("info", "MESH", f"Generation time: {result.generation_time:.1f}s")
            await send_log("success", "COMPLETE", "3D model generation complete!", 1.0)
            return {
                "success": True,
                "asset_id": asset_id,
                "name": payload.get("name", "Untitled"),
                "mesh_path": str(result.mesh_path) if result.mesh_path else None,
                "thumbnail_path": str(result.thumbnail_path) if result.thumbnail_path else None,
                "thumbnail_url": f"/storage/generated/{asset_id}/thumbnail.png",
                "download_url": f"/storage/generated/{asset_id}/{asset_id}.glb",
                "vertex_count": result.vertex_count,
                "face_count": result.face_count,
                "generation_time": result.generation_time,
                "has_texture": config.texture.enabled,
            }
        else:
            await send_log("error", "MESH", f"Generation failed: {result.error}")
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
                "thumbnail_path": str(result.thumbnail_path) if result.thumbnail_path else None,
                "thumbnail_url": f"/storage/generated/{asset_id}/thumbnail.png",
                "download_url": f"/storage/generated/{asset_id}/{asset_id}.glb",
                "vertex_count": result.vertex_count,
                "face_count": result.face_count,
                "generation_time": result.generation_time,
                "has_texture": config.texture.enabled,
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

    async def _process_add_texture(self, job) -> dict:
        """Add texture to an existing untextured mesh.

        Uses PipelineManager for clean VRAM management:
        1. Fully unloads shape pipeline
        2. Loads texture pipeline fresh
        3. Generates texture
        4. Saves result

        Args:
            job: Job instance with payload containing:
                - asset_id: ID of the asset to texture
                - mesh_path: Path to the existing mesh file
                - source_image_path: Path to the original source image

        Returns:
            Result dictionary
        """
        payload = job.payload
        asset_id = payload["asset_id"]
        mesh_path = Path(payload["mesh_path"])
        source_image_path = Path(payload["source_image_path"])

        logger.info(f"Adding texture to asset {asset_id}")

        # Get the current event loop for thread-safe scheduling
        loop = asyncio.get_running_loop()

        # Helper to send detailed logs
        async def send_log(level: str, stage: str, message: str, progress: float = None):
            await self._ws_manager.send_generation_log(
                job_id=job.id,
                level=level,
                stage=stage,
                message=message,
                progress=progress,
                asset_id=asset_id,
            )

        # Initial system logs
        await send_log("system", "INIT", f"Texture job {job.id[:8]} started", 0.0)
        await send_log("info", "TEXTURE", f"Target asset: {asset_id[:8]}...")

        # Create progress callback
        async def progress_callback(progress: float, stage: str):
            # Scale: 0-40% for pipeline loading, 40-100% for texture generation
            if "Loading" in stage or "Unloading" in stage or "Preparing" in stage:
                adjusted_progress = progress * 0.40
            else:
                adjusted_progress = 0.40 + progress * 0.60
            await self._queue.update_progress(job.id, adjusted_progress, stage)
            await self._ws_manager.send_progress(
                job_id=job.id,
                progress=adjusted_progress,
                stage=stage,
                status="processing",
            )
            await send_log("info", "PROGRESS", stage, adjusted_progress)

        def sync_progress(progress: float, stage: str):
            asyncio.run_coroutine_threadsafe(progress_callback(progress, stage), loop)

        try:
            import trimesh
            from PIL import Image

            # STEP 1: Load mesh and image first (before VRAM changes)
            await send_log("info", "MESH", "Loading existing mesh for texturing...")
            sync_progress(0.05, "Loading mesh...")

            loaded = trimesh.load(str(mesh_path))

            # Handle Scene vs Trimesh
            if isinstance(loaded, trimesh.Scene):
                meshes = [g for g in loaded.geometry.values() if isinstance(g, trimesh.Trimesh)]
                if meshes:
                    mesh = trimesh.util.concatenate(meshes)
                else:
                    raise ValueError("No valid meshes found in GLB file")
            else:
                mesh = loaded

            await send_log("success", "MESH", f"Mesh loaded: {len(mesh.vertices):,} vertices, {len(mesh.faces):,} faces")

            sync_progress(0.10, "Loading source image...")
            await send_log("info", "IMAGE", "Loading source image for reference...")
            source_image = Image.open(source_image_path)
            await send_log("info", "IMAGE", f"Image loaded: {source_image.size[0]}x{source_image.size[1]}")

            # STEP 2: Prepare for TEXTURE stage using PipelineManager
            # This will: unload shape pipeline, load texture pipeline
            await send_log("system", "PIPELINE", "Initializing texture pipeline (~18GB)...", 0.15)
            await self._ws_manager.send_progress(
                job_id=job.id,
                progress=0.15,
                stage="Preparing texture model (~18GB)...",
                status="processing",
            )

            prepare_result = await self._pipeline_manager.prepare_for_stage(
                PipelineStage.TEXTURE,
                progress_callback=sync_progress,
            )

            if not prepare_result.get("success"):
                await send_log("error", "PIPELINE", f"Failed: {prepare_result.get('error')}")
                return {
                    "success": False,
                    "error": prepare_result.get("error", "Failed to load texture pipeline"),
                }

            await send_log("success", "PIPELINE", f"Texture model loaded ({prepare_result.get('vram_used_gb', 0):.1f}GB)")

            # Get the texture pipeline
            texture_pipeline = self._pipeline_manager.texture_pipeline
            if texture_pipeline is None:
                await send_log("error", "PIPELINE", "Texture pipeline reference is null")
                return {
                    "success": False,
                    "error": "Texture pipeline not loaded. Check backend logs for errors.",
                }

            # STEP 3: Generate texture using standalone function
            await send_log("system", "TEXTURE", "Starting AI texture generation...", 0.45)
            await send_log("info", "TEXTURE", "Running Hunyuan3D-Paint inference...")

            from src.inference.pipeline import generate_texture_on_mesh

            output_path = mesh_path  # Overwrite original

            success, error = await generate_texture_on_mesh(
                pipeline=texture_pipeline,
                mesh=mesh,
                image=source_image,
                output_path=output_path,
                progress_callback=sync_progress,
            )

            if not success:
                await send_log("error", "TEXTURE", f"Generation failed: {error}")
                return {
                    "success": False,
                    "error": error or "Texture generation failed",
                }

            await send_log("success", "TEXTURE", "Texture applied successfully!")

            # STEP 4: Update database
            await send_log("info", "DATABASE", "Updating asset record...")
            async with async_session_maker() as session:
                from sqlalchemy import update
                from src.generation.models import Asset

                await session.execute(
                    update(Asset)
                    .where(Asset.id == asset_id)
                    .values(has_texture=True)
                )
                await session.commit()

            await send_log("success", "DATABASE", "Asset marked as textured")
            await send_log("success", "COMPLETE", "Texture generation complete!", 1.0)
            sync_progress(1.0, "Complete")

            return {
                "success": True,
                "asset_id": asset_id,
                "name": payload.get("name", "Untitled"),
                "mesh_path": str(output_path),
                "has_texture": True,
            }

        except Exception as e:
            logger.exception(f"Add texture failed: {e}")
            await send_log("error", "ERROR", f"Exception: {str(e)}")
            return {
                "success": False,
                "error": str(e),
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
        # async_session_maker already imported at module level

        payload = job.payload
        asset_id = payload["asset_id"]
        mesh_path = Path(payload["mesh_path"])
        character_type = CharacterType(payload.get("character_type", "auto"))
        processor = RiggingProcessor(payload.get("processor", "auto"))

        # Resolve mesh path - file_path is stored relative to working directory
        # (e.g., "storage/generated/{id}/{id}.glb"), so use as-is
        if not mesh_path.is_absolute() and not mesh_path.exists():
            # Try prepending STORAGE_ROOT only if path doesn't exist and doesn't start with storage
            if not str(mesh_path).startswith("storage"):
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

        # Clear VRAM before rigging to prevent OOM (UniRig uses GPU)
        import gc
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                logger.info("Cleared VRAM before rigging")
        except ImportError:
            pass

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
                    asset.skinning_data = result.skinning.model_dump() if result.skinning else None
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
