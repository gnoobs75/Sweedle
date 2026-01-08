"""WebSocket message schemas."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """WebSocket message types."""
    # Server -> Client
    PROGRESS = "progress"
    QUEUE_STATUS = "queue_status"
    JOB_CREATED = "job_created"
    ASSET_READY = "asset_ready"
    ERROR = "error"
    PONG = "pong"

    # Client -> Server
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    REQUEST_STATUS = "request_status"
    PING = "ping"


# Server -> Client Messages

class ProgressMessage(BaseModel):
    """Progress update for a job."""
    type: str = Field(default=MessageType.PROGRESS)
    job_id: str
    progress: float = Field(ge=0.0, le=1.0)
    stage: str
    status: str  # pending, processing, completed, failed
    result: Optional[dict] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class QueueStatusMessage(BaseModel):
    """Queue status update."""
    type: str = Field(default=MessageType.QUEUE_STATUS)
    queue_size: int
    current_job_id: Optional[str]
    pending_count: int
    processing_count: int
    completed_count: int
    failed_count: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class JobCreatedMessage(BaseModel):
    """Notification when a job is created."""
    type: str = Field(default=MessageType.JOB_CREATED)
    job_id: str
    asset_id: str
    job_type: str
    queue_position: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AssetReadyMessage(BaseModel):
    """Notification when an asset is ready."""
    type: str = Field(default=MessageType.ASSET_READY)
    asset_id: str
    name: str
    thumbnail_url: Optional[str] = None
    download_url: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorMessage(BaseModel):
    """Error notification."""
    type: str = Field(default=MessageType.ERROR)
    code: str
    message: str
    job_id: Optional[str] = None
    details: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Client -> Server Messages

class SubscribeMessage(BaseModel):
    """Subscribe to job updates."""
    action: str = Field(default="subscribe")
    job_id: str


class UnsubscribeMessage(BaseModel):
    """Unsubscribe from job updates."""
    action: str = Field(default="unsubscribe")
    job_id: str


class RequestStatusMessage(BaseModel):
    """Request current queue status."""
    action: str = Field(default="request_status")


class PingMessage(BaseModel):
    """Keepalive ping."""
    action: str = Field(default="ping")
