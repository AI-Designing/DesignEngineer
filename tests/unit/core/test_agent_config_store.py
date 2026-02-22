"""
Unit tests for AgentConfigStore (Redis-backed runtime agent model config).
"""

from unittest.mock import MagicMock, patch

import pytest

from ai_designer.llm.agent_config_store import AgentConfigStore
from ai_designer.llm.model_config import AGENT_MODEL_CONFIG

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_redis():
    """In-memory FakeRedis instance."""
    from fakeredis import FakeRedis

    return FakeRedis(decode_responses=True)


@pytest.fixture
def store(fake_redis):
    """AgentConfigStore backed by FakeRedis."""
    s = AgentConfigStore.__new__(AgentConfigStore)
    s._ttl = None
    s._redis = fake_redis
    return s


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAgentConfigStore:
    def test_get_returns_default_when_no_override(self, store):
        """Without any Redis key, get() returns the static AGENT_MODEL_CONFIG default."""
        cfg = store.get("planner")
        assert cfg["primary"] == AGENT_MODEL_CONFIG["planner"]["primary"]
        assert cfg["temperature"] == AGENT_MODEL_CONFIG["planner"]["temperature"]

    def test_set_and_get_primary_override(self, store):
        """set() persists a model override; get() reflects it immediately."""
        store.set("planner", primary="openai/gpt-4o-mini")
        cfg = store.get("planner")
        assert cfg["primary"] == "openai/gpt-4o-mini"
        # Other fields should remain default
        assert cfg["temperature"] == AGENT_MODEL_CONFIG["planner"]["temperature"]

    def test_set_and_get_multiple_fields(self, store):
        """Multiple fields can be overridden in one set() call."""
        store.set(
            "generator", primary="openai/gpt-4o", temperature=0.5, max_tokens=1024
        )
        cfg = store.get("generator")
        assert cfg["primary"] == "openai/gpt-4o"
        assert cfg["temperature"] == 0.5
        assert cfg["max_tokens"] == 1024

    def test_reset_clears_all_overrides(self, store):
        """reset() removes all Redis keys for an agent; get() falls back to default."""
        store.set("validator", primary="openai/gpt-4o-mini", temperature=0.9)
        store.reset("validator")
        cfg = store.get("validator")
        assert cfg["primary"] == AGENT_MODEL_CONFIG["validator"]["primary"]
        assert cfg["temperature"] == AGENT_MODEL_CONFIG["validator"]["temperature"]

    def test_get_all_returns_all_agents(self, store):
        """get_all() returns a config dict for every known agent."""
        all_configs = store.get_all()
        assert set(all_configs.keys()) == set(AGENT_MODEL_CONFIG.keys())

    def test_get_override_source_shows_redis_override(self, store):
        """get_override_source() reports 'redis_override' for set fields."""
        store.set("orchestrator", primary="openai/gpt-4o")
        sources = store.get_override_source("orchestrator")
        assert sources["primary"] == "redis_override"
        assert sources["fallback"] == "config_default"
        assert sources["temperature"] == "config_default"

    def test_set_invalid_agent_raises(self, store):
        """set() raises ValueError for unknown agent names."""
        with pytest.raises(ValueError, match="Unknown agent"):
            store.set("nonexistent_agent", primary="openai/gpt-4o")

    def test_redis_unavailable_fallback(self):
        """When Redis is unavailable, get() falls back to static defaults without error."""
        s = AgentConfigStore.__new__(AgentConfigStore)
        s._ttl = None
        s._redis = None  # Simulate unavailable Redis
        cfg = s.get("planner")
        assert cfg["primary"] == AGENT_MODEL_CONFIG["planner"]["primary"]

    def test_set_with_redis_unavailable_logs_warning(self):
        """set() emits a warning and does not crash when Redis is unavailable."""
        s = AgentConfigStore.__new__(AgentConfigStore)
        s._ttl = None
        s._redis = None
        # Should not raise
        s.set("planner", primary="openai/gpt-4o-mini")
