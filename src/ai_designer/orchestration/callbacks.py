"""
WebSocket callback integration for pipeline progress updates with audit trail logging.

Provides real-time progress updates to connected clients and logs all events
to Redis Streams for immutable audit trail.
"""

from typing import Any, Dict, Optional
from uuid import UUID

import structlog

from ..redis_utils.audit import AuditEventType, AuditLogger

logger = structlog.get_logger(__name__)


class PipelineWebSocketCallback:
    """
    Callback handler for pipeline progress updates with audit logging.

    Sends structured messages to WebSocket connections and logs events
    to Redis Streams as the pipeline progresses.
    """

    def __init__(
        self,
        websocket_manager: Any,
        audit_logger: Optional[AuditLogger] = None,
    ):
        """
        Initialize callback with WebSocket manager and audit logger.

        Args:
            websocket_manager: WebSocket connection manager instance
            audit_logger: Optional AuditLogger for event persistence
        """
        self.websocket_manager = websocket_manager
        self.audit_logger = audit_logger

    async def on_node_start(
        self,
        request_id: UUID,
        node_name: str,
        iteration: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Called when a pipeline node starts execution.

        Args:
            request_id: Design request ID
            node_name: Name of the node starting
            iteration: Current iteration number
            metadata: Additional node metadata
        """
        try:
            # Log to audit trail
            if self.audit_logger:
                event_type_map = {
                    "planner_node": AuditEventType.PLAN_GENERATED,
                    "generator_node": AuditEventType.SCRIPT_GENERATED,
                    "executor_node": AuditEventType.EXECUTION_STARTED,
                    "validator_node": AuditEventType.VALIDATION_PASSED,
                }
                event_type = event_type_map.get(node_name, AuditEventType.NODE_STARTED)

                self.audit_logger.log_event(
                    event_type=AuditEventType.NODE_STARTED,
                    request_id=request_id,
                    message=f"Started {node_name} (iteration {iteration})",
                    node=node_name,
                    status="running",
                    metadata={
                        "iteration": iteration,
                        **(metadata or {}),
                    },
                )

            # Send WebSocket update
            event = format_node_start_event(node_name, iteration, metadata)
            await self._send_websocket_update(request_id, event)

        except Exception as e:
            logger.warning(
                "Failed to handle node start event",
                request_id=str(request_id),
                node=node_name,
                error=str(e),
            )

    async def on_node_complete(
        self,
        request_id: UUID,
        node_name: str,
        iteration: int,
        output: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None,
    ) -> None:
        """
        Called when a pipeline node completes execution.

        Args:
            request_id: Design request ID
            node_name: Name of the node that completed
            iteration: Current iteration number
            output: Node output data
            duration_ms: Execution duration in milliseconds
        """
        try:
            # Log to audit trail
            if self.audit_logger:
                # Map node completion to appropriate audit event
                event_type_map = {
                    "planner_node": AuditEventType.PLAN_GENERATED,
                    "generator_node": AuditEventType.SCRIPT_GENERATED,
                    "executor_node": AuditEventType.EXECUTION_COMPLETED,
                    "validator_node": AuditEventType.VALIDATION_PASSED,
                }
                event_type = event_type_map.get(node_name, AuditEventType.NODE_COMPLETED)

                # Extract relevant metadata from output
                metadata = {
                    "iteration": iteration,
                    "duration_ms": duration_ms,
                }
                if output:
                    # Include summary of output (avoid logging entire script)
                    if "plan" in output:
                        metadata["plan_summary"] = str(output["plan"])[:200]
                    if "script" in output:
                        metadata["script_length"] = len(output.get("script", ""))
                    if "validation_score" in output:
                        metadata["validation_score"] = output["validation_score"]

                self.audit_logger.log_event(
                    event_type=event_type,
                    request_id=request_id,
                    message=f"Completed {node_name} (iteration {iteration})",
                    node=node_name,
                    status="completed",
                    metadata=metadata,
                )

            # Send WebSocket update
            event = format_node_complete_event(node_name, iteration, output, duration_ms)
            await self._send_websocket_update(request_id, event)

        except Exception as e:
            logger.warning(
                "Failed to handle node complete event",
                request_id=str(request_id),
                node=node_name,
                error=str(e),
            )

    async def on_node_error(
        self,
        request_id: UUID,
        node_name: str,
        iteration: int,
        error: str,
    ) -> None:
        """
        Called when a pipeline node encounters an error.

        Args:
            request_id: Design request ID
            node_name: Name of the node that failed
            iteration: Current iteration number
            error: Error message
        """
        try:
            # Log to audit trail
            if self.audit_logger:
                event_type_map = {
                    "planner_node": AuditEventType.PLAN_FAILED,
                    "generator_node": AuditEventType.SCRIPT_GENERATION_FAILED,
                    "executor_node": AuditEventType.EXECUTION_FAILED,
                    "validator_node": AuditEventType.VALIDATION_FAILED,
                }
                event_type = event_type_map.get(node_name, AuditEventType.NODE_FAILED)

                self.audit_logger.log_event(
                    event_type=event_type,
                    request_id=request_id,
                    message=f"Failed {node_name} (iteration {iteration}): {error}",
                    node=node_name,
                    status="failed",
                    error=error,
                    metadata={"iteration": iteration},
                )

            # Send WebSocket update
            event = format_node_error_event(node_name, iteration, error)
            await self._send_websocket_update(request_id, event)

        except Exception as e:
            logger.warning(
                "Failed to handle node error event",
                request_id=str(request_id),
                node=node_name,
                error=str(e),
            )

    async def on_routing_decision(
        self,
        request_id: UUID,
        from_node: str,
        to_node: str,
        reason: str,
        score: Optional[float] = None,
    ) -> None:
        """
        Called when pipeline makes a routing decision.

        Args:
            request_id: Design request ID
            from_node: Node transitioning from
            to_node: Node transitioning to
            reason: Reason for routing decision
            score: Validation score if applicable
        """
        try:
            # Log routing decision
            if self.audit_logger:
                metadata = {"from": from_node, "to": to_node, "reason": reason}
                if score is not None:
                    metadata["score"] = score

                # Determine event type based on routing
                if to_node == "refine":
                    event_type = AuditEventType.REFINEMENT_STARTED
                elif to_node == "__end__":
                    event_type = AuditEventType.PIPELINE_COMPLETED
                else:
                    event_type = AuditEventType.STATUS_CHANGED

                self.audit_logger.log_event(
                    event_type=event_type,
                    request_id=request_id,
                    message=f"Routing from {from_node} to {to_node}: {reason}",
                    node=from_node,
                    metadata=metadata,
                )

            # Send WebSocket update
            event = format_routing_event(from_node, to_node, reason, score)
            await self._send_websocket_update(request_id, event)

        except Exception as e:
            logger.warning(
                "Failed to handle routing event",
                request_id=str(request_id),
                error=str(e),
            )

    async def _send_websocket_update(
        self, request_id: UUID, event: Dict[str, Any]
    ) -> None:
        """Send event via WebSocket."""
        try:
            message = {
                "type": "pipeline_progress",
                "request_id": str(request_id),
                "event": event,
            }

            await self.websocket_manager.broadcast(str(request_id), message)

            logger.debug(
                "Sent pipeline progress update",
                request_id=str(request_id),
                node=event.get("node"),
                status=event.get("status"),
            )

        except Exception as e:
            logger.warning(
                "Failed to send WebSocket update",
                request_id=str(request_id),
                error=str(e),
            )


async def create_progress_callback(
    websocket_manager: Optional[Any],
    audit_logger: Optional[AuditLogger] = None,
) -> Optional[PipelineWebSocketCallback]:
    """
    Create a WebSocket callback with audit logging.

    Args:
        websocket_manager: Optional WebSocket manager
        audit_logger: Optional AuditLogger for event persistence

    Returns:
        Callback instance or None
    """
    if websocket_manager:
        return PipelineWebSocketCallback(websocket_manager, audit_logger)
    return None


def format_node_start_event(
    node_name: str,
    iteration: int,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Format event for node start.

    Args:
        node_name: Name of the node
        iteration: Current iteration number
        metadata: Additional metadata

    Returns:
        Event dictionary
    """
    event = {
        "node": node_name,
        "status": "started",
        "iteration": iteration,
    }
    if metadata:
        event.update(metadata)
    return event


def format_node_complete_event(
    node_name: str,
    iteration: int,
    output: Optional[Dict[str, Any]] = None,
    duration_ms: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Format event for node completion.

    Args:
        node_name: Name of the node
        iteration: Current iteration number
        output: Node output data
        duration_ms: Execution duration in milliseconds

    Returns:
        Event dictionary
    """
    event = {
        "node": node_name,
        "status": "completed",
        "iteration": iteration,
    }
    if duration_ms is not None:
        event["duration_ms"] = duration_ms
    if output:
        # Include summary, not full output
        event["output_summary"] = {k: str(v)[:100] for k, v in output.items()}
    return event


def format_node_error_event(
    node_name: str,
    iteration: int,
    error: str,
) -> Dict[str, Any]:
    """
    Format event for node error.

    Args:
        node_name: Name of the node
        iteration: Current iteration number
        error: Error message

    Returns:
        Event dictionary
    """
    return {
        "node": node_name,
        "status": "error",
        "iteration": iteration,
        "error": error,
    }


def format_routing_event(
    from_node: str,
    to_node: str,
    reason: str,
    score: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Format event for routing decision.

    Args:
        from_node: Node transitioning from
        to_node: Node transitioning to
        reason: Reason for routing decision
        score: Validation score if applicable

    Returns:
        Event dictionary
    """
    event = {
        "node": "router",
        "status": "routing",
        "from_node": from_node,
        "to_node": to_node,
        "reason": reason,
    }
    if score is not None:
        event["score"] = score
    return event

