"""WebSocket endpoints for real-time design updates."""

import json
import logging
from typing import Any, Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()


# Connection manager for WebSocket clients
class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        # Map: request_id -> list of WebSocket connections
        self.active_connections: Dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, request_id: str) -> None:
        """Accept and register a WebSocket connection."""
        await websocket.accept()
        if request_id not in self.active_connections:
            self.active_connections[request_id] = []
        self.active_connections[request_id].append(websocket)
        logger.info(f"WebSocket connected for request {request_id}")

    def disconnect(self, websocket: WebSocket, request_id: str) -> None:
        """Remove a WebSocket connection."""
        if request_id in self.active_connections:
            self.active_connections[request_id].remove(websocket)
            if not self.active_connections[request_id]:
                del self.active_connections[request_id]
        logger.info(f"WebSocket disconnected for request {request_id}")

    async def send_update(self, request_id: str, message: Dict[str, Any]) -> None:
        """Send an update to all connected clients for a request."""
        if request_id in self.active_connections:
            for connection in self.active_connections[request_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending WebSocket update: {e}")


# Global connection manager
manager = ConnectionManager()


@router.websocket("/{request_id}")
async def websocket_endpoint(websocket: WebSocket, request_id: str):
    """
    WebSocket endpoint for real-time design updates.

    Clients connect to /ws/{request_id} to receive updates:
    - Status changes (planning, generating, executing, validating)
    - Progress updates (iteration counts, step completion)
    - Validation results
    - Error notifications

    Message format:
    {
        "type": "status" | "progress" | "validation" | "error" | "completed",
        "request_id": "...",
        "timestamp": "...",
        "data": {...}
    }

    Args:
        websocket: WebSocket connection
        request_id: Design request ID to subscribe to
    """
    await manager.connect(websocket, request_id)

    try:
        # Send initial connection confirmation
        await websocket.send_json(
            {
                "type": "connected",
                "request_id": request_id,
                "message": "WebSocket connected successfully",
            }
        )

        # Keep connection alive and listen for client messages (if any)
        while True:
            # Wait for any message from client (keep-alive, etc.)
            data = await websocket.receive_text()
            logger.debug(f"Received WebSocket message for {request_id}: {data}")

            # Echo back as acknowledgment
            await websocket.send_json(
                {
                    "type": "ack",
                    "request_id": request_id,
                    "received": data,
                }
            )

            # Handle stream_design messages
            try:
                msg = json.loads(data)
            except (json.JSONDecodeError, TypeError):
                msg = {}

            if msg.get("type") == "stream_design":
                prompt = msg.get("prompt", "")
                if prompt:
                    from ai_designer.api.deps import get_llm_provider
                    from ai_designer.schemas.llm_schemas import (
                        LLMMessage,
                        LLMRequest,
                        LLMRole,
                    )

                    llm_provider = get_llm_provider()
                    llm_request = LLMRequest(
                        messages=[LLMMessage(role=LLMRole.USER, content=prompt)],
                        model=llm_provider.default_model,
                    )
                    try:
                        async for chunk in llm_provider.complete_stream(llm_request):
                            await websocket.send_json(
                                {"type": "stream_chunk", "content": chunk}
                            )
                        await websocket.send_json({"type": "stream_done"})
                    except Exception as stream_err:  # noqa: BLE001
                        await websocket.send_json(
                            {"type": "error", "message": str(stream_err)}
                        )

    except WebSocketDisconnect:
        manager.disconnect(websocket, request_id)
        logger.info(f"WebSocket client disconnected from {request_id}")
    except Exception as e:
        logger.exception(f"WebSocket error for {request_id}: {e}")
        manager.disconnect(websocket, request_id)
