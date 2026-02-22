"""
Tests for /admin/agents/config API endpoints.
"""

from unittest.mock import patch

import pytest
from fakeredis import FakeRedis
from fastapi.testclient import TestClient

from ai_designer.api.app import create_app
from ai_designer.llm.agent_config_store import AgentConfigStore
from ai_designer.llm.model_config import AGENT_MODEL_CONFIG

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def fake_redis_store():
    """A shared AgentConfigStore backed by FakeRedis for the test module."""
    store = AgentConfigStore.__new__(AgentConfigStore)
    store._ttl = None
    store._redis = FakeRedis(decode_responses=True)
    return store


@pytest.fixture(autouse=True)
def patch_store(fake_redis_store):
    """Patch get_agent_config_store to return the FakeRedis-backed store."""
    with patch(
        "ai_designer.api.routes.agent_config.get_agent_config_store",
        return_value=fake_redis_store,
    ):
        # Also reset all agent overrides before each test
        for agent in AGENT_MODEL_CONFIG:
            fake_redis_store.reset(agent)
        yield


@pytest.fixture(scope="module")
def client():
    """FastAPI TestClient for the full app with auth disabled."""
    import os

    os.environ.setdefault("OPPER_API_KEY", "test-key")  # pragma: allowlist secret
    app = create_app()
    with patch("ai_designer.api.middleware.auth._DISABLED", True):
        with TestClient(app) as c:
            yield c


# ---------------------------------------------------------------------------
# GET /admin/agents/config
# ---------------------------------------------------------------------------


class TestListAgentConfigs:
    def test_returns_200_with_all_agents(self, client):
        resp = client.get("/api/v1/admin/agents/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "agents" in data
        for name in AGENT_MODEL_CONFIG:
            assert name in data["agents"]

    def test_sources_all_config_default_initially(self, client):
        resp = client.get("/api/v1/admin/agents/config")
        data = resp.json()
        for agent_data in data["agents"].values():
            for source in agent_data["sources"].values():
                assert source == "config_default"


# ---------------------------------------------------------------------------
# GET /admin/agents/config/{agent_name}
# ---------------------------------------------------------------------------


class TestGetAgentConfig:
    def test_returns_planner_config(self, client):
        resp = client.get("/api/v1/admin/agents/config/planner")
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent"] == "planner"
        assert "primary" in data["config"]

    def test_returns_404_for_unknown_agent(self, client):
        resp = client.get("/api/v1/admin/agents/config/unknown_agent")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /admin/agents/config/{agent_name}
# ---------------------------------------------------------------------------


class TestUpdateAgentConfig:
    def test_update_primary_model(self, client):
        payload = {"primary": "openai/gpt-4o-mini"}
        resp = client.post("/api/v1/admin/agents/config/planner", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["config"]["primary"] == "openai/gpt-4o-mini"
        assert data["sources"]["primary"] == "redis_override"

    def test_update_temperature(self, client):
        payload = {"temperature": 0.1}
        resp = client.post("/api/v1/admin/agents/config/generator", json=payload)
        assert resp.status_code == 200
        assert resp.json()["config"]["temperature"] == 0.1

    def test_update_multiple_fields(self, client):
        payload = {
            "primary": "anthropic/claude-3-5-sonnet-20241022",
            "max_tokens": 1024,
        }
        resp = client.post("/api/v1/admin/agents/config/validator", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["config"]["primary"] == "anthropic/claude-3-5-sonnet-20241022"
        assert data["config"]["max_tokens"] == 1024

    def test_returns_404_for_unknown_agent(self, client):
        resp = client.post(
            "/api/v1/admin/agents/config/ghost", json={"primary": "openai/gpt-4o"}
        )
        assert resp.status_code == 404

    def test_empty_body_returns_422(self, client):
        resp = client.post("/api/v1/admin/agents/config/planner", json={})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /admin/agents/config/{agent_name}
# ---------------------------------------------------------------------------


class TestResetAgentConfig:
    def test_reset_after_override(self, client):
        # First set an override
        client.post(
            "/api/v1/admin/agents/config/orchestrator",
            json={"primary": "openai/gpt-4o-mini"},
        )
        # Then reset
        resp = client.delete("/api/v1/admin/agents/config/orchestrator")
        assert resp.status_code == 200
        data = resp.json()
        # Sources should all be config_default after reset
        assert all(s == "config_default" for s in data["sources"].values())

    def test_returns_404_for_unknown_agent(self, client):
        resp = client.delete("/api/v1/admin/agents/config/ghost")
        assert resp.status_code == 404
