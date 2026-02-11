"""
Redis Streams-based immutable audit trail for design workflows.

Provides comprehensive event logging for all design lifecycle events with:
- Immutable append-only audit trail via Redis Streams
- Event filtering and querying
- Automatic stream trimming to prevent unbounded growth
- Dual-write to Pub/Sub for real-time notifications
"""

import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """Types of audit events in the design lifecycle."""

    # Initial request
    PROMPT_RECEIVED = "prompt_received"

    # Planning phase
    PLAN_GENERATED = "plan_generated"
    PLAN_FAILED = "plan_failed"

    # Generation phase
    SCRIPT_GENERATED = "script_generated"
    SCRIPT_GENERATION_FAILED = "script_generation_failed"

    # Execution phase
    EXECUTION_STARTED = "execution_started"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"

    # Validation phase
    VALIDATION_PASSED = "validation_passed"
    VALIDATION_FAILED = "validation_failed"

    # Refinement
    REFINEMENT_STARTED = "refinement_started"
    REFINEMENT_COMPLETED = "refinement_completed"

    # Export
    DESIGN_EXPORTED = "design_exported"

    # Pipeline events
    PIPELINE_STARTED = "pipeline_started"
    PIPELINE_COMPLETED = "pipeline_completed"
    PIPELINE_FAILED = "pipeline_failed"

    # Node transitions (LangGraph)
    NODE_STARTED = "node_started"
    NODE_COMPLETED = "node_completed"
    NODE_FAILED = "node_failed"

    # State changes
    STATUS_CHANGED = "status_changed"


class AuditEvent(BaseModel):
    """Immutable audit event record."""

    event_id: Optional[str] = Field(
        default=None, description="Redis Stream entry ID (set by Redis)"
    )
    event_type: AuditEventType = Field(..., description="Type of audit event")
    request_id: UUID = Field(..., description="Design request ID")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Event timestamp"
    )
    agent: Optional[str] = Field(
        default=None, description="Agent that triggered the event (planner/generator/etc)"
    )
    node: Optional[str] = Field(
        default=None, description="LangGraph node name (if applicable)"
    )
    status: Optional[str] = Field(
        default=None, description="Execution status at time of event"
    )
    message: str = Field(..., description="Human-readable event description")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional event-specific data"
    )
    error: Optional[str] = Field(
        default=None, description="Error message if event indicates failure"
    )

    def to_stream_fields(self) -> Dict[str, str]:
        """Convert to Redis Stream field-value pairs (all strings)."""
        return {
            "event_type": self.event_type.value,
            "request_id": str(self.request_id),
            "timestamp": self.timestamp.isoformat(),
            "agent": self.agent or "",
            "node": self.node or "",
            "status": self.status or "",
            "message": self.message,
            "metadata": json.dumps(self.metadata),
            "error": self.error or "",
        }

    @classmethod
    def from_stream_entry(
        cls, entry_id: str, fields: Dict[bytes, bytes]
    ) -> "AuditEvent":
        """Parse Redis Stream entry into AuditEvent."""
        decoded = {
            k.decode("utf-8"): v.decode("utf-8") for k, v in fields.items()
        }

        return cls(
            event_id=entry_id,
            event_type=AuditEventType(decoded["event_type"]),
            request_id=UUID(decoded["request_id"]),
            timestamp=datetime.fromisoformat(decoded["timestamp"]),
            agent=decoded.get("agent") or None,
            node=decoded.get("node") or None,
            status=decoded.get("status") or None,
            message=decoded["message"],
            metadata=json.loads(decoded.get("metadata", "{}")),
            error=decoded.get("error") or None,
        )


