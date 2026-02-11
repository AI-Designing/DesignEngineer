"""
Tests for LangGraph orchestration pipeline.

Tests cover:
- Pipeline construction
- State management
- Node execution
- Conditional routing
- Iteration limits
- Error handling
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from ai_designer.agents.generator import GeneratorAgent
from ai_designer.agents.planner import PlannerAgent
from ai_designer.agents.validator import ValidatorAgent
from ai_designer.orchestration.pipeline import PipelineExecutor, build_design_pipeline
from ai_designer.orchestration.routing import (
    ROUTE_FAIL,
    ROUTE_REFINE,
    ROUTE_REPLAN,
    ROUTE_SUCCESS,
    route_after_validation,
)
from ai_designer.orchestration.state import PipelineState
from ai_designer.schemas.design_state import DesignRequest, DesignState, ExecutionStatus
from ai_designer.schemas.task_graph import TaskGraph
from ai_designer.schemas.validation import ValidationResult


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider."""
    provider = MagicMock()
    provider.complete_async = AsyncMock(return_value="Mock response")
    return provider


@pytest.fixture
def mock_planner(mock_llm_provider):
    """Mock planner agent."""
    planner = PlannerAgent(llm_provider=mock_llm_provider)
    planner.plan = AsyncMock()
    return planner


@pytest.fixture
def mock_generator(mock_llm_provider):
    """Mock generator agent."""
    generator = GeneratorAgent(llm_provider=mock_llm_provider)
    generator.generate = AsyncMock()
    return generator


@pytest.fixture
def mock_validator(mock_llm_provider):
    """Mock validator agent."""
    validator = ValidatorAgent(llm_provider=mock_llm_provider)
    validator.validate = AsyncMock()
    return validator


@pytest.fixture
def design_request():
    """Sample design request."""
    return DesignRequest(
        request_id=uuid4(),
        user_prompt="Create a 10x10x10mm cube",
    )


@pytest.fixture
def sample_task_graph(design_request):
    """Sample task graph."""
    from ai_designer.schemas.task_graph import TaskNode, TaskPriority

    return TaskGraph(
        request_id=design_request.request_id,
        nodes={
            "task_1": TaskNode(
                task_id="task_1",
                description="Create cube",
                priority=TaskPriority.MEDIUM,
                estimated_duration_minutes=5,
            )
        },
        edges=[],
        total_tasks=1,
    )


@pytest.fixture
def sample_scripts():
    """Sample generated scripts."""
    return {
        "main": "import FreeCAD\nBox = FreeCAD.ActiveDocument.addObject('Part::Box', 'Box')",
    }


class TestPipelineState:
    """Test PipelineState management."""

    def test_create_from_design_state(self):
        """Test creating pipeline state from design state."""
        design_state = DesignState(
            request_id=uuid4(),
            user_prompt="Test prompt",
            max_iterations=5,
        )

        pipeline_state = PipelineState.from_design_state(design_state)

        assert pipeline_state.design_state == design_state
        assert pipeline_state.workflow_iteration == 0
        assert pipeline_state.max_workflow_iterations == 5
        assert pipeline_state.current_node is None

    def test_enter_exit_node(self):
        """Test node entry/exit tracking."""
        design_state = DesignState(
            request_id=uuid4(),
            user_prompt="Test",
        )
        pipeline_state = PipelineState.from_design_state(design_state)

        # Enter node
        pipeline_state.enter_node("planner")
        assert pipeline_state.current_node == "planner"
        assert pipeline_state.previous_node is None
        assert "planner" in pipeline_state.node_history
        assert pipeline_state.node_start_time is not None

        # Exit node
        pipeline_state.exit_node()
        assert "planner" in pipeline_state.node_durations
        assert pipeline_state.node_durations["planner"] >= 0
        assert pipeline_state.node_start_time is None

    def test_iteration_tracking(self):
        """Test iteration increment."""
        design_state = DesignState(
            request_id=uuid4(),
            user_prompt="Test",
        )
        pipeline_state = PipelineState.from_design_state(design_state)

        assert pipeline_state.workflow_iteration == 0

        pipeline_state.increment_iteration()
        assert pipeline_state.workflow_iteration == 1
        assert pipeline_state.design_state.current_iteration == 1

    def test_has_exceeded_iterations(self):
        """Test iteration limit checking."""
        design_state = DesignState(
            request_id=uuid4(),
            user_prompt="Test",
        )
        pipeline_state = PipelineState.from_design_state(design_state, max_iterations=3)

        assert not pipeline_state.has_exceeded_iterations()

        pipeline_state.workflow_iteration = 3
        assert pipeline_state.has_exceeded_iterations()

        pipeline_state.workflow_iteration = 2
        assert not pipeline_state.has_exceeded_iterations()

    def test_record_error(self):
        """Test error recording."""
        design_state = DesignState(
            request_id=uuid4(),
            user_prompt="Test",
        )
        pipeline_state = PipelineState.from_design_state(design_state)

        pipeline_state.record_error("Test error", "planner")

        assert pipeline_state.error_count == 1
        assert pipeline_state.last_error == "Test error"
        assert pipeline_state.retry_count["planner"] == 1

        # Record another error
        pipeline_state.record_error("Another error", "planner")
        assert pipeline_state.error_count == 2
        assert pipeline_state.retry_count["planner"] == 2


