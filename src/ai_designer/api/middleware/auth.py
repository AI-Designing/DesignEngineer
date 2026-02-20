"""
JWT Bearer-token authentication middleware.

Usage
-----
Register globally in create_app():

    from ai_designer.api.middleware import AuthMiddleware
    app.add_middleware(AuthMiddleware)

Or protect individual routes with the ``require_auth`` dependency:

    from ai_designer.api.middleware import require_auth
    @router.get("/protected")
    async def protected(user: dict = Depends(require_auth)):
        ...

Environment variables
---------------------
AUTH_SECRET_KEY   HMAC secret (required).  Min 32 chars.
AUTH_ALGORITHM    JWT algorithm (default: HS256).
AUTH_DISABLED     Set to "1" to bypass authentication (dev only).
AUTH_EXEMPT_PATHS Comma-separated URL prefixes that skip auth.
                  Defaults: /health, /docs, /redoc, /openapi.json, /metrics
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
_SECRET_KEY: str = os.getenv("AUTH_SECRET_KEY", "")
_ALGORITHM: str = os.getenv("AUTH_ALGORITHM", "HS256")
_DISABLED: bool = os.getenv("AUTH_DISABLED", "0") == "1"
_EXEMPT_PREFIXES: list[str] = [
    p.strip()
    for p in os.getenv(
        "AUTH_EXEMPT_PATHS",
        "/health,/docs,/redoc,/openapi.json,/metrics",
    ).split(",")
    if p.strip()
]

# ── Optional jose import ──────────────────────────────────────────────────────
try:
    from jose import JWTError, jwt  # type: ignore[import]

    _JOSE_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover
    _JOSE_AVAILABLE = False
    logger.warning(
        "python-jose is not installed. "
        "JWT validation will always fail unless AUTH_DISABLED=1."
    )


# ── Token decoder ─────────────────────────────────────────────────────────────

def _decode_token(token: str) -> dict[str, Any]:
    """
    Decode and verify a JWT.

    Raises
    ------
    HTTPException 401  on invalid / expired / missing secret.
    """
    if not _SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AUTH_SECRET_KEY is not configured on the server.",
        )
    if not _JOSE_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT library not available.",
        )
    try:
        payload: dict[str, Any] = jwt.decode(
            token, _SECRET_KEY, algorithms=[_ALGORITHM]
        )
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


# ── FastAPI dependency ────────────────────────────────────────────────────────

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> dict[str, Any] | None:
    """
    Dependency that returns the decoded JWT payload, or ``None`` if auth is
    disabled.  Raises 401 when auth is required but credentials are missing or
    invalid.
    """
    if _DISABLED:
        return {"sub": "anonymous", "disabled_auth": True}

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return _decode_token(credentials.credentials)


async def require_auth(
    user: dict[str, Any] | None = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Strict auth dependency — always demands a valid token (even when
    AUTH_DISABLED is set, it still returns a synthetic user dict so route
    signatures stay consistent).
    """
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


# ── Starlette middleware class ────────────────────────────────────────────────

class AuthMiddleware:
    """
    ASGI middleware that validates Bearer tokens for every non-exempt path.

    Adds ``request.state.user`` with the decoded JWT payload on success.
    Returns 401 JSON for protected paths that lack a valid token.
    """

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")

        # Always pass through exempt paths
        if _DISABLED or any(path.startswith(p) for p in _EXEMPT_PREFIXES):
            await self.app(scope, receive, send)
            return

        # Extract Authorization header
        headers = dict(scope.get("headers", []))
        auth_bytes: bytes = headers.get(b"authorization", b"")
        auth_value: str = auth_bytes.decode("latin-1") if auth_bytes else ""

        if not auth_value.lower().startswith("bearer "):
            await self._send_401(send, "Authorization header missing or not Bearer.")
            return

        token = auth_value[7:].strip()
        try:
            payload = _decode_token(token)
        except HTTPException as exc:
            await self._send_401(send, exc.detail)
            return

        # Attach user to request state via scope extras
        scope.setdefault("state", {})["user"] = payload
        await self.app(scope, receive, send)

    @staticmethod
    async def _send_401(send: Any, detail: str) -> None:
        import json

        body = json.dumps({"error": "Unauthorized", "detail": detail}).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                    (b"www-authenticate", b"Bearer"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
