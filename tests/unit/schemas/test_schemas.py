"""
Unit tests for Pydantic v2 schemas.
"""

from datetime import datetime
from uuid import UUID

import pytest

from ai_designer.schemas.design_state import (
    AgentType,
    DesignRequest,
    DesignState,
    ExecutionStatus,
    IterationState,
)
from ai_designer.schemas.task_graph import (
    TaskDependency,
    TaskGraph,
    TaskNode,
    TaskStatus,
)
from ai_designer.schemas.validation import (
    GeometricValidation,
    LLMReviewResult,
    SemanticValidation,
    ValidationResult,
    ValidationSeverity,
)


class TestDesignRequest:
    """Test DesignRequest schema."""

    def test_create_valid_request(self):
        """Test creating a valid design request."""
        request = DesignRequest(user_prompt="Create a cube with 10mm sides")
        assert isinstance(request.request_id, UUID)
        assert request.user_prompt == "Create a cube with 10mm sides"
        assert isinstance(request.timestamp, datetime)

    def test_prompt_validation(self):
        """Test prompt validation."""
        with pytest.raises(ValueError, match="at least 5 characters"):
            DesignRequest(user_prompt="cube")

    def test_immutable_request(self):
        """Test that request is immutable (frozen)."""
        request = DesignRequest(user_prompt="Create a cube")
        with pytest.raises(Exception):  # Pydantic v2 raises ValidationError
            request.user_prompt = "Modified"


class TestDesignState:
    """Test DesignState schema."""

    def test_create_design_state(self):
        """Test creating a design state."""
        request = DesignRequest(user_prompt="Create a cylinder")
        state = DesignState(
            request_id=request.request_id,
            user_prompt=request.user_prompt,
        )
        assert state.status == ExecutionStatus.PENDING
        assert state.current_iteration == 0
        assert len(state.iterations) == 0

    def test_add_iteration(self):
        """Test adding iterations."""
        request = DesignRequest(user_prompt="Create a sphere")
        state = DesignState(
            request_id=request.request_id, user_prompt=request.user_prompt
        )

        iteration = state.add_iteration(AgentType.PLANNER, {"plan": "step1, step2"})
        assert isinstance(iteration, IterationState)
        assert iteration.iteration_number == 1
        assert iteration.agent == AgentType.PLANNER
        assert state.current_iteration == 1
        assert len(state.iterations) == 1

    def test_mark_completed(self):
        """Test marking state as completed."""
        request = DesignRequest(user_prompt="Create a box")
        state = DesignState(
            request_id=request.request_id, user_prompt=request.user_prompt
        )

        state.mark_completed()
        assert state.status == ExecutionStatus.COMPLETED
        assert state.completed_at is not None

    def test_mark_failed(self):
        """Test marking state as failed."""
        request = DesignRequest(user_prompt="Create invalid")
        state = DesignState(
            request_id=request.request_id, user_prompt=request.user_prompt
        )

        state.mark_failed("Validation error", {"code": 500})
        assert state.status == ExecutionStatus.FAILED
        assert state.error_message == "Validation error"
        assert state.error_details == {"code": 500}

    def test_should_continue_iterating(self):
        """Test iteration continuation logic."""
        request = DesignRequest(user_prompt="Create a cone")
        state = DesignState(
            request_id=request.request_id,
            user_prompt=request.user_prompt,
            max_iterations=3,
        )

        assert state.should_continue_iterating() is True

        state.current_iteration = 3
        assert state.should_continue_iterating() is False

        state.current_iteration = 1
        state.mark_completed()
        assert state.should_continue_iterating() is False


