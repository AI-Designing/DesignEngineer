"""
AI Designer - FreeCAD LLM Automation System

An intelligent assistant for parametric CAD design in FreeCAD using Large Language Models.
"""

from __future__ import annotations

import typing

__version__ = "0.1.0"
__author__ = "AI Designer Team"
__email__ = "contact@ai-designer.com"

__all__ = ["FreeCADCLI"]


def __getattr__(name: str) -> typing.Any:
    """Lazy import so ``import ai_designer`` does not pull FreeCAD/LLM stacks."""
    if name == "FreeCADCLI":
        from .cli import FreeCADCLI

        return FreeCADCLI
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | {"FreeCADCLI"})
