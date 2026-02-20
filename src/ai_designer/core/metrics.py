"""
Prometheus instrumentation for the FreeCAD AI Designer API.

Provides
--------
- HTTP request counters and latency histograms (auto-instrumented via middleware)
- LLM call counters and duration histograms
- FreeCAD execution counters and duration histograms
- Agent execution gauges/counters
- A ``/metrics`` text endpoint for Prometheus scraping

Usage
-----
Register in ``create_app()``:

    from ai_designer.core.metrics import add_metrics_route, instrument_app
    instrument_app(app)   # adds /metrics route + HTTP middleware
"""

from __future__ import annotations

import logging
import os
import time
from functools import wraps
from typing import Any, Callable

logger = logging.getLogger(__name__)

# ── Optional prometheus_client import ─────────────────────────────────────────
try:
    from prometheus_client import (  # type: ignore[import]
        CONTENT_TYPE_LATEST,
        Counter,
        Gauge,
        Histogram,
        Summary,
        generate_latest,
        multiprocess,
        CollectorRegistry,
        REGISTRY,
    )

    _PROM_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover
    _PROM_AVAILABLE = False
    logger.warning(
        "prometheus_client is not installed. Metrics endpoint will be disabled."
    )

# ── Registry ─────────────────────────────────────────────────────────────────
# Support multi-process mode (uvicorn workers) via PROMETHEUS_MULTIPROC_DIR
_MULTIPROC_DIR = os.getenv("PROMETHEUS_MULTIPROC_DIR", "")
if _PROM_AVAILABLE and _MULTIPROC_DIR:  # pragma: no cover
    _registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(_registry)
else:
    _registry = REGISTRY if _PROM_AVAILABLE else None  # type: ignore[assignment]

# ── Metric definitions ────────────────────────────────────────────────────────
if _PROM_AVAILABLE:
    # HTTP
    HTTP_REQUESTS_TOTAL = Counter(
        "http_requests_total",
        "Total HTTP requests received",
        ["method", "path", "status_code"],
    )
    HTTP_REQUEST_DURATION_SECONDS = Histogram(
        "http_request_duration_seconds",
        "HTTP request latency",
        ["method", "path"],
        buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    )
    HTTP_REQUESTS_IN_FLIGHT = Gauge(
        "http_requests_in_flight",
        "HTTP requests currently being processed",
    )

    # LLM
    LLM_CALLS_TOTAL = Counter(
        "llm_calls_total",
        "Total LLM API calls",
        ["provider", "model", "status"],
    )
    LLM_CALL_DURATION_SECONDS = Histogram(
        "llm_call_duration_seconds",
        "LLM call latency",
        ["provider", "model"],
        buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
    )
    LLM_TOKEN_USAGE = Counter(
        "llm_token_usage_total",
        "Total tokens consumed",
        ["provider", "model", "token_type"],
    )
    LLM_COST_USD = Counter(
        "llm_cost_usd_total",
        "Cumulative LLM cost in USD",
        ["provider", "model"],
    )

    # FreeCAD execution
    FREECAD_EXECUTIONS_TOTAL = Counter(
        "freecad_executions_total",
        "Total FreeCAD script executions",
        ["status"],
    )
    FREECAD_EXECUTION_DURATION_SECONDS = Histogram(
        "freecad_execution_duration_seconds",
        "FreeCAD execution latency",
        buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 15.0, 30.0, 60.0],
    )

    # Agent
    AGENT_RUNS_TOTAL = Counter(
        "agent_runs_total",
        "Total agent execution runs",
        ["agent_type", "status"],
    )
    AGENT_ACTIVE = Gauge(
        "agent_active_count",
        "Number of currently running agent instances",
        ["agent_type"],
    )
    AGENT_WORKFLOW_STEPS = Histogram(
        "agent_workflow_steps",
        "Number of workflow steps per agent run",
        ["agent_type"],
        buckets=[1, 2, 3, 5, 8, 13, 21, 34],
    )

    # WebSocket
    WEBSOCKET_CONNECTIONS = Gauge(
        "websocket_connections_active",
        "Number of active WebSocket connections",
    )