class AuditLogger:
    """
    Immutable audit trail logger using Redis Streams.

    Features:
    - Append-only audit log (cannot modify history)
    - Automatic stream trimming to prevent unbounded growth
    - Dual-write to Pub/Sub for real-time notifications
    - Efficient querying and filtering
    """

    def __init__(
        self,
        redis_client,
        stream_max_length: int = 1000,
        enable_pubsub: bool = True,
    ):
        """
        Initialize audit logger.

        Args:
            redis_client: RedisClient instance
            stream_max_length: Maximum events per stream (default 1000)
            enable_pubsub: Also publish events to Pub/Sub for real-time notifications
        """
        self.redis_client = redis_client
        self.stream_max_length = stream_max_length
        self.enable_pubsub = enable_pubsub

    def _get_stream_key(self, request_id: UUID) -> str:
        """Get Redis Stream key for a design request."""
        return f"design:{request_id}:audit"

    def _get_pubsub_channel(self, request_id: UUID) -> str:
        """Get Pub/Sub channel for real-time notifications."""
        return f"design:{request_id}:events"

    def log_event(
        self,
        event_type: AuditEventType,
        request_id: UUID,
        message: str,
        agent: Optional[str] = None,
        node: Optional[str] = None,
        status: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> str:
        """
        Log an audit event to Redis Stream.

        Args:
            event_type: Type of event
            request_id: Design request ID
            message: Human-readable description
            agent: Agent name (planner, generator, validator, etc.)
            node: LangGraph node name
            status: Current execution status
            metadata: Additional event data
            error: Error message if applicable

        Returns:
            Redis Stream entry ID
        """
        event = AuditEvent(
            event_type=event_type,
            request_id=request_id,
            message=message,
            agent=agent,
            node=node,
            status=status,
            metadata=metadata or {},
            error=error,
        )

        stream_key = self._get_stream_key(request_id)

        try:
            # Write to Redis Stream with automatic trimming
            entry_id = self.redis_client.xadd(
                stream_key,
                event.to_stream_fields(),
                maxlen=self.stream_max_length,
                approximate=True,  # ~maxlen for better performance
            )

            event.event_id = entry_id.decode("utf-8") if isinstance(entry_id, bytes) else entry_id

            # Dual-write to Pub/Sub for real-time notifications
            if self.enable_pubsub:
                try:
                    channel = self._get_pubsub_channel(request_id)
                    payload = json.dumps(
                        {
                            "event_type": event_type.value,
                            "request_id": str(request_id),
                            "timestamp": event.timestamp.isoformat(),
                            "message": message,
                            "agent": agent,
                            "node": node,
                            "status": status,
                            "metadata": metadata or {},
                            "error": error,
                        }
                    )
                    self.redis_client.publish(channel, payload)
                except Exception as e:
                    logger.warning(f"Failed to publish event to Pub/Sub: {e}")

            logger.debug(
                f"Logged {event_type.value} for {request_id}: {message}"
            )
            return event.event_id

        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
            raise

    def get_history(
        self,
        request_id: UUID,
        start: str = "-",
        end: str = "+",
        count: Optional[int] = None,
    ) -> List[AuditEvent]:
        """
        Retrieve audit history for a design request.

        Args:
            request_id: Design request ID
            start: Start entry ID ('-' for beginning)
            end: End entry ID ('+' for end)
            count: Maximum number of events to retrieve

        Returns:
            List of AuditEvent objects in chronological order
        """
        stream_key = self._get_stream_key(request_id)

        try:
            entries = self.redis_client.xrange(stream_key, start, end, count)
            return [
                AuditEvent.from_stream_entry(
                    entry_id.decode("utf-8") if isinstance(entry_id, bytes) else entry_id,
                    fields,
                )
                for entry_id, fields in entries
            ]
        except Exception as e:
            logger.error(f"Failed to retrieve audit history: {e}")
            return []

    def get_recent_events(
        self, request_id: UUID, limit: int = 10
    ) -> List[AuditEvent]:
        """
        Get the most recent audit events.

        Args:
            request_id: Design request ID
            limit: Number of events to retrieve

        Returns:
            List of recent AuditEvent objects (newest first)
        """
        stream_key = self._get_stream_key(request_id)

        try:
            # Use XREVRANGE to get events in reverse chronological order
            entries = self.redis_client.xrevrange(
                stream_key, start="+", end="-", count=limit
            )
            return [
                AuditEvent.from_stream_entry(
                    entry_id.decode("utf-8") if isinstance(entry_id, bytes) else entry_id,
                    fields,
                )
                for entry_id, fields in entries
            ]
        except Exception as e:
            logger.error(f"Failed to retrieve recent events: {e}")
            return []

    def get_events_by_type(
        self, request_id: UUID, event_type: AuditEventType
    ) -> List[AuditEvent]:
        """
        Filter audit events by type.

        Args:
            request_id: Design request ID
            event_type: Type of events to retrieve

        Returns:
            List of matching AuditEvent objects
        """
        all_events = self.get_history(request_id)
        return [e for e in all_events if e.event_type == event_type]

    def get_event_count(self, request_id: UUID) -> int:
        """
        Get total number of events in audit trail.

        Args:
            request_id: Design request ID

        Returns:
            Number of events
        """
        stream_key = self._get_stream_key(request_id)
        try:
            return self.redis_client.xlen(stream_key)
        except Exception as e:
            logger.error(f"Failed to get event count: {e}")
            return 0

    def get_timeline_summary(self, request_id: UUID) -> Dict[str, Any]:
        """
        Get a summary of the design timeline.

        Args:
            request_id: Design request ID

        Returns:
            Dictionary with event counts, timeline, and key milestones
        """
        events = self.get_history(request_id)

        if not events:
            return {"request_id": str(request_id), "total_events": 0, "events": []}

        event_counts = {}
        for event in events:
            event_counts[event.event_type.value] = (
                event_counts.get(event.event_type.value, 0) + 1
            )

        return {
            "request_id": str(request_id),
            "total_events": len(events),
            "event_counts": event_counts,
            "first_event": events[0].timestamp.isoformat() if events else None,
            "last_event": events[-1].timestamp.isoformat() if events else None,
            "timeline": [
                {
                    "event_type": e.event_type.value,
                    "timestamp": e.timestamp.isoformat(),
                    "message": e.message,
                    "agent": e.agent,
                    "node": e.node,
                }
                for e in events
            ],
        }
