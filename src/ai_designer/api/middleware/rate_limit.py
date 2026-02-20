"""
Redis sliding-window rate-limit middleware.

Algorithm
---------
For each (client_key, window_start) we keep a Redis sorted-set whose members
are individual request timestamps (as floats).  On each request:

1. Remove entries older than ``window_seconds``.
2. Count remaining entries.
3. If count >= ``max_requests``, respond with 429.
4. Otherwise, add the current timestamp and set TTL.

The client key is taken from (in priority order):
  - Authenticated user ``sub`` on ``request.state.user``
  - ``X-Forwarded-For`` header (first IP)
  - Remote address

Configuration (env vars or constructor kwargs)
----------------------------------------------
RATE_LIMIT_MAX_REQUESTS   int, default 60
RATE_LIMIT_WINDOW_SECONDS int, default 60
RATE_LIMIT_REDIS_URL      str, default redis://localhost:6379/0
RATE_LIMIT_DISABLED       "1" to bypass globally (dev/test)
RATE_LIMIT_EXEMPT_PATHS   comma-separated prefixes that skip limiting
                          Defaults: /health, /metrics
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
_MAX_REQUESTS: int = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "60"))
_WINDOW_SECONDS: int = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
_REDIS_URL: str = os.getenv("RATE_LIMIT_REDIS_URL", "redis://localhost:6379/0")
_DISABLED: bool = os.getenv("RATE_LIMIT_DISABLED", "0") == "1"
_EXEMPT_PREFIXES: list[str] = [
    p.strip()
    for p in os.getenv("RATE_LIMIT_EXEMPT_PATHS", "/health,/metrics").split(",")
    if p.strip()
]

# ── Optional redis import ─────────────────────────────────────────────────────
try:
    import redis.asyncio as aioredis  # type: ignore[import]

    _REDIS_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover
    _REDIS_AVAILABLE = False
    logger.warning(
        "redis package not installed. Rate limiting will be disabled."
    )


def _get_redis_pool() -> Any | None:
    """
    Lazily create a single async Redis connection pool.
    Returns None when Redis is unavailable.
    """
    if not _REDIS_AVAILABLE:
        return None
    try:
        return aioredis.from_url(
            _REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=1,
        )
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not create Redis connection pool: %s", exc)
        return None


_redis_pool: Any | None = None  # module-level singleton


def _redis() -> Any | None:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = _get_redis_pool()
    return _redis_pool


# ── Rate-limit logic ──────────────────────────────────────────────────────────

async def _check_rate_limit(
    client_key: str,
    max_requests: int,
    window_seconds: int,
) -> tuple[bool, int, int]:
    """
    Check whether the client has exceeded the rate limit.

    Returns
    -------
    (allowed, remaining, retry_after_seconds)
    """
    pool = _redis()
    if pool is None:
        # Fail-open: allow the request if Redis is unavailable
        return True, max_requests, 0

    now = time.time()
    window_start = now - window_seconds
    redis_key = f"rate_limit:{client_key}"

    try:
        pipe = pool.pipeline()
        # Remove old entries
        pipe.zremrangebyscore(redis_key, "-inf", window_start)
        # Count entries in current window
        pipe.zcard(redis_key)
        # Add current request
        pipe.zadd(redis_key, {str(now): now})
        # Reset TTL
        pipe.expire(redis_key, window_seconds * 2)
        results = await pipe.execute()

        count: int = results[1]  # count BEFORE adding current request

        if count >= max_requests:
            remaining = 0
            retry_after = int(window_seconds - (now - window_start))
            return False, remaining, max(retry_after, 1)

        remaining = max_requests - count - 1
        return True, remaining, 0

    except Exception as exc:  # pragma: no cover
        logger.warning("Rate-limit Redis error (fail-open): %s", exc)
        return True, max_requests, 0


# ── Middleware class ──────────────────────────────────────────────────────────

class RateLimitMiddleware:
    """
    ASGI middleware for sliding-window rate limiting backed by Redis.

    Parameters
    ----------
    app             ASGI application.
    max_requests    Requests allowed per window (overrides env var).
    window_seconds  Rolling window duration in seconds (overrides env var).
    """

    def __init__(
        self,
        app: Any,
        max_requests: int = _MAX_REQUESTS,
        window_seconds: int = _WINDOW_SECONDS,
    ) -> None:
        self.app = app
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")

        if _DISABLED or any(path.startswith(p) for p in _EXEMPT_PREFIXES):
            await self.app(scope, receive, send)
            return

        client_key = self._resolve_client_key(scope)

        allowed, remaining, retry_after = await _check_rate_limit(
            client_key, self.max_requests, self.window_seconds
        )

        if not allowed:
            await self._send_429(send, remaining, retry_after)
            return

        # Inject rate-limit headers via a wrapper so we can set them on the
        # actual response rather than crafting a new one.
        async def send_with_headers(message: Any) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers += [
                    (b"x-ratelimit-limit", str(self.max_requests).encode()),
                    (b"x-ratelimit-remaining", str(remaining).encode()),
                    (b"x-ratelimit-window", str(self.window_seconds).encode()),
                ]
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_headers)

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _resolve_client_key(scope: Any) -> str:
        """Determine a stable per-client identifier for rate-limit bucketing."""
        # Prefer authenticated user identity
        state: dict[str, Any] = scope.get("state", {})
        user = state.get("user") or {}
        if isinstance(user, dict) and user.get("sub"):
            return f"user:{user['sub']}"

        # Fall back to IP
        headers = dict(scope.get("headers", []))
        xff: bytes = headers.get(b"x-forwarded-for", b"")
        if xff:
            ip = xff.decode("latin-1").split(",")[0].strip()
            return f"ip:{ip}"

        client = scope.get("client")
        if client:
            return f"ip:{client[0]}"

        return "ip:unknown"

    @staticmethod
    async def _send_429(send: Any, remaining: int, retry_after: int) -> None:
        import json

        body = json.dumps(
            {
                "error": "Too Many Requests",
                "detail": "Rate limit exceeded. Please slow down.",
                "retry_after": retry_after,
            }
        ).encode()

        await send(
            {
                "type": "http.response.start",
                "status": 429,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                    (b"retry-after", str(retry_after).encode()),
                    (b"x-ratelimit-remaining", b"0"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
