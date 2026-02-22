"""
Redis-backed agent model configuration store.

Allows runtime hot-swapping of the LLM model assigned to each agent
(planner, generator, validator, orchestrator) without restarting the server.

Redis key layout
----------------
  agent_config:{agent_name}:primary   → primary model string
  agent_config:{agent_name}:fallback  → fallback model string (optional)
  agent_config:{agent_name}:temperature → float string
  agent_config:{agent_name}:max_tokens  → int string

If a Redis key is absent, :func:`get_agent_model_config` falls back to
``AGENT_MODEL_CONFIG`` from :mod:`ai_designer.llm.model_config` (which itself
supports env-var overrides).

Usage
-----
::

    from ai_designer.llm.agent_config_store import AgentConfigStore

    store = AgentConfigStore()

    # Override planner model at runtime
    store.set("planner", primary="openai/gpt-4o-mini")

    # Read effective config (Redis override → env override → YAML default)
    cfg = store.get("planner")
    print(cfg["primary"])  # "openai/gpt-4o-mini"

    # Reset to default
    store.reset("planner")
"""

import logging
from typing import Any, Dict, Optional

import redis

from ai_designer.llm.model_config import AGENT_MODEL_CONFIG, get_agent_config

logger = logging.getLogger(__name__)

# Redis key prefix for all agent config entries
_KEY_PREFIX = "agent_config"

# Fields we persist in Redis per agent
_FIELDS = ("primary", "fallback", "temperature", "max_tokens")


class AgentConfigStore:
    """
    Thin wrapper around Redis for per-agent LLM model configuration.

    Thread-safe: each method opens/closes its own Redis pipeline or uses the
    shared connection pool.
    """

    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        redis_password: Optional[str] = None,
        ttl: Optional[int] = None,
    ):
        """
        Initialise the store.

        Args:
            redis_host: Redis server hostname.
            redis_port: Redis server port.
            redis_db: Redis database index.
            redis_password: Optional Redis AUTH password.
            ttl: Optional TTL (seconds) for all keys written by this store.
                 ``None`` means keys persist indefinitely.
        """
        self._ttl = ttl
        try:
            self._redis = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                decode_responses=True,
                socket_connect_timeout=5,
            )
            self._redis.ping()
            logger.info(
                "AgentConfigStore connected to Redis",
                extra={"host": redis_host, "port": redis_port},
            )
        except redis.RedisError as exc:
            logger.warning(
                "AgentConfigStore: Redis unavailable (%s). "
                "Runtime overrides will not be persisted; "
                "falling back to static config.",
                exc,
            )
            self._redis = None  # type: ignore[assignment]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, agent_name: str) -> Dict[str, Any]:
        """Return the effective model config for *agent_name*.

        Priority:  Redis override  >  env-var override  >  YAML default.

        Args:
            agent_name: One of ``"planner"``, ``"generator"``, ``"validator"``,
                ``"orchestrator"``.

        Returns:
            Dict with keys ``primary``, ``fallback``, ``temperature``,
            ``max_tokens``.
        """
        # Start from the static default (already applies env-var overrides)
        base = get_agent_config(agent_name)

        if self._redis is None:
            return base

        # Apply any Redis overrides on top
        redis_overrides = self._read_redis(agent_name)
        if redis_overrides:
            for field, value in redis_overrides.items():
                base[field] = value  # type: ignore[assignment]

        return base

    def set(
        self,
        agent_name: str,
        primary: Optional[str] = None,
        fallback: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> None:
        """Persist model config overrides for *agent_name* in Redis.

        Only the provided keyword arguments are written; the rest remain
        unchanged (Redis keys are set/updated individually).

        Args:
            agent_name: Target agent identifier.
            primary: New primary model string (e.g. ``"openai/gpt-4o-mini"``).
            fallback: New fallback model string.
            temperature: Sampling temperature override.
            max_tokens: Token limit override.

        Raises:
            ValueError: If *agent_name* is not known.
        """
        if agent_name.lower() not in AGENT_MODEL_CONFIG:
            raise ValueError(
                f"Unknown agent '{agent_name}'. "
                f"Valid names: {list(AGENT_MODEL_CONFIG.keys())}"
            )

        if self._redis is None:
            logger.warning(
                "AgentConfigStore: Redis unavailable; override for '%s' not saved.",
                agent_name,
            )
            return

        pipe = self._redis.pipeline()
        updates: Dict[str, str] = {}

        if primary is not None:
            updates["primary"] = primary
        if fallback is not None:
            updates["fallback"] = fallback
        if temperature is not None:
            updates["temperature"] = str(temperature)
        if max_tokens is not None:
            updates["max_tokens"] = str(max_tokens)

        for field, value in updates.items():
            key = self._key(agent_name, field)
            pipe.set(key, value)
            if self._ttl is not None:
                pipe.expire(key, self._ttl)

        pipe.execute()
        logger.info(
            "AgentConfigStore: updated '%s' config in Redis: %s",
            agent_name,
            updates,
        )

    def reset(self, agent_name: str) -> None:
        """Remove all Redis overrides for *agent_name*, reverting to defaults.

        Args:
            agent_name: Target agent identifier.
        """
        if self._redis is None:
            return

        pipe = self._redis.pipeline()
        for field in _FIELDS:
            pipe.delete(self._key(agent_name, field))
        pipe.execute()
        logger.info("AgentConfigStore: reset '%s' to config defaults", agent_name)

    def get_all(self) -> Dict[str, Dict[str, Any]]:
        """Return effective configs for all known agents.

        Returns:
            Dict mapping agent name → effective config dict.
        """
        return {name: self.get(name) for name in AGENT_MODEL_CONFIG}

    def get_override_source(self, agent_name: str) -> Dict[str, str]:
        """Return a per-field source map for *agent_name*.

        Returns:
            Dict mapping field → ``"redis_override"`` or ``"config_default"``.
        """
        redis_overrides = self._read_redis(agent_name) if self._redis else {}
        result: Dict[str, str] = {}
        for field in _FIELDS:
            result[field] = (
                "redis_override" if field in redis_overrides else "config_default"
            )
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _key(self, agent_name: str, field: str) -> str:
        return f"{_KEY_PREFIX}:{agent_name.lower()}:{field}"

    def _read_redis(self, agent_name: str) -> Dict[str, Any]:
        """Read all persisted fields for *agent_name* from Redis.

        Returns an empty dict if Redis is unreachable or no keys exist.
        """
        overrides: Dict[str, Any] = {}
        try:
            for field in _FIELDS:
                val = self._redis.get(self._key(agent_name, field))
                if val is not None:
                    if field == "temperature":
                        overrides[field] = float(val)
                    elif field == "max_tokens":
                        overrides[field] = int(val)
                    else:
                        overrides[field] = val
        except redis.RedisError as exc:
            logger.warning("AgentConfigStore: Redis read error: %s", exc)
        return overrides


# ---------------------------------------------------------------------------
# Module-level singleton — shared across agents
# ---------------------------------------------------------------------------
_store: Optional[AgentConfigStore] = None


def get_agent_config_store(
    redis_host: str = "localhost",
    redis_port: int = 6379,
    redis_db: int = 0,
    redis_password: Optional[str] = None,
) -> AgentConfigStore:
    """Return the module-level :class:`AgentConfigStore` singleton.

    The first call initialises the store; subsequent calls reuse it.
    """
    global _store
    if _store is None:
        _store = AgentConfigStore(
            redis_host=redis_host,
            redis_port=redis_port,
            redis_db=redis_db,
            redis_password=redis_password,
        )
    return _store
