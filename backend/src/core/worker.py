"""Background worker for processing GPU jobs from the queue."""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from src.config import settings
from src.core.queue import JobQueue, JobStatus, get_queue
from src.core.websocket_manager import WebSocketManager, get_websocket_manager
from src.inference.config import GenerationConfig, TextureConfig, OutputFormat, GenerationMode
from src.inference.pipeline import Hunyuan3DPipeline, get_pipeline

logger = logging.getLogger(__name__)


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

        # Initialize pipeline (loads models)
        logger.info("Initializing inference pipeline...")
        await self._pipeline.initialize()
        logger.info("Pipeline initialized")

        # Start processing loop
        self._task = asyncio.create_task(self._process_loop())
        logger.info("Background worker started")

    async def stop(self) -> None:
        """Stop the background worker gracefully."""
        if not self._running:
            return

        logger.info("Stopping background worker...")
        self._running = False

        # Cancel the processing task
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        # Cleanup pipeline
        await self._pipeline.cleanup()

        logger.info("Background worker stopped")

    async def _process_loop(self) -> None:
        """Main processing loop."""
        while self._running:
            try:
                # Get next job from queue
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