class TestRouting:
    """Test conditional routing logic."""

    def test_route_success(self):
        """Test routing to success when score >= 0.8."""
        request_id = uuid4()
        design_state = DesignState(request_id=request_id, user_prompt="Test")
        pipeline_state = PipelineState.from_design_state(design_state)
        pipeline_state.validation_result = ValidationResult(
            request_id=str(request_id),
            is_valid=True,
            overall_score=0.9,
            dimensional_scores={},
            issues=[],
            refinement_suggestions=[],
            should_refine=False,
        )

        decision = route_after_validation(pipeline_state)
        assert decision == ROUTE_SUCCESS
        assert "passed" in pipeline_state.routing_reason.lower()

    def test_route_refine(self):
        """Test routing to refine when 0.4 <= score < 0.8."""
        request_id = uuid4()
        design_state = DesignState(request_id=request_id, user_prompt="Test")
        pipeline_state = PipelineState.from_design_state(design_state)
        pipeline_state.validation_result = ValidationResult(
            request_id=str(request_id),
            is_valid=False,
            overall_score=0.6,
            dimensional_scores={},
            issues=[],
            refinement_suggestions=["Improve quality"],
            should_refine=True,
        )

        decision = route_after_validation(pipeline_state)
        assert decision == ROUTE_REFINE
        assert "refinement" in pipeline_state.routing_reason.lower()

    def test_route_replan(self):
        """Test routing to replan when 0.2 <= score < 0.4."""
        request_id = uuid4()
        design_state = DesignState(request_id=request_id, user_prompt="Test")
        pipeline_state = PipelineState.from_design_state(design_state)
        pipeline_state.validation_result = ValidationResult(
            request_id=str(request_id),
            is_valid=False,
            overall_score=0.3,
            dimensional_scores={},
            issues=["Major structural issue"],
            refinement_suggestions=[],
            should_refine=False,
        )

        decision = route_after_validation(pipeline_state)
        assert decision == ROUTE_REPLAN
        assert "replanning" in pipeline_state.routing_reason.lower()

    def test_route_fail(self):
        """Test routing to fail when score < 0.2."""
        request_id = uuid4()
        design_state = DesignState(request_id=request_id, user_prompt="Test")
        pipeline_state = PipelineState.from_design_state(design_state)
        pipeline_state.validation_result = ValidationResult(
            request_id=str(request_id),
            is_valid=False,
            overall_score=0.1,
            dimensional_scores={},
            issues=["Unrecoverable error"],
            refinement_suggestions=[],
            should_refine=False,
        )

        decision = route_after_validation(pipeline_state)
        assert decision == ROUTE_FAIL
        assert "failed" in pipeline_state.routing_reason.lower()

    def test_route_fail_max_iterations(self):
        """Test routing to fail when max iterations exceeded."""
        request_id = uuid4()
        design_state = DesignState(request_id=request_id, user_prompt="Test")
        pipeline_state = PipelineState.from_design_state(design_state, max_iterations=3)
        pipeline_state.workflow_iteration = 3
        pipeline_state.validation_result = ValidationResult(
            request_id=str(request_id),
            is_valid=False,
            overall_score=0.6,  # Would normally refine
            dimensional_scores={},
            issues=[],
            refinement_suggestions=["Improve"],
            should_refine=True,
        )

        decision = route_after_validation(pipeline_state)
        assert decision == ROUTE_FAIL
        assert "iterations" in pipeline_state.routing_reason.lower()

    def test_route_fail_no_validation(self):
        """Test routing to fail when no validation result."""
        design_state = DesignState(request_id=uuid4(), user_prompt="Test")
        pipeline_state = PipelineState.from_design_state(design_state)
        pipeline_state.validation_result = None

        decision = route_after_validation(pipeline_state)
        assert decision == ROUTE_FAIL


