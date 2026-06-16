"""
AI Designer - FreeCAD LLM Automation System

Production runtime: FastAPI service (``uvicorn ai_designer.api.app:app``).
"""

from __future__ import annotations

__version__ = "0.1.0"
__author__ = "AI Designer Team"
__email__ = "contact@ai-designer.com"

__all__ = ["create_app"]


def __getattr__(name: str):
    """Lazy import so ``import ai_designer`` does not pull the full API stack."""
    if name == "create_app":
        from ai_designer.api import create_app

        return create_app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | {"create_app"})
