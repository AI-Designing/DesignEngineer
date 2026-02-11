"""
WebSocket callback integration for pipeline progress updates.

Provides real-time progress updates to connected clients as the pipeline
executes through different nodes.
"""

from typing import Any, Dict, Optional
from uuid import UUID

import structlog

logger = structlog.get_logger(__name__)


class PipelineWebSocketCallback:
    """
    WebSocket callback handler for pipeline progress updates.
    
    Sends structured messages to WebSocket connections as the pipeline
    progresses through nodes.
    """
    
    def __init__(self, websocket_manager: Any):
        """
        Initialize callback with WebSocket manager.
        
        Args:
            websocket_manager: WebSocket connection manager instance
        """
        self.websocket_manager = websocket_manager
    
    async def __call__(
        self,
        request_id: UUID,
        event: Dict[str, Any],
    ) -> None:
        """
        Send progress update via WebSocket.
        
        Args:
            request_id: Design request ID
            event: Event data to send
        """
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
            # Don't fail pipeline if WebSocket send fails
            logger.warning(
                "Failed to send WebSocket update",
                request_id=str(request_id),
                error=str(e),
            )


async def create_progress_callback(
    websocket_manager: Optional[Any],
) -> Optional[PipelineWebSocketCallback]:
    """
    Create a WebSocket callback if manager is available.
    
    Args:
        websocket_manager: Optional WebSocket manager
        
    Returns:
        Callback instance or None
    """
    if websocket_manager:
        return PipelineWebSocketCallback(websocket_manager)
    return None


def format_node_start_event(node_name: str, iteration: int) -> Dict[str, Any]:
    """
    Format event for node start.
    
    Args:
        node_name: Name of the node
        iteration: Current iteration number
        
    Returns:
        Event dictionary
    """
    return {
        "node": node_name,
        "status": "started",
        "iteration": iteration,
    }


def format_node_complete_event(
    node_name: str,
    iteration: int,
    **metadata: Any,
) -> Dict[str, Any]:
    """
    Format event for node completion.
    
    Args:
        node_name: Name of the node
        iteration: Current iteration number
        **metadata: Additional metadata
        
    Returns:
        Event dictionary
    """
    return {
        "node": node_name,
        "status": "completed",
        "iteration": iteration,
        **metadata,
    }


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
    decision: str,
    reason: str,
    iteration: int,
) -> Dict[str, Any]:
    """
    Format event for routing decision.
    
    Args:
        decision: Routing decision (success/refine/replan/fail)
        reason: Reason for decision
        iteration: Current iteration number
        
    Returns:
        Event dictionary
    """
    return {
        "node": "router",
        "status": "routing",
        "decision": decision,
        "reason": reason,
        "iteration": iteration,
    }
