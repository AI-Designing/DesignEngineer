"""
Integration tests for Redis Streams audit trail and enhanced state management.

Tests:
- AuditLogger event logging and retrieval
- DesignState serialization/deserialization
- TTL management and cleanup
- Pub/Sub bridge to WebSocket
- End-to-end audit trail for pipeline execution
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import UUID, uuid4

import pytest

from ai_designer.redis_utils.audit import AuditEvent, AuditEventType, AuditLogger
from ai_designer.redis_utils.client import RedisClient
from ai_designer.redis_utils.pubsub_bridge import PubSubBridge
from ai_designer.redis_utils.state_cache import StateCache
from ai_designer.schemas.design_state import DesignRequest, DesignState, ExecutionStatus


class MockRedisClient:
    """Mock Redis client for testing."""

    def __init__(self):
        self.store: dict = {}
        self.streams: dict = {}
        self.pubsub_channels: dict = {}
        self.ttls: dict = {}

    def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        self.store[key] = value
        if ex:
            self.ttls[key] = time.time() + ex
        return True

    def get(self, key: str) -> Optional[bytes]:
        if key in self.store:
            # Check TTL
            if key in self.ttls and time.time() > self.ttls[key]:
                del self.store[key]
                del self.ttls[key]
                return None
            return self.store[key].encode("utf-8")
        return None

    def delete(self, key: str) -> int:
        if key in self.store:
            del self.store[key]
            if key in self.ttls:
                del self.ttls[key]
            return 1
        return 0

    def hset(self, name: str, key: str, value: str) -> int:
        if name not in self.store:
            self.store[name] = {}
        self.store[name][key] = value
        return 1

    def hget(self, name: str, key: str) -> Optional[str]:
        if name in self.store and isinstance(self.store[name], dict):
            return self.store[name].get(key)
        return None

    def hgetall(self, name: str) -> dict:
        if name in self.store and isinstance(self.store[name], dict):
            return self.store[name]
        return {}

    def hdel(self, name: str, key: str) -> int:
        if name in self.store and isinstance(self.store[name], dict):
            if key in self.store[name]:
                del self.store[name][key]
                return 1
        return 0

    def xadd(
        self,
        stream: str,
        fields: dict,
        maxlen: Optional[int] = None,
        approximate: bool = True,
    ) -> str:
        if stream not in self.streams:
            self.streams[stream] = []

        # Generate entry ID (timestamp-sequence)
        entry_id = f"{int(time.time() * 1000)}-{len(self.streams[stream])}"

        # Convert all values to bytes for realistic behavior
        entry_fields = {k.encode("utf-8"): v.encode("utf-8") for k, v in fields.items()}

        self.streams[stream].append((entry_id.encode("utf-8"), entry_fields))

        # Trim stream if maxlen specified
        if maxlen and len(self.streams[stream]) > maxlen:
            self.streams[stream] = self.streams[stream][-maxlen:]

        return entry_id.encode("utf-8")

    def xrange(
        self, stream: str, start: str = "-", end: str = "+", count: Optional[int] = None
    ) -> list:
        if stream not in self.streams:
            return []

        entries = self.streams[stream]
        if count:
            entries = entries[:count]

        return entries

    def xrevrange(
        self, stream: str, start: str = "+", end: str = "-", count: Optional[int] = None
    ) -> list:
        if stream not in self.streams:
            return []

        entries = list(reversed(self.streams[stream]))
        if count:
            entries = entries[:count]

        return entries

    def xlen(self, stream: str) -> int:
        return len(self.streams.get(stream, []))

    def publish(self, channel: str, message: str) -> int:
        if channel not in self.pubsub_channels:
            self.pubsub_channels[channel] = []
        self.pubsub_channels[channel].append(message)
        return len(self.pubsub_channels.get(channel, []))

    def subscribe(self, *channels: str):
        # Return mock PubSub object
        mock_pubsub = Mock()
        mock_pubsub.get_message = Mock(return_value=None)
        mock_pubsub.subscribe = Mock()
        mock_pubsub.unsubscribe = Mock()
        mock_pubsub.close = Mock()
        return mock_pubsub

    def expire(self, key: str, seconds: int) -> bool:
        if key in self.store:
            self.ttls[key] = time.time() + seconds
            return True
        return False

    def ttl(self, key: str) -> int:
        if key not in self.store:
            return -2
        if key not in self.ttls:
            return -1
        remaining = int(self.ttls[key] - time.time())
        return max(remaining, 0)


@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    return MockRedisClient()


@pytest.fixture
def audit_logger(mock_redis):
    """Create AuditLogger with mock Redis."""
    return AuditLogger(mock_redis, stream_max_length=100, enable_pubsub=True)


@pytest.fixture
def state_cache(mock_redis):
    """Create StateCache with mock Redis."""
    return StateCache(mock_redis)


@pytest.fixture
def sample_design_request():
    """Create sample DesignRequest."""
    return DesignRequest(
        user_prompt="Create a simple bracket with mounting holes",
        constraints={"max_width": 100, "material": "steel"},
    )


@pytest.fixture
def sample_design_state(sample_design_request):
    """Create sample DesignState."""
    return DesignState(
        request_id=sample_design_request.request_id,
        user_prompt=sample_design_request.user_prompt,
        status=ExecutionStatus.PENDING,
    )


# ============================================================================
# AuditLogger Tests
# ============================================================================


def test_log_event_creates_stream_entry(audit_logger, mock_redis):
    """Test that logging an event creates a stream entry."""
    request_id = uuid4()

    entry_id = audit_logger.log_event(
        event_type=AuditEventType.PROMPT_RECEIVED,
        request_id=request_id,
        message="User submitted design prompt",
        metadata={"prompt_length": 50},
    )

    assert entry_id is not None
    stream_key = f"design:{request_id}:audit"
    assert stream_key in mock_redis.streams
    assert len(mock_redis.streams[stream_key]) == 1


def test_log_event_publishes_to_pubsub(audit_logger, mock_redis):
    """Test that logging an event publishes to Pub/Sub."""
    request_id = uuid4()

    audit_logger.log_event(
        event_type=AuditEventType.PLAN_GENERATED,
        request_id=request_id,
        message="Planner generated task decomposition",
        agent="planner",
    )

    channel = f"design:{request_id}:events"
    assert channel in mock_redis.pubsub_channels
    assert len(mock_redis.pubsub_channels[channel]) == 1

    # Verify message format
    message = json.loads(mock_redis.pubsub_channels[channel][0])
    assert message["event_type"] == "plan_generated"
    assert message["request_id"] == str(request_id)
    assert message["agent"] == "planner"


def test_get_history_retrieves_events(audit_logger):
    """Test retrieving audit history."""
    request_id = uuid4()

    # Log multiple events
    audit_logger.log_event(AuditEventType.PROMPT_RECEIVED, request_id, "Event 1")
    time.sleep(0.01)  # Ensure different timestamps
    audit_logger.log_event(AuditEventType.PLAN_GENERATED, request_id, "Event 2")
    time.sleep(0.01)
    audit_logger.log_event(AuditEventType.SCRIPT_GENERATED, request_id, "Event 3")

    history = audit_logger.get_history(request_id)

    assert len(history) == 3
    assert history[0].event_type == AuditEventType.PROMPT_RECEIVED
    assert history[1].event_type == AuditEventType.PLAN_GENERATED
    assert history[2].event_type == AuditEventType.SCRIPT_GENERATED


def test_get_recent_events_limits_results(audit_logger):
    """Test getting recent events with limit."""
    request_id = uuid4()

    # Log 10 events
    for i in range(10):
        audit_logger.log_event(
            AuditEventType.NODE_STARTED,
            request_id,
            f"Event {i}",
        )
        time.sleep(0.01)

    recent = audit_logger.get_recent_events(request_id, limit=3)

    assert len(recent) == 3
    # Should be in reverse chronological order (newest first)
    assert recent[0].message == "Event 9"
    assert recent[1].message == "Event 8"
    assert recent[2].message == "Event 7"


def test_get_events_by_type_filters_correctly(audit_logger):
    """Test filtering events by type."""
    request_id = uuid4()

    audit_logger.log_event(AuditEventType.PLAN_GENERATED, request_id, "Plan 1")
    audit_logger.log_event(AuditEventType.SCRIPT_GENERATED, request_id, "Script 1")
    audit_logger.log_event(AuditEventType.PLAN_GENERATED, request_id, "Plan 2")

    plan_events = audit_logger.get_events_by_type(
        request_id, AuditEventType.PLAN_GENERATED
    )

    assert len(plan_events) == 2
    assert all(e.event_type == AuditEventType.PLAN_GENERATED for e in plan_events)


def test_stream_trimming_enforces_maxlen(mock_redis):
    """Test that streams are automatically trimmed to maxlen."""
    audit_logger = AuditLogger(mock_redis, stream_max_length=5)
    request_id = uuid4()

    # Log 10 events (should trim to 5)
    for i in range(10):
        audit_logger.log_event(
            AuditEventType.NODE_STARTED,
            request_id,
            f"Event {i}",
        )

    stream_key = f"design:{request_id}:audit"
    assert len(mock_redis.streams[stream_key]) == 5


def test_get_timeline_summary(audit_logger):
    """Test getting timeline summary."""
    request_id = uuid4()

    audit_logger.log_event(AuditEventType.PROMPT_RECEIVED, request_id, "Start")
    audit_logger.log_event(AuditEventType.PLAN_GENERATED, request_id, "Plan")
    audit_logger.log_event(AuditEventType.VALIDATION_PASSED, request_id, "Valid")
    audit_logger.log_event(AuditEventType.VALIDATION_PASSED, request_id, "Valid 2")

    summary = audit_logger.get_timeline_summary(request_id)

    assert summary["total_events"] == 4
    assert summary["event_counts"]["prompt_received"] == 1
    assert summary["event_counts"]["plan_generated"] == 1
    assert summary["event_counts"]["validation_passed"] == 2
    assert len(summary["timeline"]) == 4


# ============================================================================
# StateCache DesignState Tests
# ============================================================================


def test_cache_design_state(state_cache, sample_design_state):
    """Test caching DesignState."""
    success = state_cache.cache_design_state(sample_design_state, ttl_seconds=3600)

    assert success is True

    # Verify stored in Redis
    key = f"design:{sample_design_state.request_id}:state"
    assert key in state_cache.redis_client.store


def test_retrieve_design_state(state_cache, sample_design_state):
    """Test retrieving DesignState."""
    state_cache.cache_design_state(sample_design_state)

    retrieved = state_cache.retrieve_design_state(sample_design_state.request_id)

    assert retrieved is not None
    assert retrieved.request_id == sample_design_state.request_id
    assert retrieved.user_prompt == sample_design_state.user_prompt
    assert retrieved.status == sample_design_state.status


def test_design_state_pydantic_serialization_roundtrip(
    state_cache, sample_design_state
):
    """Test Pydantic serialization/deserialization roundtrip."""
    # Update state with complex data
    sample_design_state.status = ExecutionStatus.GENERATING
    sample_design_state.execution_plan = {"steps": ["step1", "step2"]}
    sample_design_state.freecad_script = "import Part\n..."

    state_cache.cache_design_state(sample_design_state)
    retrieved = state_cache.retrieve_design_state(sample_design_state.request_id)

    assert retrieved.status == ExecutionStatus.GENERATING
    assert retrieved.execution_plan == {"steps": ["step1", "step2"]}
    assert retrieved.freecad_script == "import Part\n..."


def test_update_design_state(state_cache, sample_design_state):
    """Test updating DesignState."""
    state_cache.cache_design_state(sample_design_state)

    # Update state
    sample_design_state.status = ExecutionStatus.COMPLETED
    state_cache.update_design_state(sample_design_state)

    retrieved = state_cache.retrieve_design_state(sample_design_state.request_id)
    assert retrieved.status == ExecutionStatus.COMPLETED


def test_delete_design_state(state_cache, sample_design_state):
    """Test deleting DesignState."""
    state_cache.cache_design_state(sample_design_state)

    success = state_cache.delete_design_state(sample_design_state.request_id)
    assert success is True

    retrieved = state_cache.retrieve_design_state(sample_design_state.request_id)
    assert retrieved is None


def test_list_design_states(state_cache):
    """Test listing design states."""
    # Create multiple states
    state1 = DesignState(
        request_id=uuid4(), user_prompt="Design 1", status=ExecutionStatus.PENDING
    )
    state2 = DesignState(
        request_id=uuid4(), user_prompt="Design 2", status=ExecutionStatus.COMPLETED
    )
    state3 = DesignState(
        request_id=uuid4(), user_prompt="Design 3", status=ExecutionStatus.PENDING
    )

    state_cache.cache_design_state(state1)
    state_cache.cache_design_state(state2)
    state_cache.cache_design_state(state3)

    # List all
    all_ids = state_cache.list_design_states()
    assert len(all_ids) == 3

    # Filter by status
    pending_ids = state_cache.list_design_states(status=ExecutionStatus.PENDING)
    assert len(pending_ids) == 2

    completed_ids = state_cache.list_design_states(status=ExecutionStatus.COMPLETED)
    assert len(completed_ids) == 1


def test_design_state_ttl_management(state_cache, sample_design_state):
    """Test TTL management for DesignState."""
    state_cache.cache_design_state(sample_design_state, ttl_seconds=3600)

    # Check TTL exists
    ttl = state_cache.get_design_ttl(sample_design_state.request_id)
    assert ttl > 0
    assert ttl <= 3600

    # Update TTL
    success = state_cache.set_design_ttl(sample_design_state.request_id, 7200)
    assert success is True

    new_ttl = state_cache.get_design_ttl(sample_design_state.request_id)
    assert new_ttl > 3600


def test_cleanup_completed_designs(state_cache):
    """Test cleanup of old completed designs."""
    # Create old completed design
    old_state = DesignState(
        request_id=uuid4(),
        user_prompt="Old design",
        status=ExecutionStatus.COMPLETED,
    )
    old_state.completed_at = datetime(2026, 1, 1)  # Very old

    # Create recent completed design
    recent_state = DesignState(
        request_id=uuid4(),
        user_prompt="Recent design",
        status=ExecutionStatus.COMPLETED,
    )
    recent_state.completed_at = datetime.utcnow()

    state_cache.cache_design_state(old_state)
    state_cache.cache_design_state(recent_state)

    # Cleanup designs older than 1 hour
    deleted = state_cache.cleanup_completed_designs(older_than_hours=1)

    assert deleted == 1

    # Old design should be deleted
    assert state_cache.retrieve_design_state(old_state.request_id) is None

    # Recent design should still exist
    assert state_cache.retrieve_design_state(recent_state.request_id) is not None


# ============================================================================
# PubSubBridge Tests
# ============================================================================


@pytest.mark.asyncio
async def test_pubsub_bridge_forwards_to_websocket():
    """Test that PubSubBridge forwards events to WebSocket."""
    mock_redis = MockRedisClient()
    mock_ws_manager = AsyncMock()
    mock_ws_manager.send_update = AsyncMock()

    bridge = PubSubBridge(mock_redis, mock_ws_manager)

    # Simulate Pub/Sub message
    request_id = uuid4()
    event_data = {
        "event_type": "plan_generated",
        "request_id": str(request_id),
        "timestamp": datetime.utcnow().isoformat(),
        "message": "Test message",
        "agent": "planner",
    }

    message = {
        "type": "message",
        "channel": f"design:{request_id}:events",
        "data": json.dumps(event_data),
    }

    await bridge._handle_message(message)

    # Verify WebSocket send was called
    mock_ws_manager.send_update.assert_called_once()
    call_args = mock_ws_manager.send_update.call_args
    assert call_args[0][0] == str(request_id)
    assert call_args[0][1]["type"] == "status"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
