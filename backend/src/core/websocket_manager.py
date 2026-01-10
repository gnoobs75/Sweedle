"""WebSocket connection manager for real-time updates."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Optional, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections and message broadcasting.

    Handles connection lifecycle, message routing, and broadcasting
    progress updates to all connected clients.
    """

    def __init__(self):
        """Initialize manager."""
        self._connections: Set[WebSocket] = set()
        self._subscriptions: dict[str, Set[WebSocket]] = {}  # job_id -> connections
        self._lock = asyncio.Lock()

    @property
    def connection_count(self) -> int:
        """Number of active connections."""
        return len(self._connections)

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection.

        Args:
            websocket: FastAPI WebSocket instance
        """
        await websocket.accept()

        async with self._lock:
            self._connections.add(websocket)

        logger.info(f"WebSocket connected. Total connections: {len(self._connections)}")

    async def disconnect(self, websocket: WebSocket) -> None:
        """Handle WebSocket disconnection.

        Args:
            websocket: FastAPI WebSocket instance
        """
        async with self._lock:
            self._connections.discard(websocket)

            # Remove from all subscriptions
            for job_id in list(self._subscriptions.keys()):
                self._subscriptions[job_id].discard(websocket)
                if not self._subscriptions[job_id]:
                    del self._subscriptions[job_id]

        logger.info(f"WebSocket disconnected. Total connections: {len(self._connections)}")

    async def subscribe(self, websocket: WebSocket, job_id: str) -> None:
        """Subscribe a connection to job updates.

        Args:
            websocket: WebSocket connection
            job_id: Job ID to subscribe to
        """
        async with self._lock:
            if job_id not in self._subscriptions:
                self._subscriptions[job_id] = set()
            self._subscriptions[job_id].add(websocket)

        logger.debug(f"WebSocket subscribed to job {job_id}")

    async def unsubscribe(self, websocket: WebSocket, job_id: str) -> None:
        """Unsubscribe from job updates.

        Args:
            websocket: WebSocket connection
            job_id: Job ID to unsubscribe from
        """
        async with self._lock:
            if job_id in self._subscriptions:
                self._subscriptions[job_id].discard(websocket)
                if not self._subscriptions[job_id]:
                    del self._subscriptions[job_id]

    async def broadcast(self, message: dict) -> None:
        """Broadcast message to all connected clients.

        Args:
            message: Message dictionary to send
        """
        if not self._connections:
            return

        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.utcnow().isoformat()

        data = json.dumps(message)
        disconnected = []

        for connection in self._connections.copy():
            try:
                await connection.send_text(data)
            except Exception as e:
                logger.debug(f"Failed to send to connection: {e}")
                disconnected.append(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            await self.disconnect(conn)

    async def send_to_job(self, job_id: str, message: dict) -> None:
        """Send message to subscribers of a specific job.

        Args:
            job_id: Job ID
            message: Message dictionary to send
        """
        async with self._lock:
            subscribers = self._subscriptions.get(job_id, set()).copy()

        if not subscribers:
            # Fall back to broadcast for single-user setup
            await self.broadcast(message)
            return

        if "timestamp" not in message:
            message["timestamp"] = datetime.utcnow().isoformat()

        data = json.dumps(message)
        disconnected = []

        for connection in subscribers:
            try:
                await connection.send_text(data)
            except Exception as e:
                logger.debug(f"Failed to send to subscriber: {e}")
                disconnected.append(connection)

        for conn in disconnected:
            await self.disconnect(conn)

    async def send_progress(
        self,
        job_id: str,
        progress: float,
        stage: str,
        status: str = "processing",
        result: Optional[dict] = None,
        error: Optional[str] = None,
        asset_id: Optional[str] = None,
    ) -> None:
        """Send progress update for a job.

        Args:
            job_id: Job ID
            progress: Progress value (0.0-1.0)
            stage: Current stage description
            status: Job status
            result: Result data (for completed jobs)
            error: Error message (for failed jobs)
            asset_id: Associated asset ID
        """
        message = {
            "type": "progress",
            "job_id": job_id,
            "progress": progress,
            "stage": stage,
            "status": status,
        }

        if asset_id is not None:
            message["asset_id"] = asset_id

        if result is not None:
            message["result"] = result

        if error is not None:
            message["error"] = error

        await self.broadcast(message)

    async def send_queue_status(self, status: dict) -> None:
        """Send queue status update.

        Args:
            status: Queue status dictionary
        """
        message = {
            "type": "queue_status",
            **status,
        }
        await self.broadcast(message)

    async def send_job_created(
        self,
        job_id: str,
        asset_id: str,
        job_type: str,
        position: int,
    ) -> None:
        """Send notification when a job is created.

        Args:
            job_id: Job ID
            asset_id: Associated asset ID
            job_type: Type of job
            position: Position in queue
        """
        message = {
            "type": "job_created",
            "job_id": job_id,
            "asset_id": asset_id,
            "job_type": job_type,
            "queue_position": position,
        }
        await self.broadcast(message)

    async def send_asset_ready(
        self,
        asset_id: str,
        name: str,
        thumbnail_url: Optional[str] = None,
        download_url: Optional[str] = None,
    ) -> None:
        """Send notification when an asset is ready.

        Args:
            asset_id: Asset ID
            name: Asset name
            thumbnail_url: URL to thumbnail
            download_url: URL to download asset
        """
        message = {
            "type": "asset_ready",
            "asset_id": asset_id,
            "name": name,
            "thumbnail_url": thumbnail_url,
            "download_url": download_url,
        }
        await self.broadcast(message)

    async def send_error(
        self,
        code: str,
        message_text: str,
        job_id: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> None:
        """Send error notification.

        Args:
            code: Error code
            message_text: Error message
            job_id: Associated job ID
            details: Additional error details
        """
        message = {
            "type": "error",
            "code": code,
            "message": message_text,
        }

        if job_id:
            message["job_id"] = job_id

        if details:
            message["details"] = details

        await self.broadcast(message)

    async def send_rigging_progress(
        self,
        job_id: str,
        progress: float,
        stage: str,
        detected_type: Optional[str] = None,
    ) -> None:
        """Send rigging-specific progress update.

        Args:
            job_id: Job ID
            progress: Progress value (0.0-1.0)
            stage: Current processing stage
            detected_type: Detected character type (humanoid/quadruped)
        """
        message = {
            "type": "rigging_progress",
            "job_id": job_id,
            "progress": progress,
            "stage": stage,
        }

        if detected_type:
            message["detected_type"] = detected_type

        await self.broadcast(message)

    async def send_rigging_complete(
        self,
        asset_id: str,
        character_type: str,
        bone_count: int,
    ) -> None:
        """Send notification when rigging is complete.

        Args:
            asset_id: Asset ID that was rigged
            character_type: Detected character type
            bone_count: Number of bones in skeleton
        """
        message = {
            "type": "rigging_complete",
            "asset_id": asset_id,
            "character_type": character_type,
            "bone_count": bone_count,
        }
        await self.broadcast(message)


# Global manager instance
_manager: Optional[WebSocketManager] = None


def get_websocket_manager() -> WebSocketManager:
    """Get or create the global WebSocket manager instance."""
    global _manager
    if _manager is None:
        _manager = WebSocketManager()
    return _manager
