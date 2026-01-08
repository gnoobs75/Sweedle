"""Job queue system using asyncio for batch processing."""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class JobPriority(int, Enum):
    """Job priority levels. Lower value = higher priority."""
    HIGH = 0
    NORMAL = 1
    LOW = 2


class JobStatus(str, Enum):
    """Job status values."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Job:
    """Represents a generation job in the queue."""
    id: str
    job_type: str
    payload: dict
    priority: JobPriority = JobPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    stage: str = "pending"
    error: Optional[str] = None
    result: Optional[Any] = None

    def __lt__(self, other: "Job") -> bool:
        """Compare for priority queue ordering."""
        if self.priority != other.priority:
            return self.priority.value < other.priority.value
        return self.created_at < other.created_at


class JobQueue:
    """Async job queue with priority support.

    Uses asyncio.PriorityQueue for efficient ordering and
    provides methods for job management and status tracking.
    """

    def __init__(self, max_size: int = 100):
        """Initialize queue.

        Args:
            max_size: Maximum number of jobs in queue
        """
        self._queue: asyncio.PriorityQueue[Job] = asyncio.PriorityQueue(maxsize=max_size)
        self._jobs: dict[str, Job] = {}
        self._current_job: Optional[Job] = None
        self._lock = asyncio.Lock()
        self._max_size = max_size

        # Statistics
        self._completed_count = 0
        self._failed_count = 0

    @property
    def size(self) -> int:
        """Current queue size."""
        return self._queue.qsize()

    @property
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return self._queue.empty()

    @property
    def is_full(self) -> bool:
        """Check if queue is full."""
        return self._queue.full()

    @property
    def current_job(self) -> Optional[Job]:
        """Currently processing job."""
        return self._current_job

    async def enqueue(
        self,
        job_id: str,
        job_type: str,
        payload: dict,
        priority: JobPriority = JobPriority.NORMAL,
    ) -> Job:
        """Add a job to the queue.

        Args:
            job_id: Unique job identifier
            job_type: Type of job (e.g., "image_to_3d")
            payload: Job data
            priority: Job priority level

        Returns:
            Created Job instance

        Raises:
            asyncio.QueueFull: If queue is at capacity
        """
        job = Job(
            id=job_id,
            job_type=job_type,
            payload=payload,
            priority=priority,
        )

        async with self._lock:
            if job_id in self._jobs:
                raise ValueError(f"Job {job_id} already exists")

            self._jobs[job_id] = job

        await self._queue.put(job)
        logger.info(f"Enqueued job {job_id} with priority {priority.name}")

        return job

    async def dequeue(self) -> Optional[Job]:
        """Get the next job from the queue.

        This method blocks until a job is available.

        Returns:
            Next Job to process, or None if cancelled
        """
        try:
            job = await self._queue.get()

            async with self._lock:
                # Check if job was cancelled while waiting
                if job.status == JobStatus.CANCELLED:
                    self._queue.task_done()
                    return await self.dequeue()

                job.status = JobStatus.PROCESSING
                job.started_at = datetime.utcnow()
                self._current_job = job

            logger.info(f"Dequeued job {job.id}")
            return job

        except asyncio.CancelledError:
            return None

    async def complete(
        self,
        job_id: str,
        result: Any = None,
        error: Optional[str] = None,
    ) -> None:
        """Mark a job as completed.

        Args:
            job_id: Job ID
            result: Job result data
            error: Error message if failed
        """
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                logger.warning(f"Attempted to complete unknown job {job_id}")
                return

            job.completed_at = datetime.utcnow()
            job.result = result
            job.error = error
            job.progress = 1.0 if not error else job.progress

            if error:
                job.status = JobStatus.FAILED
                self._failed_count += 1
            else:
                job.status = JobStatus.COMPLETED
                self._completed_count += 1

            if self._current_job and self._current_job.id == job_id:
                self._current_job = None

        self._queue.task_done()
        logger.info(f"Completed job {job_id} with status {job.status.value}")

    async def update_progress(
        self,
        job_id: str,
        progress: float,
        stage: str = "",
    ) -> None:
        """Update job progress.

        Args:
            job_id: Job ID
            progress: Progress value (0.0-1.0)
            stage: Current stage description
        """
        async with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.progress = min(max(progress, 0.0), 1.0)
                if stage:
                    job.stage = stage

    async def cancel(self, job_id: str) -> bool:
        """Cancel a pending job.

        Note: Jobs that are already processing cannot be cancelled.

        Args:
            job_id: Job ID to cancel

        Returns:
            True if cancelled, False if not cancellable
        """
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False

            if job.status != JobStatus.PENDING:
                return False

            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.utcnow()
            job.error = "Cancelled by user"

        logger.info(f"Cancelled job {job_id}")
        return True

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID.

        Args:
            job_id: Job ID

        Returns:
            Job instance or None
        """
        return self._jobs.get(job_id)

    def get_status(self) -> dict:
        """Get queue status summary.

        Returns:
            Dictionary with queue statistics
        """
        pending = sum(1 for j in self._jobs.values() if j.status == JobStatus.PENDING)
        processing = 1 if self._current_job else 0

        return {
            "queue_size": self._queue.qsize(),
            "current_job_id": self._current_job.id if self._current_job else None,
            "pending_count": pending,
            "processing_count": processing,
            "completed_count": self._completed_count,
            "failed_count": self._failed_count,
            "total_jobs": len(self._jobs),
        }

    def get_pending_jobs(self) -> list[Job]:
        """Get all pending jobs in priority order.

        Returns:
            List of pending jobs
        """
        jobs = [j for j in self._jobs.values() if j.status == JobStatus.PENDING]
        return sorted(jobs)

    def get_recent_jobs(self, limit: int = 20) -> list[Job]:
        """Get recent jobs (all statuses).

        Args:
            limit: Maximum number of jobs to return

        Returns:
            List of recent jobs, newest first
        """
        jobs = sorted(
            self._jobs.values(),
            key=lambda j: j.created_at,
            reverse=True,
        )
        return jobs[:limit]

    async def clear_completed(self, max_age_hours: int = 24) -> int:
        """Remove old completed/failed jobs from memory.

        Args:
            max_age_hours: Remove jobs older than this

        Returns:
            Number of jobs removed
        """
        cutoff = datetime.utcnow()
        removed = 0

        async with self._lock:
            to_remove = []
            for job_id, job in self._jobs.items():
                if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                    if job.completed_at:
                        age_hours = (cutoff - job.completed_at).total_seconds() / 3600
                        if age_hours > max_age_hours:
                            to_remove.append(job_id)

            for job_id in to_remove:
                del self._jobs[job_id]
                removed += 1

        if removed:
            logger.info(f"Cleared {removed} old jobs from queue")

        return removed


# Global queue instance
_queue: Optional[JobQueue] = None


def get_queue() -> JobQueue:
    """Get or create the global queue instance."""
    global _queue
    if _queue is None:
        _queue = JobQueue()
    return _queue
