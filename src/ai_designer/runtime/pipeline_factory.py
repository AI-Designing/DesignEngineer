"""
Construct LangGraph :class:`~ai_designer.orchestration.pipeline.PipelineExecutor`.

Single place for the ``PipelineExecutor(...)`` call shape so FastAPI deps and
CLI stay aligned.
"""

from __future__ import annotations

import logging
import os
from typing import Callable, Optional

from ai_designer.agents.executor import FreeCADExecutor
from ai_designer.agents.generator import GeneratorAgent
from ai_designer.agents.planner import PlannerAgent
from ai_designer.agents.validator import ValidatorAgent
from ai_designer.core.llm_provider import UnifiedLLMProvider
from ai_designer.orchestration.pipeline import PipelineExecutor

logger = logging.getLogger(__name__)


def create_pipeline_executor(
    planner: PlannerAgent,
    generator: GeneratorAgent,
    validator: ValidatorAgent,
    executor: Optional[FreeCADExecutor] = None,
    *,
    max_iterations: int = 5,
    websocket_callback: Optional[Callable] = None,
) -> PipelineExecutor:
    """
    Build a ``PipelineExecutor`` with the given agents.

    Args:
        planner: Planner agent
        generator: Generator agent
        validator: Validator agent
        executor: FreeCAD executor (optional; pipeline may still plan/generate)
        max_iterations: Refinement cap
        websocket_callback: Optional progress hook

    Returns:
        Configured pipeline executor
    """
    return PipelineExecutor(
        planner=planner,
        generator=generator,
        validator=validator,
        executor=executor,
        websocket_callback=websocket_callback,
        max_iterations=max_iterations,
    )


def build_default_freecad_executor() -> FreeCADExecutor:
    """Create a ``FreeCADExecutor`` using the same defaults as API dependencies."""
    freecad_path = os.getenv("FREECAD_PATH")
    return FreeCADExecutor(
        timeout=600,
        save_outputs=True,
        freecad_path=freecad_path,
    )


def build_cli_pipeline_executor(
    *,
    max_iterations: int = 5,
    websocket_callback: Optional[Callable] = None,
) -> PipelineExecutor:
    """
    Build a fresh pipeline for **CLI** use (separate process from uvicorn).

    Does not use FastAPI globals in ``api.deps``; safe for ``python -m ai_designer``.

    Raises:
        Exception: If ``UnifiedLLMProvider`` cannot be constructed (misconfigured keys, etc.)
    """
    llm_provider = UnifiedLLMProvider()
    planner = PlannerAgent(llm_provider=llm_provider)
    generator = GeneratorAgent(llm_provider=llm_provider)
    validator = ValidatorAgent(llm_provider=llm_provider)
    executor = build_default_freecad_executor()
    pipe = create_pipeline_executor(
        planner,
        generator,
        validator,
        executor,
        max_iterations=max_iterations,
        websocket_callback=websocket_callback,
    )
    logger.info("CLI PipelineExecutor initialized (standalone stack)")
    return pipe
