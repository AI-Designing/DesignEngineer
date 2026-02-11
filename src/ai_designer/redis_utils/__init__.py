"""
Redis utilities for state management, caching, and audit trail.

Provides:
- RedisClient: Connection pooling and Redis operations
- StateCache: Legacy FreeCAD state + DesignState Pydantic persistence
- AuditLogger: Immutable audit trail via Redis Streams
- PubSubBridge: Redis Pub/Sub to WebSocket forwarding
"""

from .audit import AuditEvent, AuditEventType, AuditLogger
from .client import RedisClient
from .pubsub_bridge import PubSubBridge, get_pubsub_bridge, set_pubsub_bridge
from .state_cache import StateCache

__all__ = [
    "RedisClient",
    "StateCache",
    "AuditLogger",
    "AuditEvent",
    "AuditEventType",
    "PubSubBridge",
    "get_pubsub_bridge",
    "set_pubsub_bridge",
]

