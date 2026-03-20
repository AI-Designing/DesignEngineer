"""
Admin API routes for runtime agent model configuration.

These endpoints allow hot-swapping the LLM model assigned to any agent
(planner, generator, validator, orchestrator) without a server restart.
Changes are persisted in Redis and take effect immediately on the next
LLM call.

Endpoints
---------
GET  /admin/agents/config
    Returns the effective config for all agents plus the source of each
    field (``"redis_override"`` vs ``"config_default"``).

GET  /admin/agents/config/{agent_name}
    Returns the effective config for a single agent.

POST /admin/agents/config/{agent_name}
    Overrides one or more config fields for an agent.
    Body: ``AgentConfigUpdate``

DELETE /admin/agents/config/{agent_name}
    Resets an agent to its config.yaml / env-var default.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ai_designer.llm.agent_config_store import get_agent_config_store
from ai_designer.llm.model_config import AGENT_MODEL_CONFIG

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class AgentConfigUpdate(BaseModel):
    """Payload for updating an agent's model configuration."""

    primary: Optional[str] = Field(
        default=None,
        description=(
            "New primary Opper model string. "
            "Format: 'provider/model-name', e.g. 'openai/gpt-4o-mini' or "
            "'anthropic/claude-3-5-sonnet-20241022'. "
            "See https://docs.opper.ai/capabilities/models for all options."
        ),
        examples=["openai/gpt-4o-mini", "anthropic/claude-3-5-sonnet-20241022"],
    )
    fallback: Optional[str] = Field(
        default=None,
        description=(
            "New fallback Opper model string used when the primary fails. "
            "Leave null to keep the current fallback."
        ),
        examples=["gcp/gemini-2.0-flash"],
    )
    temperature: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Sampling temperature override (0.0 – 2.0).",
    )
    max_tokens: Optional[int] = Field(
        default=None,
        gt=0,
        description="Maximum tokens to generate.",
    )


class AgentConfigResponse(BaseModel):
    """Effective model config for one agent."""

    agent: str
    config: Dict[str, Any]
    sources: Dict[str, str] = Field(
        description=(
            "Per-field source: 'redis_override' (set via API) "
            "or 'config_default' (from config.yaml / env var)."
        )
    )


class AllAgentsConfigResponse(BaseModel):
    """Effective model configs for all agents."""

    agents: Dict[str, AgentConfigResponse]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

VALID_AGENTS = list(AGENT_MODEL_CONFIG.keys())


def _resolved_response(agent_name: str) -> AgentConfigResponse:
    store = get_agent_config_store()
    return AgentConfigResponse(
        agent=agent_name,
        config=store.get(agent_name),
        sources=store.get_override_source(agent_name),
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get(
    "/admin/agents/config",
    response_model=AllAgentsConfigResponse,
    summary="List all agent model configs",
    tags=["Admin"],
)
async def list_agent_configs() -> AllAgentsConfigResponse:
    """
    Return the effective LLM model configuration for every agent.

    Each field shows whether its current value comes from a Redis runtime
    override (set via this API) or from the config.yaml / env-var default.
    """
    agents: Dict[str, AgentConfigResponse] = {}
    for name in VALID_AGENTS:
        agents[name] = _resolved_response(name)
    return AllAgentsConfigResponse(agents=agents)


@router.get(
    "/admin/agents/config/{agent_name}",
    response_model=AgentConfigResponse,
    summary="Get model config for one agent",
    tags=["Admin"],
)
async def get_agent_config_endpoint(agent_name: str) -> AgentConfigResponse:
    """
    Return the effective LLM model configuration for **agent_name**.

    Valid agent names: ``planner``, ``generator``, ``validator``, ``orchestrator``.
    """
    if agent_name not in VALID_AGENTS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown agent '{agent_name}'. Valid agents: {VALID_AGENTS}",
        )
    return _resolved_response(agent_name)


@router.post(
    "/admin/agents/config/{agent_name}",
    response_model=AgentConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Override model config for one agent",
    tags=["Admin"],
)
async def update_agent_config(
    agent_name: str,
    payload: AgentConfigUpdate,
) -> AgentConfigResponse:
    """
    Override one or more fields of the LLM model config for **agent_name**.

    The change is persisted in Redis and takes effect **immediately** on the
    next LLM call — no restart required.

    Only the fields included in the request body are updated; omitted fields
    retain their current values.

    **Example — switch the planner to a cheaper model:**
    ```json
    POST /admin/agents/config/planner
    {
      "primary": "openai/gpt-4o-mini",
      "temperature": 0.2
    }
    ```
    """
    if agent_name not in VALID_AGENTS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown agent '{agent_name}'. Valid agents: {VALID_AGENTS}",
        )

    if payload.model_fields_set == set():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Request body must contain at least one field to update.",
        )

    store = get_agent_config_store()
    try:
        store.set(
            agent_name,
            primary=payload.primary,
            fallback=payload.fallback,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    logger.info(
        "Agent config updated via API: agent=%s fields=%s",
        agent_name,
        payload.model_fields_set,
    )
    return _resolved_response(agent_name)


@router.delete(
    "/admin/agents/config/{agent_name}",
    response_model=AgentConfigResponse,
    summary="Reset agent config to default",
    tags=["Admin"],
)
async def reset_agent_config(agent_name: str) -> AgentConfigResponse:
    """
    Remove all Redis overrides for **agent_name**, reverting to the
    ``config.yaml`` / env-var default.

    The change takes effect immediately on the next LLM call.
    """
    if agent_name not in VALID_AGENTS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown agent '{agent_name}'. Valid agents: {VALID_AGENTS}",
        )

    store = get_agent_config_store()
    store.reset(agent_name)
    logger.info("Agent config reset to default via API: agent=%s", agent_name)
    return _resolved_response(agent_name)
