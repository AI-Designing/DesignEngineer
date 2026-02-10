"""Unit tests for PlannerAgent.

Tests cover:
- Task graph generation from natural language
- JSON response parsing and validation
- DAG validation and cycle detection
- Replanning with feedback
- Error handling and retries
- LLM provider integration
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from ai_designer.agents.planner import PlannerAgent
from ai_designer.core.llm_provider import LLMResponse, UnifiedLLMProvider
from ai_designer.schemas.design_state import AgentType, DesignRequest
from ai_designer.schemas.task_graph import TaskGraph, TaskStatus


class TestPlannerAgentInit:
    """Test PlannerAgent initialization."""

    def test_init_default_params(self):
        """Test initialization with default parameters."""
        mock_provider = MagicMock(spec=UnifiedLLMProvider)
        planner = PlannerAgent(llm_provider=mock_provider)

        assert planner.llm_provider is mock_provider
        assert planner.agent_type == AgentType.PLANNER
        assert planner.default_temperature == 0.3
        assert planner.max_retries == 3

    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        mock_provider = MagicMock(spec=UnifiedLLMProvider)
        planner = PlannerAgent(
            llm_provider=mock_provider,
            temperature=0.7,
            max_retries=5,
        )

        assert planner.default_temperature == 0.7
        assert planner.max_retries == 5

    def test_init_invalid_temperature(self):
        """Test initialization with invalid temperature raises ValueError."""
        mock_provider = MagicMock(spec=UnifiedLLMProvider)

        with pytest.raises(ValueError, match="Temperature must be in"):
            PlannerAgent(llm_provider=mock_provider, temperature=1.5)

        with pytest.raises(ValueError, match="Temperature must be in"):
            PlannerAgent(llm_provider=mock_provider, temperature=-0.1)


class TestPlannerAgentPlanning:
    """Test PlannerAgent task graph generation."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mock LLM provider."""
        mock = MagicMock(spec=UnifiedLLMProvider)
        mock.default_model = "gpt-4o"
        return mock

    @pytest.fixture
    def planner(self, mock_provider):
        """Create a PlannerAgent instance."""
        return PlannerAgent(llm_provider=mock_provider)

    @pytest.fixture
    def design_request(self):
        """Create a sample design request."""
        return DesignRequest(user_prompt="Create a box 10x10x10mm with a 2mm hole")

    @pytest.fixture
    def valid_llm_response(self):
        """Create a valid LLM response with task graph JSON."""
        response_json = {
            "tasks": [
                {
                    "id": "task_1",
                    "operation": "create_box",
                    "description": "Create base box 10x10x10mm",
                    "parameters": {"length": 10.0, "width": 10.0, "height": 10.0},
                    "status": "pending",
                },
                {
                    "id": "task_2",
                    "operation": "create_cylinder",
                    "description": "Create hole cylinder",
                    "parameters": {"radius": 1.0, "height": 12.0},
                    "status": "pending",
                },
                {
                    "id": "task_3",
                    "operation": "boolean_cut",
                    "description": "Cut hole from box",
                    "parameters": {
                        "base_task_id": "task_1",
                        "tool_task_id": "task_2",
                    },
                    "status": "pending",
                },
            ],
            "dependencies": [
                {"from_task_id": "task_1", "to_task_id": "task_3"},
                {"from_task_id": "task_2", "to_task_id": "task_3"},
            ],
        }

        return LLMResponse(
            content=json.dumps(response_json),
            model="gpt-4",
            provider="openai",
            usage={"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300},
            finish_reason="stop",
        )

    @pytest.mark.asyncio
    async def test_plan_success(
        self, planner, mock_provider, design_request, valid_llm_response
    ):
        """Test successful task graph generation."""
        mock_provider.generate = AsyncMock(return_value=valid_llm_response)

        task_graph = await planner.plan(design_request)

        # Verify task graph structure
        assert isinstance(task_graph, TaskGraph)
        assert len(task_graph.nodes) == 3
        assert len(task_graph.edges) == 2

        # Verify tasks
        assert "task_1" in task_graph.nodes
        assert "task_2" in task_graph.nodes
        assert "task_3" in task_graph.nodes

        task_1 = task_graph.nodes["task_1"]
        assert task_1.operation_type == "create_box"
        assert task_1.parameters == {"length": 10.0, "width": 10.0, "height": 10.0}
        assert task_1.status == TaskStatus.PENDING

        # Verify dependencies
        ready_tasks = task_graph.get_ready_tasks()
        ready_task_ids = [task.task_id for task in ready_tasks]
        assert "task_1" in ready_task_ids
        assert "task_2" in ready_task_ids
        assert "task_3" not in ready_task_ids  # Has dependencies

        # Verify LLM was called
        mock_provider.generate.assert_called_once()
        call_args = mock_provider.generate.call_args[0][0]
        assert call_args.temperature == 0.3
        assert len(call_args.messages) == 2

    @pytest.mark.asyncio
    async def test_plan_with_custom_temperature(
        self, planner, mock_provider, design_request, valid_llm_response
    ):
        """Test planning with custom temperature."""
        mock_provider.generate = AsyncMock(return_value=valid_llm_response)

        await planner.plan(design_request, temperature=0.8)

        call_args = mock_provider.generate.call_args[0][0]
        assert call_args.temperature == 0.8

    @pytest.mark.asyncio
    async def test_plan_with_markdown_response(
        self, planner, mock_provider, design_request
    ):
        """Test parsing LLM response wrapped in markdown code blocks."""
        response_json = {
            "tasks": [
                {
                    "id": "task_1",
                    "operation": "create_box",
                    "description": "Test box",
                    "parameters": {"length": 10.0},
                    "status": "pending",
                }
            ],
            "dependencies": [],
        }

        markdown_response = LLMResponse(
            content=f"```json\n{json.dumps(response_json)}\n```",
            model="gpt-4",
            provider="openai",
            usage={"prompt_tokens": 50, "completion_tokens": 100, "total_tokens": 150},
            finish_reason="stop",
        )

        mock_provider.generate = AsyncMock(return_value=markdown_response)

        task_graph = await planner.plan(design_request)

        assert len(task_graph.nodes) == 1
        assert "task_1" in task_graph.nodes

    @pytest.mark.asyncio
    async def test_plan_invalid_json(self, planner, mock_provider, design_request):
        """Test handling of invalid JSON response."""
        invalid_response = LLMResponse(
            content="This is not valid JSON {invalid}",
            model="gpt-4",
            provider="openai",
            usage={"prompt_tokens": 50, "completion_tokens": 20, "total_tokens": 70},
            finish_reason="stop",
        )

        mock_provider.generate = AsyncMock(return_value=invalid_response)

        with pytest.raises(RuntimeError, match="Failed to generate valid task graph"):
            await planner.plan(design_request)

        # Should retry max_retries times
        assert mock_provider.generate.call_count == 3

    @pytest.mark.asyncio
    async def test_plan_missing_tasks_field(
        self, planner, mock_provider, design_request
    ):
        """Test handling of response missing 'tasks' field."""
        invalid_response = LLMResponse(
            content=json.dumps({"dependencies": []}),
            model="gpt-4",
            provider="openai",
            usage={"prompt_tokens": 50, "completion_tokens": 20, "total_tokens": 70},
            finish_reason="stop",
        )

        mock_provider.generate = AsyncMock(return_value=invalid_response)

        with pytest.raises(RuntimeError, match="Failed to generate valid task graph"):
            await planner.plan(design_request)

    @pytest.mark.asyncio
    async def test_plan_with_cycle(self, planner, mock_provider, design_request):
        """Test detection of cyclic dependencies."""
        cyclic_response = {
            "tasks": [
                {
                    "id": "task_1",
                    "operation": "create_box",
                    "description": "Box",
                    "status": "pending",
                },
                {
                    "id": "task_2",
                    "operation": "create_cylinder",
                    "description": "Cylinder",
                    "status": "pending",
                },
            ],
            "dependencies": [
                {"from_task_id": "task_1", "to_task_id": "task_2"},
                {"from_task_id": "task_2", "to_task_id": "task_1"},  # Cycle!
            ],
        }

        cyclic_llm_response = LLMResponse(
            content=json.dumps(cyclic_response),
            model="gpt-4",
            provider="openai",
            usage={"prompt_tokens": 50, "completion_tokens": 100, "total_tokens": 150},
            finish_reason="stop",
        )

        mock_provider.generate = AsyncMock(return_value=cyclic_llm_response)

        with pytest.raises(RuntimeError, match="Failed to generate valid task graph"):
            await planner.plan(design_request)


class TestPlannerAgentReplanning:
    """Test PlannerAgent replanning functionality."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mock LLM provider."""
        mock = MagicMock(spec=UnifiedLLMProvider)
        mock.default_model = "gpt-4o"
        return mock

    @pytest.fixture
    def planner(self, mock_provider):
        """Create a PlannerAgent instance."""
        return PlannerAgent(llm_provider=mock_provider)

    @pytest.fixture
    def design_request(self):
        """Create a sample design request."""
        return DesignRequest(user_prompt="Create a box with a hole")

    @pytest.fixture
    def previous_graph(self, design_request):
        """Create a previous task graph."""
        from ai_designer.schemas.task_graph import TaskNode

        graph = TaskGraph(request_id=design_request.request_id)
        graph.add_task(
            TaskNode(
                task_id="task_1",
                operation_type="create_box",
                description="Box",
                parameters={"length": 10.0},
                status=TaskStatus.PENDING,
            )
        )
        return graph

    @pytest.mark.asyncio
    async def test_replan_success(
        self, planner, mock_provider, design_request, previous_graph
    ):
        """Test successful replanning with feedback."""
        improved_response = {
            "tasks": [
                {
                    "id": "task_1",
                    "operation": "create_box",
                    "description": "Improved box",
                    "parameters": {"length": 15.0, "width": 15.0, "height": 15.0},
                    "status": "pending",
                }
            ],
            "dependencies": [],
        }

        llm_response = LLMResponse(
            content=json.dumps(improved_response),
            model="gpt-4",
            provider="openai",
            usage={"prompt_tokens": 150, "completion_tokens": 100, "total_tokens": 250},
            finish_reason="stop",
        )

        mock_provider.generate = AsyncMock(return_value=llm_response)

        feedback = "Box dimensions are too small, increase to 15mm"
        new_graph = await planner.replan(design_request, feedback, previous_graph)

        assert len(new_graph.nodes) == 1
        assert new_graph.nodes["task_1"].parameters["length"] == 15.0

        # Verify LLM was called with feedback
        mock_provider.generate.assert_called_once()
        call_args = mock_provider.generate.call_args[0][0]
        assert any("VALIDATION FEEDBACK" in msg.content for msg in call_args.messages)

    @pytest.mark.asyncio
    async def test_replan_failure(
        self, planner, mock_provider, design_request, previous_graph
    ):
        """Test replanning failure after max retries."""
        invalid_response = LLMResponse(
            content="Invalid JSON",
            model="gpt-4",
            provider="openai",
            usage={"prompt_tokens": 50, "completion_tokens": 20, "total_tokens": 70},
            finish_reason="stop",
        )

        mock_provider.generate = AsyncMock(return_value=invalid_response)

        feedback = "Needs improvement"

        with pytest.raises(RuntimeError, match="Failed to replan"):
            await planner.replan(design_request, feedback, previous_graph)

        assert mock_provider.generate.call_count == 3


class TestPlannerAgentHelpers:
    """Test PlannerAgent helper methods."""

    @pytest.fixture
    def planner(self):
        """Create a PlannerAgent instance."""
        mock_provider = MagicMock(spec=UnifiedLLMProvider)
        return PlannerAgent(llm_provider=mock_provider)

    def test_parse_llm_response_valid_json(self, planner):
        """Test parsing valid JSON response."""
        content = json.dumps(
            {
                "tasks": [
                    {
                        "id": "task_1",
                        "operation": "create_box",
                        "description": "Box",
                        "status": "pending",
                    }
                ],
                "dependencies": [],
            }
        )

        result = planner._parse_llm_response(content)

        assert "tasks" in result
        assert "dependencies" in result
        assert len(result["tasks"]) == 1

    def test_parse_llm_response_markdown(self, planner):
        """Test parsing JSON wrapped in markdown."""
        content = """```json
{
  "tasks": [],
  "dependencies": []
}
```"""

        result = planner._parse_llm_response(content)

        assert "tasks" in result
        assert "dependencies" in result

    def test_parse_llm_response_invalid_json(self, planner):
        """Test parsing invalid JSON raises error."""
        with pytest.raises(json.JSONDecodeError):
            planner._parse_llm_response("Not valid JSON {")

    def test_parse_llm_response_missing_tasks(self, planner):
        """Test parsing response without tasks field."""
        content = json.dumps({"dependencies": []})

        with pytest.raises(ValueError, match="missing 'tasks' field"):
            planner._parse_llm_response(content)

    def test_parse_llm_response_auto_adds_dependencies(self, planner):
        """Test that missing dependencies field is auto-added."""
        content = json.dumps({"tasks": []})

        result = planner._parse_llm_response(content)

        assert "dependencies" in result
        assert result["dependencies"] == []

    def test_build_task_graph_valid(self, planner):
        """Test building task graph from valid data."""
        from uuid import uuid4

        task_data = {
            "tasks": [
                {
                    "id": "task_1",
                    "operation": "create_box",
                    "description": "Box",
                    "parameters": {"length": 10.0},
                    "status": "pending",
                }
            ],
            "dependencies": [],
        }

        graph = planner._build_task_graph(task_data, uuid4())

        assert len(graph.nodes) == 1
        assert "task_1" in graph.nodes

    def test_build_task_graph_with_cycle(self, planner):
        """Test building task graph with cycle raises error."""
        from uuid import uuid4

        task_data = {
            "tasks": [
                {
                    "id": "task_1",
                    "operation": "create_box",
                    "description": "Box 1",
                    "status": "pending",
                },
                {
                    "id": "task_2",
                    "operation": "create_box",
                    "description": "Box 2",
                    "status": "pending",
                },
            ],
            "dependencies": [
                {"from_task_id": "task_1", "to_task_id": "task_2"},
                {"from_task_id": "task_2", "to_task_id": "task_1"},
            ],
        }

        with pytest.raises(ValueError, match="contains cycles"):
            planner._build_task_graph(task_data, uuid4())
