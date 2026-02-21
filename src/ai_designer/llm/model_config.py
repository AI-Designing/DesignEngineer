"""
Per-agent LLM model configuration.

Centralises model selection, temperature, and token limits so no agent
hard-codes provider strings.  Runtime overrides are read from environment
variables using the convention:

    AGENT_{AGENT_NAME_UPPER}_{KEY_UPPER}

Example:
    AGENT_PLANNER_PRIMARY="openai/gpt-4o-mini"
    AGENT_GENERATOR_MAX_TOKENS="8192"
"""

import os
from typing import Optional

# ---------------------------------------------------------------------------
# Default configuration per agent role
# ---------------------------------------------------------------------------

AGENT_MODEL_CONFIG: dict = {
    "planner": {
        "primary": "anthropic/claude-3-5-sonnet-20241022",
        "fallback": "google/gemini-pro",
        "temperature": 0.3,
        "max_tokens": 4096,
    },
    "generator": {
        "primary": "google/gemini-2.0-flash",
        "fallback": "openai/gpt-4o",
        "temperature": 0.1,
        "max_tokens": 8192,
    },
    "validator": {
        "primary": "anthropic/claude-3-5-sonnet-20241022",
        "fallback": "openai/gpt-4o",
        "temperature": 0.3,
        "max_tokens": 2048,
    },
    "orchestrator": {
        "primary": "anthropic/claude-3-5-sonnet-20241022",
        "fallback": "google/gemini-pro",
        "temperature": 0.4,
        "max_tokens": 2048,
    },
}


def get_agent_config(agent_name: str) -> dict:
    """Return the model configuration for *agent_name*.

    Checks environment variable overrides before returning defaults.

    Args:
        agent_name: One of ``"planner"``, ``"generator"``, ``"validator"``,
            ``"orchestrator"``.

    Returns:
        A dict with keys ``primary``, ``fallback``, ``temperature``,
        ``max_tokens`` – with any env-var overrides applied.

    Raises:
        KeyError: If *agent_name* is not in :data:`AGENT_MODEL_CONFIG`.
    """
    key = agent_name.lower()
    if key not in AGENT_MODEL_CONFIG:
        raise KeyError(
            f"Unknown agent '{agent_name}'. "
            f"Valid names: {list(AGENT_MODEL_CONFIG.keys())}"
        )

    # Start from a mutable copy of the defaults
    config = dict(AGENT_MODEL_CONFIG[key])

    # Apply env-var overrides
    for field in ("primary", "fallback", "temperature", "max_tokens"):
        override = get_env_override(agent_name, field)
        if override is not None:
            # Cast numeric fields
            if field == "temperature":
                config[field] = float(override)
            elif field == "max_tokens":
                config[field] = int(override)
            else:
                config[field] = override

    return config


def get_env_override(agent_name: str, key: str) -> Optional[str]:
    """Return an env-var override for *agent_name*/*key*, or ``None``.

    Variable name format: ``AGENT_{AGENT_NAME_UPPER}_{KEY_UPPER}``

    Example::

        os.environ["AGENT_PLANNER_PRIMARY"] = "openai/gpt-4o-mini"
        get_env_override("planner", "primary")  # → "openai/gpt-4o-mini"
    """
    var_name = f"AGENT_{agent_name.upper()}_{key.upper()}"
    return os.environ.get(var_name)
