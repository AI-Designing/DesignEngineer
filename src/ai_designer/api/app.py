"""
FastAPI application factory with middleware and error handling.
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ai_designer.api.middleware import AuthMiddleware, RateLimitMiddleware
from ai_designer.api.routes import design, health, ws
from ai_designer.core.exceptions import (
    AgentError,
    ConfigurationError,
    FreeCADError,
    LLMError,
)
from ai_designer.core.metrics import instrument_app

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.

    Handles startup and shutdown operations:
    - Initialize connections (Redis, etc.)
    - Cleanup on shutdown
    """
    logger.info("Starting FreeCAD AI Designer API")
    # Startup: Initialize any global resources here
    # (Redis connections, model loading, etc.)

    yield

    # Shutdown: Cleanup resources
    logger.info("Shutting down FreeCAD AI Designer API")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title="FreeCAD AI Designer API",
        description="Multi-agent CAD automation system with LLM-powered design generation",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure based on deployment
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate-limit middleware (sliding window, backed by Redis)
    app.add_middleware(RateLimitMiddleware)

    # JWT auth middleware (validates Bearer tokens for protected paths)
    app.add_middleware(AuthMiddleware)

    # Add request ID middleware
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        """Add unique request ID to each request for correlation."""
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        request.state.request_id = request_id

        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)

        return response

    # Exception handlers
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        """Handle request validation errors."""
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "Validation Error",
                "detail": exc.errors(),
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    @app.exception_handler(ConfigurationError)
    async def config_exception_handler(request: Request, exc: ConfigurationError):
        """Handle configuration errors."""
        logger.error(f"Configuration error: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Configuration Error",
                "detail": str(exc),
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    @app.exception_handler(LLMError)
    async def llm_exception_handler(request: Request, exc: LLMError):
        """Handle LLM provider errors."""
        logger.error(f"LLM error: {exc}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": "LLM Service Error",
                "detail": str(exc),
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    @app.exception_handler(FreeCADError)
    async def freecad_exception_handler(request: Request, exc: FreeCADError):
        """Handle FreeCAD execution errors."""
        logger.error(f"FreeCAD error: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "FreeCAD Execution Error",
                "detail": str(exc),
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    @app.exception_handler(AgentError)
    async def agent_exception_handler(request: Request, exc: AgentError):
        """Handle agent execution errors."""
        logger.error(f"Agent error: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Agent Execution Error",
                "detail": str(exc),
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected errors."""
        logger.exception(f"Unexpected error: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal Server Error",
                "detail": "An unexpected error occurred",
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    # Include routers
    app.include_router(health.router, tags=["Health"])
    app.include_router(design.router, prefix="/api/v1", tags=["Design"])
    app.include_router(ws.router, prefix="/ws", tags=["WebSocket"])

    # Prometheus middleware + /metrics route (must come after routers)
    instrument_app(app)

    return app