else:  # pragma: no cover — stubs so code won't crash if prom unavailable
    class _NoOp:
        """No-op stub that absorbs any attribute/call."""

        def __getattr__(self, _: str) -> "_NoOp":
            return self

        def __call__(self, *a: Any, **kw: Any) -> "_NoOp":
            return self

    _noop = _NoOp()
    HTTP_REQUESTS_TOTAL = _noop  # type: ignore[assignment]
    HTTP_REQUEST_DURATION_SECONDS = _noop  # type: ignore[assignment]
    HTTP_REQUESTS_IN_FLIGHT = _noop  # type: ignore[assignment]
    LLM_CALLS_TOTAL = _noop  # type: ignore[assignment]
    LLM_CALL_DURATION_SECONDS = _noop  # type: ignore[assignment]
    LLM_TOKEN_USAGE = _noop  # type: ignore[assignment]
    LLM_COST_USD = _noop  # type: ignore[assignment]
    FREECAD_EXECUTIONS_TOTAL = _noop  # type: ignore[assignment]
    FREECAD_EXECUTION_DURATION_SECONDS = _noop  # type: ignore[assignment]
    AGENT_RUNS_TOTAL = _noop  # type: ignore[assignment]
    AGENT_ACTIVE = _noop  # type: ignore[assignment]
    AGENT_WORKFLOW_STEPS = _noop  # type: ignore[assignment]
    WEBSOCKET_CONNECTIONS = _noop  # type: ignore[assignment]


# ── Helper decorators ─────────────────────────────────────────────────────────

def track_llm_call(provider: str, model: str) -> Callable:
    """
    Decorator to instrument LLM calls.

    Example::

        @track_llm_call("openai", "gpt-4o")
        async def call_openai(prompt):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            status = "success"
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception:
                status = "error"
                raise
            finally:
                duration = time.perf_counter() - start
                LLM_CALLS_TOTAL.labels(
                    provider=provider, model=model, status=status
                ).inc()
                LLM_CALL_DURATION_SECONDS.labels(
                    provider=provider, model=model
                ).observe(duration)

        return async_wrapper

    return decorator


def track_freecad_execution(func: Callable) -> Callable:
    """
    Decorator to instrument FreeCAD script executions.

    Example::

        @track_freecad_execution
        async def execute_script(script: str): ...
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        status = "success"
        try:
            result = await func(*args, **kwargs)
            return result
        except Exception:
            status = "error"
            raise
        finally:
            duration = time.perf_counter() - start
            FREECAD_EXECUTIONS_TOTAL.labels(status=status).inc()
            FREECAD_EXECUTION_DURATION_SECONDS.observe(duration)

    return wrapper


# ── FastAPI integration ───────────────────────────────────────────────────────

def add_metrics_route(app: Any) -> None:
    """
    Add a ``GET /metrics`` route that returns Prometheus text format.

    Call after all routers are registered.
    """
    if not _PROM_AVAILABLE:
        logger.warning("prometheus_client not available — /metrics not registered.")
        return

    from starlette.responses import Response as _Resp

    def _metrics_view():  # no annotation — FastAPI won't try to resolve it
        data = generate_latest(_registry)
        return _Resp(content=data, media_type=CONTENT_TYPE_LATEST)

    app.add_api_route(
        "/metrics",
        _metrics_view,
        methods=["GET"],
        include_in_schema=False,
        tags=["Monitoring"],
    )


class PrometheusMiddleware:
    """
    ASGI middleware that instruments every HTTP request with Prometheus metrics:
    - ``http_requests_total``          counter (method, path, status_code)
    - ``http_request_duration_seconds`` histogram (method, path)
    - ``http_requests_in_flight``       gauge
    """

    # Paths that should not pollute metrics with high-cardinality noise
    _SKIP_PATHS = frozenset(["/metrics", "/health", "/favicon.ico"])

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")
        method: str = scope.get("method", "UNKNOWN")

        if path in self._SKIP_PATHS:
            await self.app(scope, receive, send)
            return

        HTTP_REQUESTS_IN_FLIGHT.inc()
        start = time.perf_counter()
        status_code = 500

        async def _send_and_capture(message: Any) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 500)
            await send(message)

        try:
            await self.app(scope, receive, _send_and_capture)
        finally:
            duration = time.perf_counter() - start
            HTTP_REQUESTS_IN_FLIGHT.dec()
            # Normalise path to avoid high cardinality from IDs
            norm_path = _normalise_path(path)
            HTTP_REQUESTS_TOTAL.labels(
                method=method, path=norm_path, status_code=str(status_code)
            ).inc()
            HTTP_REQUEST_DURATION_SECONDS.labels(
                method=method, path=norm_path
            ).observe(duration)


def _normalise_path(path: str) -> str:
    """
    Replace numeric / UUID segments with ``{id}`` to reduce cardinality.

    Examples::
        /api/v1/designs/123          → /api/v1/designs/{id}
        /api/v1/designs/abc-uuid     → /api/v1/designs/{id}
    """
    import re

    return re.sub(
        r"/([\da-fA-F]{8}-[\da-fA-F]{4}-[\da-fA-F]{4}-[\da-fA-F]{4}-[\da-fA-F]{12}|\d+)",
        "/{id}",
        path,
    )


def instrument_app(app: Any) -> None:
    """
    Convenience function: register Prometheus middleware AND ``/metrics`` route.

    Call inside ``create_app()`` after other middleware:

        instrument_app(app)
    """
    app.add_middleware(PrometheusMiddleware)
    add_metrics_route(app)
