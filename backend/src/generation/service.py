"""Generation service - business logic for 3D generation."""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiofiles
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.generation.models import Asset, AssetStatus, GenerationJob, GenerationType, JobStatus
from src.generation.schemas import GenerationParameters
from src.inference.config import GenerationConfig, TextureConfig, OutputFormat, GenerationMode
from src.inference.pipeline import GenerationResult, Hunyuan3DPipeline, get_pipeline

logger = logging.getLogger(__name__)


class GenerationService:
    """Service for handling 3D generation requests."""

    def __init__(self, db: AsyncSession, pipeline: Optional[Hunyuan3DPipeline] = None):
        """Initialize service.

        Args:
            db: Database session
            pipeline: Optional pipeline instance (uses global if not provided)
        """
        self.db = db
        self.pipeline = pipeline or get_pipeline()

    async def save_upload(self, file: UploadFile) -> Path:
        """Save uploaded file to storage.

        Args:
            file: Uploaded file

        Returns:
            Path to saved file
        """
        # Create date-based directory
        today = datetime.now()
        upload_dir = settings.UPLOAD_DIR / str(today.year) / f"{today.month:02d}" / f"{today.day:02d}"
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename
        file_ext = Path(file.filename).suffix if file.filename else ".png"
        unique_name = f"{uuid.uuid4()}{file_ext}"
        file_path = upload_dir / unique_name

        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)

        logger.info(f"Saved upload to {file_path}")
        return file_path

    async def create_asset(
        self,
        name: str,
        source_type: GenerationType,
        source_image_path: Optional[Path] = None,
        source_prompt: Optional[str] = None,
        parameters: Optional[dict] = None,
    ) -> Asset:
        """Create a new asset record.

        Args:
            name: Asset name
            source_type: Type of generation
            source_image_path: Path to source image
            source_prompt: Text prompt (for text-to-3D)
            parameters: Generation parameters

        Returns:
            Created Asset instance
        """
        asset_id = str(uuid.uuid4())

        # Create asset directory
        asset_dir = settings.GENERATED_DIR / asset_id
        asset_dir.mkdir(parents=True, exist_ok=True)

        asset = Asset(
            id=asset_id,
            name=name,
            source_type=source_type,
            source_image_path=str(source_image_path) if source_image_path else None,
            source_prompt=source_prompt,
            generation_params=parameters,
            file_path=str(asset_dir / f"{asset_id}.glb"),
            status=AssetStatus.PENDING,
        )

        self.db.add(asset)
        await self.db.flush()

        logger.info(f"Created asset {asset_id}: {name}")
        return asset

    async def create_job(
        self,
        asset_id: str,
        job_type: str,
        payload: dict,
        priority: int = 1,
    ) -> GenerationJob:
        """Create a generation job.

        Args:
            asset_id: Associated asset ID
            job_type: Type of job (image_to_3d, text_to_3d)
            payload: Job payload data
            priority: Job priority (higher = more urgent)

        Returns:
            Created GenerationJob instance
        """
        job_id = str(uuid.uuid4())

        job = GenerationJob(
            id=job_id,
            asset_id=asset_id,
            job_type=job_type,
            payload=payload,
            priority=priority,
            status=JobStatus.PENDING,
        )

        self.db.add(job)
        await self.db.flush()

        logger.info(f"Created job {job_id} for asset {asset_id}")
        return job

    async def get_job(self, job_id: str) -> Optional[GenerationJob]:
        """Get job by ID."""
        result = await self.db.execute(
            select(GenerationJob).where(GenerationJob.id == job_id)
        )
        return result.scalar_one_or_none()

    async def get_asset(self, asset_id: str) -> Optional[Asset]:
        """Get asset by ID."""
        result = await self.db.execute(
            select(Asset).where(Asset.id == asset_id)
        )
        return result.scalar_one_or_none()

    async def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        progress: float = None,
        stage: str = None,
        error: str = None,
    ) -> None:
        """Update job status.

        Args:
            job_id: Job ID
            status: New status
            progress: Progress (0.0-1.0)
            stage: Current stage description
            error: Error message if failed
        """
        job = await self.get_job(job_id)
        if not job:
            return

        job.status = status

        if progress is not None:
            job.progress = progress

        if stage is not None:
            job.stage = stage

        if error is not None:
            job.error_message = error

        if status == JobStatus.PROCESSING and job.started_at is None:
            job.started_at = datetime.utcnow()

        if status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            job.completed_at = datetime.utcnow()

        await self.db.flush()

    async def update_asset_status(
        self,
        asset_id: str,
        status: AssetStatus,
        result: Optional[GenerationResult] = None,
        error: str = None,
    ) -> None:
        """Update asset status with generation results.

        Args:
            asset_id: Asset ID
            status: New status
            result: Generation result
            error: Error message if failed
        """
        asset = await self.get_asset(asset_id)
        if not asset:
            return

        asset.status = status

        if result and result.success:
            asset.file_path = str(result.mesh_path) if result.mesh_path else asset.file_path
            asset.thumbnail_path = str(result.thumbnail_path) if result.thumbnail_path else None
            asset.vertex_count = result.vertex_count
            asset.face_count = result.face_count
            asset.generation_time_seconds = result.generation_time

            # Get file size
            if result.mesh_path and result.mesh_path.exists():
                asset.file_size_bytes = result.mesh_path.stat().st_size

        if error:
            asset.error_message = error

        await self.db.flush()

    def params_to_config(self, params: GenerationParameters) -> GenerationConfig:
        """Convert API parameters to GenerationConfig.

        Args:
            params: API generation parameters

        Returns:
            GenerationConfig instance
        """
        return GenerationConfig(
            inference_steps=params.inference_steps,
            guidance_scale=params.guidance_scale,
            octree_resolution=params.octree_resolution,
            seed=params.seed,
            texture=TextureConfig(enabled=params.generate_texture),
            face_count=params.face_count,
            output_format=OutputFormat(params.output_format.value),
            mode=GenerationMode(params.mode.value),
        )

    async def process_generation(
        self,
        job_id: str,
        asset_id: str,
        image_path: Path,
        config: GenerationConfig,
        progress_callback=None,
    ) -> GenerationResult:
        """Process a generation job.

        Args:
            job_id: Job ID
            asset_id: Asset ID
            image_path: Path to input image
            config: Generation configuration
            progress_callback: Optional progress callback

        Returns:
            GenerationResult
        """
        # Update job status to processing
        await self.update_job_status(job_id, JobStatus.PROCESSING, 0.0, "Starting...")

        # Update asset status
        await self.update_asset_status(asset_id, AssetStatus.PROCESSING)

        # Get output directory
        output_dir = settings.GENERATED_DIR / asset_id

        # Create progress wrapper that updates DB
        async def db_progress_callback(progress: float, message: str):
            await self.update_job_status(job_id, JobStatus.PROCESSING, progress, message)
            if progress_callback:
                progress_callback(progress, message)

        # Run generation (use sync callback since pipeline is sync internally)
        def sync_progress(progress: float, message: str):
            # We can't easily await here, so just call the external callback
            if progress_callback:
                progress_callback(progress, message)

        try:
            result = await self.pipeline.generate(
                image=image_path,
                config=config,
                output_dir=output_dir,
                asset_id=asset_id,
                progress_callback=sync_progress,
            )

            if result.success:
                await self.update_job_status(job_id, JobStatus.COMPLETED, 1.0, "Complete")
                await self.update_asset_status(asset_id, AssetStatus.COMPLETED, result)
            else:
                await self.update_job_status(job_id, JobStatus.FAILED, error=result.error)
                await self.update_asset_status(asset_id, AssetStatus.FAILED, error=result.error)

            return result

        except Exception as e:
            logger.exception(f"Generation failed for job {job_id}")
            error_msg = str(e)
            await self.update_job_status(job_id, JobStatus.FAILED, error=error_msg)
            await self.update_asset_status(asset_id, AssetStatus.FAILED, error=error_msg)

            return GenerationResult(
                success=False,
                error=error_msg,
            )
