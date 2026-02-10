"""Tests for the Orchestrator Agent."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from ai_designer.agents.generator import GeneratorAgent
from ai_designer.agents.orchestrator import OrchestratorAgent
from ai_designer.agents.planner import PlannerAgent
from ai_designer.agents.validator import ValidatorAgent
from ai_designer.core.llm_provider import UnifiedLLMProvider
from ai_designer.schemas.design_state import DesignRequest, ExecutionStatus
from ai_designer.schemas.task_graph import TaskGraph, TaskNode
from ai_designer.schemas.validation import ValidationResult


class TestOrchestratorAgentInit:
    """Test OrchestratorAgent initialization."""

    def test_init_default_params(self):
        """Test initialization with default parameters."""
        mock_provider = MagicMock(spec=UnifiedLLMProvider)

        orchestrator = OrchestratorAgent(llm_provider=mock_provider)

        assert orchestrator.llm_provider == mock_provider
        assert orchestrator.max_iterations == 5
        assert orchestrator.enable_refinement is True
        assert isinstance(orchestrator.planner, PlannerAgent)
        assert isinstance(orchestrator.generator, GeneratorAgent)
        assert isinstance(orchestrator.validator, ValidatorAgent)

    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        mock_provider = MagicMock(spec=UnifiedLLMProvider)
        mock_planner = MagicMock(spec=PlannerAgent)
        mock_generator = MagicMock(spec=GeneratorAgent)
        mock_validator = MagicMock(spec=ValidatorAgent)

        orchestrator = OrchestratorAgent(
            llm_provider=mock_provider,
            planner=mock_planner,
            generator=mock_generator,
            validator=mock_validator,
            max_iterations=3,
            enable_refinement=False,
        )

        assert orchestrator.planner == mock_planner
        assert orchestrator.generator == mock_generator
        assert orchestrator.validator == mock_validator
        assert orchestrator.max_iterations == 3
        assert orchestrator.enable_refinement is False

    def test_init_invalid_max_iterations(self):
        """Test initialization with invalid max_iterations."""
        mock_provider = MagicMock(spec=UnifiedLLMProvider)

        with pytest.raises(ValueError, match="max_iterations must be between"):
            OrchestratorAgent(llm_provider=mock_provider, max_iterations=0)

        with pytest.raises(ValueError, match="max_iterations must be between"):
            OrchestratorAgent(llm_provider=mock_provider, max_iterations=11)


class TestOrchestratorAgentExecution:
    """Test OrchestratorAgent execution workflows."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mock LLM provider."""
        return MagicMock(spec=UnifiedLLMProvider)

    @pytest.fixture
    def mock_planner(self):
        """Create a mock Planner agent."""
        planner = MagicMock(spec=PlannerAgent)
        return planner

    @pytest.fixture
    def mock_generator(self):
        """Create a mock Generator agent."""
        generator = MagicMock(spec=GeneratorAgent)
        return generator

    @pytest.fixture
    def mock_validator(self):
        """Create a mock Validator agent."""
        validator = MagicMock(spec=ValidatorAgent)
        return validator

    @pytest.fixture
    def orchestrator(self, mock_provider, mock_planner, mock_generator, mock_validator):
        """Create an orchestrator with mocked agents."""
        return OrchestratorAgent(
            llm_provider=mock_provider,
            planner=mock_planner,
            generator=mock_generator,
            validator=mock_validator,
            max_iterations=3,
        )

    @pytest.fixture
    def design_request(self):
        """Create a sample design request."""
        return DesignRequest(user_prompt="Create a simple box 10x10x10mm")

    @pytest.fixture
    def simple_task_graph(self):
        """Create a simple task graph."""
        request_id = uuid4()
        graph = TaskGraph(request_id=request_id)

        task = TaskNode(
            task_id="task_1",
            operation_type="create_box",
            description="Create box",
            parameters={"length": 10.0, "width": 10.0, "height": 10.0},
        )
        graph.add_task(task)

        return graph

    @pytest.fixture
    def sample_scripts(self):
        """Sample generated scripts."""
        return {
            "task_1": """import FreeCAD
import Part

doc = FreeCAD.ActiveDocument
box = doc.addObject("Part::Box", "Box")
box.Length = 10.0
box.Width = 10.0
box.Height = 10.0
doc.recompute()
# RESULT: box"""
        }

    @pytest.mark.asyncio
    async def test_execute_success_first_iteration(
        self,
        orchestrator,
        mock_planner,
        mock_generator,
        mock_validator,
        design_request,
        simple_task_graph,
        sample_scripts,
    ):
        """Test successful execution on first iteration."""
        # Setup mocks
        mock_planner.plan = AsyncMock(return_value=simple_task_graph)
        mock_generator.generate = AsyncMock(return_value=sample_scripts)

        validation = ValidationResult(
            request_id=str(design_request.request_id),
            is_valid=True,
        )
        validation.overall_score = 0.95
        mock_validator.validate = AsyncMock(return_value=validation)

        # Execute
        state = await orchestrator.execute(design_request)

        # Verify
        assert state.status == ExecutionStatus.COMPLETED
        assert state.is_valid is True
        assert state.current_iteration == 1
        assert len(state.iterations) == 3  # Plan, Generate, Validate

        mock_planner.plan.assert_called_once()
        mock_generator.generate.assert_called_once()
        mock_validator.validate.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_refinement(
        self,
        orchestrator,
        mock_planner,
        mock_generator,
        mock_validator,
        design_request,
        simple_task_graph,
        sample_scripts,
    ):
        """Test execution with one refinement iteration."""
        # Setup mocks
        mock_planner.plan = AsyncMock(return_value=simple_task_graph)
        mock_planner.replan = AsyncMock(return_value=simple_task_graph)
        mock_generator.generate = AsyncMock(return_value=sample_scripts)

        # First validation: needs refinement
        validation_1 = ValidationResult(
            request_id=str(design_request.request_id),
            is_valid=False,
        )
        validation_1.overall_score = 0.7
        validation_1.should_refine = True
        validation_1.refinement_suggestions = ["Add fillet"]

        # Second validation: passes
        validation_2 = ValidationResult(
            request_id=str(design_request.request_id),
            is_valid=True,
        )
        validation_2.overall_score = 0.9

        mock_validator.validate = AsyncMock(side_effect=[validation_1, validation_2])

        # Execute
        state = await orchestrator.execute(design_request)

        # Verify
        assert state.status == ExecutionStatus.COMPLETED
        assert state.is_valid is True
        assert state.current_iteration == 2
        assert len(state.iterations) == 6  # 2 * (Plan, Generate, Validate)

        mock_planner.plan.assert_called_once()
        mock_planner.replan.assert_called_once()
        assert mock_generator.generate.call_count == 2
        assert mock_validator.validate.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_max_iterations_exceeded(
        self,
        orchestrator,
        mock_planner,
        mock_generator,
        mock_validator,
        design_request,
        simple_task_graph,
        sample_scripts,
    ):
        """Test execution when max iterations is exceeded."""
        # Setup mocks
        mock_planner.plan = AsyncMock(return_value=simple_task_graph)
        mock_planner.replan = AsyncMock(return_value=simple_task_graph)
        mock_generator.generate = AsyncMock(return_value=sample_scripts)

        # Always return needs refinement
        validation = ValidationResult(
            request_id=str(design_request.request_id),
            is_valid=False,
        )
        validation.overall_score = 0.7
        validation.should_refine = True
        validation.refinement_suggestions = ["Improve design"]

        mock_validator.validate = AsyncMock(return_value=validation)

        # Execute
        state = await orchestrator.execute(design_request)

        # Verify - should stop at max iterations (3)
        assert state.status == ExecutionStatus.FAILED
        assert state.is_valid is False
        assert state.current_iteration == 3
        assert "Maximum iterations" in state.error_message
        assert mock_validator.validate.call_count == 3

    @pytest.mark.asyncio
    async def test_execute_planning_failure(
        self,
        orchestrator,
        mock_planner,
        design_request,
    ):
        """Test execution when planning fails."""
        # Planner raises exception
        mock_planner.plan = AsyncMock(side_effect=Exception("Planning error"))

        # Execute
        state = await orchestrator.execute(design_request)

        # Verify
        assert state.status == ExecutionStatus.FAILED
        assert "Planning failed" in state.error_message
        assert state.current_iteration == 1
        assert len(state.iterations) == 1

    @pytest.mark.asyncio
    async def test_execute_generation_failure(
        self,
        orchestrator,
        mock_planner,
        mock_generator,
        design_request,
        simple_task_graph,
    ):
        """Test execution when generation fails."""
        mock_planner.plan = AsyncMock(return_value=simple_task_graph)
        mock_generator.generate = AsyncMock(side_effect=Exception("Generation error"))

        # Execute
        state = await orchestrator.execute(design_request)

        # Verify
        assert state.status == ExecutionStatus.FAILED
        assert "Generation failed" in state.error_message

    @pytest.mark.asyncio
    async def test_execute_validation_failure_no_refinement(
        self,
        orchestrator,
        mock_planner,
        mock_generator,
        mock_validator,
        design_request,
        simple_task_graph,
        sample_scripts,
    ):
        """Test execution when validation fails and refinement not possible."""
        mock_planner.plan = AsyncMock(return_value=simple_task_graph)
        mock_generator.generate = AsyncMock(return_value=sample_scripts)

        # Validation fails, no refinement possible
        validation = ValidationResult(
            request_id=str(design_request.request_id),
            is_valid=False,
        )
        validation.overall_score = 0.3
        validation.should_refine = False  # Too low to refine

        mock_validator.validate = AsyncMock(return_value=validation)

        # Execute
        state = await orchestrator.execute(design_request)

        # Verify
        assert state.status == ExecutionStatus.FAILED
        assert "validation failed" in state.error_message
        assert state.current_iteration == 1
        assert mock_validator.validate.call_count == 1

    @pytest.mark.asyncio
    async def test_execute_with_execution_callback(
        self,
        orchestrator,
        mock_planner,
        mock_generator,
        mock_validator,
        design_request,
        simple_task_graph,
        sample_scripts,
    ):
        """Test execution with FreeCAD script execution callback."""
        # Setup mocks
        mock_planner.plan = AsyncMock(return_value=simple_task_graph)
        mock_generator.generate = AsyncMock(return_value=sample_scripts)

        validation = ValidationResult(
            request_id=str(design_request.request_id),
            is_valid=True,
        )
        validation.overall_score = 0.95
        mock_validator.validate = AsyncMock(return_value=validation)

        # Mock execution callback
        execution_result = {
            "success": True,
            "object_count": 1,
            "total_volume": 1000.0,
        }
        mock_callback = AsyncMock(return_value=execution_result)

        # Execute
        state = await orchestrator.execute(
            design_request, execution_callback=mock_callback
        )

        # Verify
        assert state.status == ExecutionStatus.COMPLETED
        mock_callback.assert_called_once_with(sample_scripts)

        # Validator should receive execution result
        call_args = mock_validator.validate.call_args
        assert call_args[0][3] == execution_result  # 4th positional arg