class TestPipelineConstruction:
    """Test pipeline construction and configuration."""

    def test_build_pipeline(self, mock_planner, mock_generator, mock_validator):
        """Test building pipeline graph."""
        pipeline = build_design_pipeline(
            planner=mock_planner,
            generator=mock_generator,
            validator=mock_validator,
            max_iterations=5,
        )

        assert pipeline is not None
        # Pipeline should be compiled and ready

    def test_pipeline_executor_initialization(
        self, mock_planner, mock_generator, mock_validator
    ):
        """Test PipelineExecutor initialization."""
        executor = PipelineExecutor(
            planner=mock_planner,
            generator=mock_generator,
            validator=mock_validator,
            max_iterations=3,
        )

        assert executor.planner == mock_planner
        assert executor.generator == mock_generator
        assert executor.validator == mock_validator
        assert executor.max_iterations == 3
        assert executor.pipeline is not None


@pytest.mark.asyncio
class TestPipelineExecution:
    """Test end-to-end pipeline execution."""

    async def test_successful_execution(
        self,
        mock_planner,
        mock_generator,
        mock_validator,
        design_request,
        sample_task_graph,
        sample_scripts,
    ):
        """Test successful pipeline execution without iteration."""
        # Setup mocks
        mock_planner.plan.return_value = sample_task_graph
        mock_generator.generate.return_value = sample_scripts
        mock_validator.validate.return_value = ValidationResult(
            request_id=str(design_request.request_id),
            is_valid=True,
            overall_score=0.9,
            should_refine=False,
        )

        # Create and execute pipeline
        executor = PipelineExecutor(
            planner=mock_planner,
            generator=mock_generator,
            validator=mock_validator,
            max_iterations=5,
        )

        result = await executor.execute(design_request)

        # Verify execution
        assert result.status == ExecutionStatus.COMPLETED
        assert result.is_valid
        assert mock_planner.plan.call_count == 1
        assert mock_generator.generate.call_count == 1
        assert mock_validator.validate.call_count == 1

    async def test_refinement_loop(
        self,
        mock_planner,
        mock_generator,
        mock_validator,
        design_request,
        sample_task_graph,
        sample_scripts,
    ):
        """Test pipeline with refinement iteration."""
        # Setup mocks - fail first, then succeed
        mock_planner.plan.return_value = sample_task_graph
        mock_generator.generate.return_value = sample_scripts

        # First validation: needs refinement
        validation_1 = ValidationResult(
            request_id=str(design_request.request_id),
            is_valid=False,
            overall_score=0.6,
            should_refine=True,
            refinement_suggestions=["Improve quality"],
        )

        # Second validation: success
        validation_2 = ValidationResult(
            request_id=str(design_request.request_id),
            is_valid=True,
            overall_score=0.9,
            should_refine=False,
        )

        mock_validator.validate.side_effect = [validation_1, validation_2]

        # Execute pipeline
        executor = PipelineExecutor(
            planner=mock_planner,
            generator=mock_generator,
            validator=mock_validator,
            max_iterations=5,
        )

        result = await executor.execute(design_request)

        # Should have refined once
        assert result.status == ExecutionStatus.COMPLETED
        assert result.is_valid
        assert mock_validator.validate.call_count == 2
        assert mock_generator.generate.call_count == 2

    async def test_max_iterations_exceeded(
        self,
        mock_planner,
        mock_generator,
        mock_validator,
        design_request,
        sample_task_graph,
        sample_scripts,
    ):
        """Test pipeline stops at max iterations."""
        # Setup mocks - always need refinement
        mock_planner.plan.return_value = sample_task_graph
        mock_generator.generate.return_value = sample_scripts
        mock_validator.validate.return_value = ValidationResult(
            request_id=str(design_request.request_id),
            is_valid=False,
            overall_score=0.6,
            should_refine=True,
            refinement_suggestions=["Keep trying"],
        )

        # Execute with low max iterations
        executor = PipelineExecutor(
            planner=mock_planner,
            generator=mock_generator,
            validator=mock_validator,
            max_iterations=2,
        )

        result = await executor.execute(design_request)

        # Should fail after max iterations
        assert result.status == ExecutionStatus.FAILED
        assert not result.is_valid
        assert (
            "iterations" in result.error_message.lower()
            or result.error_message is not None
        )

    async def test_pipeline_error_handling(
        self,
        mock_planner,
        mock_generator,
        mock_validator,
        design_request,
    ):
        """Test pipeline handles errors gracefully."""
        # Setup planner to fail
        mock_planner.plan.side_effect = Exception("Planning failed")

        executor = PipelineExecutor(
            planner=mock_planner,
            generator=mock_generator,
            validator=mock_validator,
            max_iterations=5,
        )

        result = await executor.execute(design_request)

        assert result.status == ExecutionStatus.FAILED
        assert result.error_message is not None
