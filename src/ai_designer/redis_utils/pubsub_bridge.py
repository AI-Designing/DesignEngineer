"""
Redis Pub/Sub to WebSocket bridge for real-time design notifications.

Listens to Redis Pub/Sub channels and forwards events to connected WebSocket clients,
enabling real-time updates for design workflows.
"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


class PubSubBridge:
    """
    Bridge between Redis Pub/Sub and WebSocket connections.

    Subscribes to Redis channels for design events and forwards them to
    WebSocket clients in real-time.
    """

    def __init__(self, redis_client, websocket_manager=None):
        """
        Initialize Pub/Sub bridge.

        Args:
            redis_client: RedisClient instance
            websocket_manager: WebSocket ConnectionManager from api/routes/ws.py (optional)
        """
        self.redis_client = redis_client
        self.websocket_manager = websocket_manager
        self.pubsub = None
        self.running = False
        self._listener_task = None

    def _get_channel_pattern(self) -> str:
        """Get channel pattern for all design events."""
        return "design:*:events"

    async def start_listener(self) -> None:
        """
        Start listening to Redis Pub/Sub channels.

        This should be called as a background task in the FastAPI lifespan.
        """
        if self.running:
            logger.warning("Pub/Sub listener already running")
            return

        try:
            # Subscribe to all design event channels using pattern matching
            self.pubsub = self.redis_client.subscribe("__keyevent@0__:*")
            # Note: Pattern subscription requires CONFIG SET notify-keyspace-events
            # For now, we'll manually subscribe to known channels

            self.running = True
            logger.info("Started Redis Pub/Sub listener")

            # Run listener in background
            self._listener_task = asyncio.create_task(self._listen_loop())

        except Exception as e:
            logger.error(f"Failed to start Pub/Sub listener: {e}")
            self.running = False

    async def _listen_loop(self) -> None:
        """Main loop for listening to Pub/Sub messages."""
        if not self.pubsub:
            logger.error("PubSub not initialized")
            return

        logger.info("Pub/Sub listener loop started")

        try:
            while self.running:
                # Get message with timeout to allow periodic checking of running flag
                message = self.pubsub.get_message(timeout=1.0)

                if message and message["type"] == "message":
                    await self._handle_message(message)

                # Small delay to prevent tight loop
                await asyncio.sleep(0.01)

        except Exception as e:
            logger.error(f"Error in Pub/Sub listener loop: {e}")
        finally:
            logger.info("Pub/Sub listener loop stopped")

    async def _handle_message(self, message: Dict[str, Any]) -> None:
        """
        Handle incoming Pub/Sub message and forward to WebSocket.

        Args:
            message: Redis Pub/Sub message dict
        """
        try:
            channel = message["channel"]
            data = message["data"]

            # Decode if bytes
            if isinstance(channel, bytes):
                channel = channel.decode("utf-8")
            if isinstance(data, bytes):
                data = data.decode("utf-8")

            # Parse channel to extract request_id: design:{request_id}:events
            parts = channel.split(":")
            if len(parts) != 3 or parts[0] != "design" or parts[2] != "events":
                logger.warning(f"Invalid channel format: {channel}")
                return

            request_id = parts[1]

            # Parse event data (should be JSON)
            try:
                event_data = json.loads(data)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in Pub/Sub message: {data}")
                return

            # Forward to WebSocket if manager available
            if self.websocket_manager:
                await self._forward_to_websocket(request_id, event_data)
            else:
                logger.debug(f"No WebSocket manager, skipping forward: {request_id}")

        except Exception as e:
            logger.error(f"Error handling Pub/Sub message: {e}")

    async def _forward_to_websocket(
        self, request_id: str, event_data: Dict[str, Any]
    ) -> None:
        """
        Forward event to WebSocket clients.

        Converts audit event format to WebSocket message format.

        Args:
            request_id: Design request ID
            event_data: Event data from audit logger
        """
        try:
            # Map audit event types to WebSocket message types
            event_type = event_data.get("event_type", "unknown")
            status_map = {
                "prompt_received": "status",
                "plan_generated": "status",
                "script_generated": "status",
                "execution_completed": "status",
                "validation_passed": "validation",
                "validation_failed": "validation",
                "refinement_started": "status",
                "pipeline_completed": "completed",
                "pipeline_failed": "error",
                "node_started": "progress",
                "node_completed": "progress",
                "node_failed": "error",
            }

            message_type = status_map.get(event_type, "status")

            # Build WebSocket message matching format from api/routes/ws.py
            ws_message = {
                "type": message_type,
                "request_id": request_id,
                "timestamp": event_data.get("timestamp"),
                "data": {
                    "event_type": event_type,
                    "message": event_data.get("message"),
                    "agent": event_data.get("agent"),
                    "node": event_data.get("node"),
                    "status": event_data.get("status"),
                    "metadata": event_data.get("metadata", {}),
                    "error": event_data.get("error"),
                },
            }

            # Send to all WebSocket clients subscribed to this request_id
            await self.websocket_manager.send_update(request_id, ws_message)

            logger.debug(
                f"Forwarded {event_type} to WebSocket clients for {request_id}"
            )

        except Exception as e:
            logger.error(f"Error forwarding to WebSocket: {e}")

    async def stop_listener(self) -> None:
        """Stop the Pub/Sub listener."""
        self.running = False

        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

        if self.pubsub:
            try:
                self.pubsub.close()
            except Exception as e:
                logger.error(f"Error closing PubSub: {e}")

        logger.info("Stopped Redis Pub/Sub listener")

    def subscribe_to_design(self, request_id: UUID) -> None:
        """
        Subscribe to events for a specific design request.

        Args:
            request_id: Design request ID to subscribe to
        """
        if not self.pubsub:
            logger.warning("PubSub not initialized, cannot subscribe")
            return

        try:
            channel = f"design:{request_id}:events"
            self.pubsub.subscribe(channel)
            logger.info(f"Subscribed to {channel}")
        except Exception as e:
            logger.error(f"Failed to subscribe to design channel: {e}")

    def unsubscribe_from_design(self, request_id: UUID) -> None:
        """
        Unsubscribe from events for a specific design request.

        Args:
            request_id: Design request ID to unsubscribe from
        """
        if not self.pubsub:
            return

        try:
            channel = f"design:{request_id}:events"
            self.pubsub.unsubscribe(channel)
            logger.info(f"Unsubscribed from {channel}")
        except Exception as e:
            logger.error(f"Failed to unsubscribe from design channel: {e}")


# Global PubSubBridge instance (initialized in FastAPI lifespan)
_bridge_instance: Optional[PubSubBridge] = None


def get_pubsub_bridge() -> Optional[PubSubBridge]:
    """Get the global PubSubBridge instance."""
    return _bridge_instance


def set_pubsub_bridge(bridge: PubSubBridge) -> None:
    """Set the global PubSubBridge instance."""
    global _bridge_instance
    _bridge_instance = bridge