class TestOrchestratorAgentHelpers:
    """Test OrchestratorAgent helper methods."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mock LLM provider."""
        return MagicMock(spec=UnifiedLLMProvider)

    @pytest.fixture
    def orchestrator(self, mock_provider):
        """Create an orchestrator."""
        mock_planner = MagicMock(spec=PlannerAgent)
        mock_generator = MagicMock(spec=GeneratorAgent)
        mock_validator = MagicMock(spec=ValidatorAgent)

        return OrchestratorAgent(
            llm_provider=mock_provider,
            planner=mock_planner,
            generator=mock_generator,
            validator=mock_validator,
        )

    @pytest.mark.asyncio
    async def test_execute_scripts_success(self, orchestrator):
        """Test script execution with successful callback."""
        scripts = {"task_1": "import FreeCAD"}
        result = {"success": True, "object_count": 1}

        callback = AsyncMock(return_value=result)

        execution_result = await orchestrator._execute_scripts(scripts, callback)

        assert execution_result == result
        callback.assert_called_once_with(scripts)

    @pytest.mark.asyncio
    async def test_execute_scripts_failure(self, orchestrator):
        """Test script execution with failing callback."""
        scripts = {"task_1": "import FreeCAD"}

        callback = AsyncMock(side_effect=Exception("Execution failed"))

        execution_result = await orchestrator._execute_scripts(scripts, callback)

        assert execution_result is not None
        assert "error" in execution_result
        assert execution_result["success"] is False