class TestTaskGraph:
    """Test TaskGraph schema."""

    def test_create_task_graph(self):
        """Test creating a task graph."""
        request = DesignRequest(user_prompt="Test prompt")
        graph = TaskGraph(request_id=request.request_id)

        assert isinstance(graph.graph_id, str)
        assert graph.total_tasks == 0
        assert len(graph.nodes) == 0

    def test_add_task(self):
        """Test adding tasks."""
        request = DesignRequest(user_prompt="Test prompt")
        graph = TaskGraph(request_id=request.request_id)

        task1 = TaskNode(description="Create sketch", operation_type="sketch")
        graph.add_task(task1)

        assert graph.total_tasks == 1
        assert task1.task_id in graph.nodes

    def test_add_dependency(self):
        """Test adding dependencies."""
        request = DesignRequest(user_prompt="Test prompt")
        graph = TaskGraph(request_id=request.request_id)

        task1 = TaskNode(description="Sketch", operation_type="sketch")
        task2 = TaskNode(description="Extrude", operation_type="extrude")
        graph.add_task(task1)
        graph.add_task(task2)

        graph.add_dependency(task1.task_id, task2.task_id)
        assert task1.task_id in graph.nodes[task2.task_id].depends_on

    def test_get_ready_tasks(self):
        """Test getting ready tasks."""
        request = DesignRequest(user_prompt="Test prompt")
        graph = TaskGraph(request_id=request.request_id)

        task1 = TaskNode(description="Sketch", operation_type="sketch")
        task2 = TaskNode(description="Extrude", operation_type="extrude")
        graph.add_task(task1)
        graph.add_task(task2)
        graph.add_dependency(task1.task_id, task2.task_id)

        ready = graph.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].task_id == task1.task_id

        task1.mark_completed()
        ready = graph.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].task_id == task2.task_id

    def test_execution_order(self):
        """Test topological sort for execution order."""
        request = DesignRequest(user_prompt="Test prompt")
        graph = TaskGraph(request_id=request.request_id)

        task1 = TaskNode(description="Sketch", operation_type="sketch")
        task2 = TaskNode(description="Extrude", operation_type="extrude")
        task3 = TaskNode(description="Fillet", operation_type="fillet")
        graph.add_task(task1)
        graph.add_task(task2)
        graph.add_task(task3)

        graph.add_dependency(task1.task_id, task2.task_id)
        graph.add_dependency(task2.task_id, task3.task_id)

        order = graph.get_execution_order()
        assert len(order) == 3
        assert order[0] == [task1.task_id]
        assert order[1] == [task2.task_id]
        assert order[2] == [task3.task_id]

    def test_has_cycles(self):
        """Test cycle detection."""
        request = DesignRequest(user_prompt="Test prompt")
        graph = TaskGraph(request_id=request.request_id)

        task1 = TaskNode(description="Task1", operation_type="op1")
        task2 = TaskNode(description="Task2", operation_type="op2")
        graph.add_task(task1)
        graph.add_task(task2)

        graph.add_dependency(task1.task_id, task2.task_id)
        assert graph.has_cycles() is False

        # Create cycle
        graph.add_dependency(task2.task_id, task1.task_id)
        assert graph.has_cycles() is True


class TestValidation:
    """Test validation schemas."""

    def test_geometric_validation(self):
        """Test geometric validation."""
        geo = GeometricValidation(
            is_valid=True,
            has_solid_bodies=True,
            body_count=1,
            total_volume=1000.0,
        )
        assert geo.is_valid is True
        assert geo.body_count == 1

    def test_semantic_validation(self):
        """Test semantic validation."""
        sem = SemanticValidation(
            is_valid=True,
            confidence_score=0.95,
            requirements_met=["10mm cube"],
            detected_features=["Box", "Sketch"],
        )
        assert sem.is_valid is True
        assert sem.confidence_score == 0.95

    def test_llm_review(self):
        """Test LLM review result."""
        review = LLMReviewResult(
            overall_assessment="Good design",
            quality_score=0.8,
            strengths=["Clean code", "Efficient"],
            weaknesses=["Missing comments"],
        )
        assert review.quality_score == 0.8
        assert len(review.strengths) == 2

    def test_validation_result(self):
        """Test complete validation result."""
        result = ValidationResult(
            request_id="test-123",
            is_valid=True,
            geometric=GeometricValidation(is_valid=True),
            semantic=SemanticValidation(is_valid=True, confidence_score=0.9),
        )
        assert result.is_valid is True

    def test_add_issue(self):
        """Test adding issues."""
        result = ValidationResult(request_id="test-123", is_valid=False)
        result.add_issue(ValidationSeverity.ERROR, "Invalid geometry", "geometric")

        assert len(result.all_issues) == 1
        assert result.all_issues[0]["severity"] == "error"
        assert result.all_issues[0]["source"] == "geometric"

    def test_calculate_overall_score(self):
        """Test overall score calculation."""
        result = ValidationResult(
            request_id="test-123",
            is_valid=True,
            geometric_score=0.8,
            semantic_score=0.9,
        )
        result.llm_review = LLMReviewResult(
            overall_assessment="Good", quality_score=0.85, strengths=[], weaknesses=[]
        )

        score = result.calculate_overall_score()
        assert 0.8 <= score <= 0.9  # Weighted average
        assert result.overall_score == score

    def test_has_critical_issues(self):
        """Test critical issue detection."""
        result = ValidationResult(request_id="test-123", is_valid=False)
        result.add_issue(ValidationSeverity.WARNING, "Minor issue", "test")
        assert result.has_critical_issues() is False

        result.add_issue(ValidationSeverity.CRITICAL, "Fatal error", "test")
        assert result.has_critical_issues() is True
