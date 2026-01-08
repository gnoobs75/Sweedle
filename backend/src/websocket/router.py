"""WebSocket router for real-time updates."""

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.core.queue import get_queue
from src.core.websocket_manager import get_websocket_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/progress")
async def websocket_progress_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time progress updates.

    Clients can:
    - Receive broadcast progress updates for all jobs
    - Subscribe to specific job updates
    - Request current queue status
    - Send ping/pong for keepalive

    Message format (client -> server):
    ```json
    {"action": "subscribe", "job_id": "..."}
    {"action": "unsubscribe", "job_id": "..."}
    {"action": "request_status"}
    {"action": "ping"}
    ```

    Message format (server -> client):
    ```json
    {"type": "progress", "job_id": "...", "progress": 0.5, "stage": "...", "status": "processing"}
    {"type": "queue_status", "queue_size": 5, "pending_count": 4, ...}
    {"type": "job_created", "job_id": "...", "asset_id": "...", ...}
    {"type": "asset_ready", "asset_id": "...", "name": "...", ...}
    {"type": "error", "code": "...", "message": "..."}
    {"type": "pong"}
    ```
    """
    ws_manager = get_websocket_manager()
    queue = get_queue()

    await ws_manager.connect(websocket)

    try:
        # Send initial queue status
        await websocket.send_json({
            "type": "queue_status",
            **queue.get_status(),
        })

        while True:
            # Receive messages from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                action = message.get("action")

                if action == "subscribe":
                    job_id = message.get("job_id")
                    if job_id:
                        await ws_manager.subscribe(websocket, job_id)

                        # Send current job status if exists
                        job = queue.get_job(job_id)
                        if job:
                            await websocket.send_json({
                                "type": "progress",
                                "job_id": job.id,
                                "progress": job.progress,
                                "stage": job.stage,
                                "status": job.status.value,
                            })

                elif action == "unsubscribe":
                    job_id = message.get("job_id")
                    if job_id:
                        await ws_manager.unsubscribe(websocket, job_id)

                elif action == "request_status":
                    await websocket.send_json({
                        "type": "queue_status",
                        **queue.get_status(),
                    })

                elif action == "ping":
                    await websocket.send_json({"type": "pong"})

                else:
                    logger.warning(f"Unknown WebSocket action: {action}")

            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received: {data}")
                await websocket.send_json({
                    "type": "error",
                    "code": "invalid_json",
                    "message": "Invalid JSON format",
                })

    except WebSocketDisconnect:
        logger.debug("WebSocket client disconnected")

    except Exception as e:
        logger.exception(f"WebSocket error: {e}")

    finally:
        await ws_manager.disconnect(websocket)
