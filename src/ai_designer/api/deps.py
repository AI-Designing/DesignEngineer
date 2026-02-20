"""
Dependency injection for FastAPI endpoints.

Provides reusable dependencies for:
- LLM provider access
- Redis connections
- Agent instances
- Configuration
"""

import logging
from typing import Optional

from fastapi import Depends, Header, HTTPException, status

from ai_designer.agents.executor import FreeCADExecutor
from ai_designer.agents.generator import GeneratorAgent
from ai_designer.agents.orchestrator import OrchestratorAgent
from ai_designer.agents.planner import PlannerAgent
from ai_designer.agents.validator import ValidatorAgent
from ai_designer.core.llm_provider import UnifiedLLMProvider
from ai_designer.export.exporter import CADExporter
from ai_designer.orchestration.pipeline import PipelineExecutor

logger = logging.getLogger(__name__)


# Global instances (will be initialized on app startup)
_llm_provider: Optional[UnifiedLLMProvider] = None
_planner_agent: Optional[PlannerAgent] = None
_generator_agent: Optional[GeneratorAgent] = None
_validator_agent: Optional[ValidatorAgent] = None
_orchestrator_agent: Optional[OrchestratorAgent] = None
_freecad_executor: Optional[FreeCADExecutor] = None
_pipeline_executor: Optional[PipelineExecutor] = None
_cad_exporter: Optional[CADExporter] = None


def get_llm_provider() -> UnifiedLLMProvider:
    """
    Get the unified LLM provider instance.

    Returns:
        Configured LLM provider

    Raises:
        HTTPException: If provider not initialized
    """
    global _llm_provider

    if _llm_provider is None:
        # Initialize on first use
        try:
            _llm_provider = UnifiedLLMProvider()
            logger.info("Initialized UnifiedLLMProvider")
        except Exception as e:
            logger.error(f"Failed to initialize LLM provider: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LLM provider unavailable",
            )

    return _llm_provider


def get_planner_agent(
    llm_provider: UnifiedLLMProvider = Depends(get_llm_provider),
) -> PlannerAgent:
    """
    Get the Planner Agent instance.

    Args:
        llm_provider: LLM provider dependency

    Returns:
        Configured Planner Agent
    """
    global _planner_agent

    if _planner_agent is None:
        _planner_agent = PlannerAgent(llm_provider=llm_provider)
        logger.info("Initialized PlannerAgent")

    return _planner_agent


def get_generator_agent(
    llm_provider: UnifiedLLMProvider = Depends(get_llm_provider),
) -> GeneratorAgent:
    """
    Get the Generator Agent instance.

    Args:
        llm_provider: LLM provider dependency

    Returns:
        Configured Generator Agent
    """
    global _generator_agent

    if _generator_agent is None:
        _generator_agent = GeneratorAgent(llm_provider=llm_provider)
        logger.info("Initialized GeneratorAgent")

    return _generator_agent


def get_validator_agent(
    llm_provider: UnifiedLLMProvider = Depends(get_llm_provider),
) -> ValidatorAgent:
    """
    Get the Validator Agent instance.

    Args:
        llm_provider: LLM provider dependency

    Returns:
        Configured Validator Agent
    """
    global _validator_agent

    if _validator_agent is None:
        _validator_agent = ValidatorAgent(llm_provider=llm_provider)
        logger.info("Initialized ValidatorAgent")

    return _validator_agent


def get_freecad_executor() -> FreeCADExecutor:
    """
    Get the FreeCAD Executor instance.

    Returns:
        Configured FreeCAD Executor
    """
    global _freecad_executor

    if _freecad_executor is None:
        _freecad_executor = FreeCADExecutor(
            timeout=60,
            save_outputs=True,
        )
        logger.info("Initialized FreeCADExecutor")

    return _freecad_executor


def get_orchestrator_agent(
    planner: PlannerAgent = Depends(get_planner_agent),
    generator: GeneratorAgent = Depends(get_generator_agent),
    validator: ValidatorAgent = Depends(get_validator_agent),
) -> OrchestratorAgent:
    """
    Get the Orchestrator Agent instance.

    Args:
        planner: Planner agent dependency
        generator: Generator agent dependency
        validator: Validator agent dependency

    Returns:
        Configured Orchestrator Agent
    """
    global _orchestrator_agent

    if _orchestrator_agent is None:
        _orchestrator_agent = OrchestratorAgent(
            llm_provider=get_llm_provider(),
            planner=planner,
            generator=generator,
            validator=validator,
            max_iterations=5,
            enable_refinement=True,
        )
        logger.info("Initialized OrchestratorAgent")

    return _orchestrator_agent


async def verify_api_key(
    x_api_key: Optional[str] = Header(None, description="API key for authentication"),
) -> str:
    """
    Verify API key authentication.

    Args:
        x_api_key: API key from request header

    Returns:
        Verified API key

    Raises:
        HTTPException: If API key is missing or invalid
    """
    # TODO: Implement actual API key verification
    # For now, accept any key or no key (development mode)

    if x_api_key is None:
        logger.warning("No API key provided (development mode)")
        return "dev-mode"

    # TODO: Verify against stored keys in Redis/database
    # For now, accept all keys
    return x_api_key


def get_pipeline_executor(
    planner: PlannerAgent = Depends(get_planner_agent),
    generator: GeneratorAgent = Depends(get_generator_agent),
    validator: ValidatorAgent = Depends(get_validator_agent),
    executor: FreeCADExecutor = Depends(get_freecad_executor),
) -> PipelineExecutor:
    """
    Get the LangGraph Pipeline Executor instance.

    Args:
        planner: Planner agent dependency
        generator: Generator agent dependency
        validator: Validator agent dependency
        executor: FreeCAD executor dependency

    Returns:
        Configured Pipeline Executor with LangGraph orchestration
    """
    global _pipeline_executor

    if _pipeline_executor is None:
        _pipeline_executor = PipelineExecutor(
            planner=planner,
            generator=generator,
            validator=validator,
            executor=executor,
            websocket_callback=None,  # Will be set when WebSocket manager is ready
            max_iterations=5,
        )
        logger.info("Initialized PipelineExecutor with LangGraph")

    return _pipeline_executor


def get_cad_exporter() -> CADExporter:
    """
    Get the CAD Exporter instance.

    Returns:
        Configured CAD exporter with metadata and caching
    """
    global _cad_exporter

    if _cad_exporter is None:
        _cad_exporter = CADExporter(
            outputs_dir="outputs",
            enable_cache=True,
        )
        logger.info("Initialized CADExporter")

    return _cad_exporter


def reset_dependencies() -> None:
    """
    Reset all global dependency instances.

    Useful for testing or when configuration changes.
    """
    global _llm_provider, _planner_agent, _generator_agent, _validator_agent
    global _orchestrator_agent, _freecad_executor, _pipeline_executor, _cad_exporter

    _llm_provider = None
    _planner_agent = None
    _generator_agent = None
    _validator_agent = None
    _orchestrator_agent = None
    _freecad_executor = None
    _pipeline_executor = None
    _cad_exporter = None

    logger.info("Reset all dependency instances")
