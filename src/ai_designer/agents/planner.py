"""Planner Agent for decomposing design prompts into hierarchical task graphs.

The PlannerAgent converts natural language design descriptions into structured
TaskGraph objects with proper dependencies and execution order. It uses LLM-based
reasoning to identify primitive CAD operations, their parameters, and relationships.

Key Features:
- Natural language to task decomposition
- Hierarchical task organization with dependencies
- DAG validation to prevent cycles
- Topological sorting for execution order
- Support for multiple LLM providers via UnifiedLLMProvider

Example:
    >>> planner = PlannerAgent(llm_provider=my_provider)
    >>> task_graph = await planner.plan("Create a box 10x10x10 with a 2mm hole")
    >>> print(f"Generated {len(task_graph.tasks)} tasks")
"""

import json
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from ai_designer.core.llm_provider import LLMRequest, LLMRole, UnifiedLLMProvider
from ai_designer.schemas.design_state import AgentType, DesignRequest
from ai_designer.schemas.task_graph import (
    TaskDependency,
    TaskGraph,
    TaskNode,
    TaskStatus,
)

logger = logging.getLogger(__name__)


class PlannerAgent:
    """Agent responsible for decomposing design prompts into executable task graphs.

    The PlannerAgent uses LLM-based reasoning to convert natural language design
    descriptions into structured TaskGraph objects. It identifies primitive CAD
    operations (create_box, create_cylinder, boolean_cut, etc.), extracts their
    parameters, and establishes dependencies between tasks.

    Attributes:
        llm_provider: Unified LLM provider for multi-model support
        agent_type: Fixed to AgentType.PLANNER
        default_temperature: Temperature for LLM sampling (default: 0.3 for consistency)
        max_retries: Maximum retry attempts for LLM failures (default: 3)
    """

    # System prompt for task decomposition
    SYSTEM_PROMPT = """You are an expert CAD design planner specialized in FreeCAD.
Your role is to decompose natural language design descriptions into a hierarchical
task graph of primitive CAD operations.

AVAILABLE OPERATIONS:
- create_box: Create a rectangular box (params: length, width, height)
- create_cylinder: Create a cylinder (params: radius, height)
- create_sphere: Create a sphere (params: radius)
- create_cone: Create a cone (params: radius1, radius2, height)
- create_torus: Create a torus (params: radius1, radius2)
- boolean_cut: Subtract one shape from another (params: base_task_id, tool_task_id)
- boolean_fuse: Union of two shapes (params: base_task_id, tool_task_id)
- boolean_common: Intersection of two shapes (params: base_task_id, tool_task_id)
- fillet: Round edges (params: base_task_id, radius, edge_indices)
- chamfer: Bevel edges (params: base_task_id, distance, edge_indices)
- extrude: Extrude a 2D sketch (params: sketch_task_id, distance)
- revolve: Revolve a 2D sketch (params: sketch_task_id, axis, angle)

RESPONSE FORMAT:
Return a JSON object with this exact structure:
{
  "tasks": [
    {
      "id": "task_1",
      "operation": "create_box",
      "description": "Create base box 10x10x10mm",
      "parameters": {"length": 10.0, "width": 10.0, "height": 10.0},
      "status": "pending"
    },
    {
      "id": "task_2",
      "operation": "create_cylinder",
      "description": "Create hole cylinder radius 1mm height 12mm",
      "parameters": {"radius": 1.0, "height": 12.0},
      "status": "pending"
    },
    {
      "id": "task_3",
      "operation": "boolean_cut",
      "description": "Cut hole from box",
      "parameters": {"base_task_id": "task_1", "tool_task_id": "task_2"},
      "status": "pending"
    }
  ],
  "dependencies": [
    {"from_task_id": "task_1", "to_task_id": "task_3"},
    {"from_task_id": "task_2", "to_task_id": "task_3"}
  ]
}

RULES:
1. Use descriptive task IDs (task_1, task_2, etc.)
2. All parameters must be numeric or reference other task IDs
3. Dependencies must form a DAG (no cycles)
4. Status is always "pending" for new tasks
5. Boolean operations require base_task_id and tool_task_id
6. Ensure topological ordering is possible

Decompose the following design prompt into a task graph:"""

    def __init__(
        self,
        llm_provider: UnifiedLLMProvider,
        temperature: float = 0.3,
        max_retries: int = 3,
    ):
        """Initialize the Planner Agent.

        Args:
            llm_provider: Unified LLM provider for model interactions
            temperature: LLM temperature for sampling (0.0-1.0, lower = more deterministic)
            max_retries: Maximum retry attempts for LLM failures

        Raises:
            ValueError: If temperature is not in [0.0, 1.0] range
        """
        if not 0.0 <= temperature <= 1.0:
            raise ValueError(f"Temperature must be in [0.0, 1.0], got {temperature}")

        self.llm_provider = llm_provider
        self.agent_type = AgentType.PLANNER
        self.default_temperature = temperature
        self.max_retries = max_retries

        logger.info(
            f"Initialized PlannerAgent with temperature={temperature}, "
            f"max_retries={max_retries}"
        )

    async def plan(
        self,
        design_request: DesignRequest,
        temperature: Optional[float] = None,
    ) -> TaskGraph:
        """Decompose a design request into a hierarchical task graph.

        Uses LLM-based reasoning to convert the natural language prompt into
        structured tasks with dependencies. Validates the resulting graph for
        cycles and ensures topological ordering is possible.

        Args:
            design_request: The design request containing prompt and parameters
            temperature: Override default temperature for this planning call

        Returns:
            TaskGraph: A validated DAG of tasks with dependencies

        Raises:
            ValueError: If LLM response is invalid or task graph has cycles
            RuntimeError: If LLM fails after max retries
        """
        temp = temperature if temperature is not None else self.default_temperature

        logger.info(
            f"Planning task graph for request {design_request.request_id} "
            f"with prompt: {design_request.user_prompt[:100]}..."
        )

        # Prepare LLM request
        llm_request = LLMRequest(
            messages=[
                {
                    "role": LLMRole.SYSTEM,
                    "content": self.SYSTEM_PROMPT,
                },
                {
                    "role": LLMRole.USER,
                    "content": design_request.user_prompt,
                },
            ],
            model=self.llm_provider.default_model,
            temperature=temp,
            max_tokens=2048,
        )

        # Get LLM response with retries
        for attempt in range(1, self.max_retries + 1):
            try:
                response = await self.llm_provider.generate(llm_request)

                # Parse JSON response
                task_data = self._parse_llm_response(response.content)

                # Build and validate task graph
                task_graph = self._build_task_graph(
                    task_data, design_request.request_id
                )

                logger.info(
                    f"Successfully created task graph with {len(task_graph.nodes)} "
                    f"tasks and {len(task_graph.edges)} dependencies"
                )

                return task_graph

            except (json.JSONDecodeError, ValueError, KeyError) as e:
                logger.warning(
                    f"Attempt {attempt}/{self.max_retries} failed: {e}",
                    exc_info=True,
                )

                if attempt == self.max_retries:
                    raise RuntimeError(
                        f"Failed to generate valid task graph after "
                        f"{self.max_retries} attempts"
                    ) from e

                # Optionally adjust temperature for retry
                llm_request.temperature = min(temp + 0.1, 1.0)

        # Should never reach here due to the raise in the loop
        raise RuntimeError("Unexpected error in plan method")

    def _parse_llm_response(self, content: str) -> Dict[str, Any]:
        """Parse and validate LLM JSON response.

        Args:
            content: Raw LLM response content

        Returns:
            Parsed JSON data with tasks and dependencies

        Raises:
            json.JSONDecodeError: If response is not valid JSON
            ValueError: If required fields are missing
        """
        # Try to extract JSON from markdown code blocks if present
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]  # Remove ```json
        if content.startswith("```"):
            content = content[3:]  # Remove ```
        if content.endswith("```"):
            content = content[:-3]  # Remove trailing ```

        content = content.strip()

        # Parse JSON
        data = json.loads(content)

        # Validate structure
        if "tasks" not in data:
            raise ValueError("Response missing 'tasks' field")

        if not isinstance(data["tasks"], list):
            raise ValueError("'tasks' must be a list")

        if "dependencies" not in data:
            # Dependencies are optional, default to empty list
            data["dependencies"] = []

        if not isinstance(data["dependencies"], list):
            raise ValueError("'dependencies' must be a list")

        return data

    def _build_task_graph(
        self, task_data: Dict[str, Any], request_id: UUID
    ) -> TaskGraph:
        """Build and validate a TaskGraph from parsed LLM data.

        Args:
            task_data: Parsed JSON with tasks and dependencies
            request_id: UUID from the DesignRequest

        Returns:
            Validated TaskGraph object

        Raises:
            ValueError: If task graph has cycles or invalid structure
        """
        task_graph = TaskGraph(request_id=request_id)

        # Add all tasks first
        for task_dict in task_data["tasks"]:
            task_node = TaskNode(
                task_id=task_dict["id"],
                operation_type=task_dict["operation"],
                description=task_dict["description"],
                parameters=task_dict.get("parameters", {}),
                status=TaskStatus(task_dict.get("status", "pending")),
            )
            task_graph.add_task(task_node)

        # Add dependencies
        for dep_dict in task_data.get("dependencies", []):
            task_graph.add_dependency(
                from_task=dep_dict["from_task_id"],
                to_task=dep_dict["to_task_id"],
                dependency_type=dep_dict.get("dependency_type", "requires"),
            )

        # Validate DAG structure
        if task_graph.has_cycles():
            raise ValueError("Task graph contains cycles - not a valid DAG")

        # Verify topological ordering is possible
        execution_order = task_graph.get_execution_order()
        total_tasks_in_order = sum(len(level) for level in execution_order)
        if total_tasks_in_order != len(task_graph.nodes):
            raise ValueError(
                f"Topological sort failed: expected {len(task_graph.nodes)} "
                f"tasks but got {total_tasks_in_order}"
            )

        return task_graph

    async def replan(
        self,
        design_request: DesignRequest,
        feedback: str,
        previous_graph: TaskGraph,
    ) -> TaskGraph:
        """Regenerate task graph based on validation feedback.

        Used when the Validator agent identifies issues that require plan changes.
        The LLM receives the original prompt, previous task graph, and feedback
        to generate an improved plan.

        Args:
            design_request: Original design request
            feedback: Validation feedback describing issues
            previous_graph: The previous task graph that failed validation

        Returns:
            New TaskGraph addressing the feedback

        Raises:
            RuntimeError: If replanning fails after max retries
        """
        logger.info(
            f"Replanning for request {design_request.request_id} "
            f"with feedback: {feedback[:100]}..."
        )

        # Convert previous graph to JSON for context
        previous_json = {
            "tasks": [
                {
                    "id": task.task_id,
                    "operation": task.operation_type,
                    "description": task.description,
                    "parameters": task.parameters,
                    "status": task.status.value,
                }
                for task in previous_graph.nodes.values()
            ],
            "dependencies": [
                {
                    "from_task_id": dep.from_task,
                    "to_task_id": dep.to_task,
                }
                for dep in previous_graph.edges
            ],
        }

        replan_prompt = f"""ORIGINAL PROMPT:
{design_request.user_prompt}

PREVIOUS TASK GRAPH:
{json.dumps(previous_json, indent=2)}

VALIDATION FEEDBACK:
{feedback}

Please generate an improved task graph that addresses the feedback while
maintaining the original design intent."""

        llm_request = LLMRequest(
            messages=[
                {
                    "role": LLMRole.SYSTEM,
                    "content": self.SYSTEM_PROMPT,
                },
                {
                    "role": LLMRole.USER,
                    "content": replan_prompt,
                },
            ],
            model=self.llm_provider.default_model,
            temperature=self.default_temperature,
            max_tokens=2048,
        )

        # Reuse the main planning logic
        for attempt in range(1, self.max_retries + 1):
            try:
                response = await self.llm_provider.generate(llm_request)
                task_data = self._parse_llm_response(response.content)
                task_graph = self._build_task_graph(
                    task_data, design_request.request_id
                )

                logger.info(
                    f"Successfully replanned with {len(task_graph.nodes)} tasks"
                )

                return task_graph

            except (json.JSONDecodeError, ValueError, KeyError) as e:
                logger.warning(
                    f"Replan attempt {attempt}/{self.max_retries} failed: {e}",
                    exc_info=True,
                )

                if attempt == self.max_retries:
                    raise RuntimeError(
                        f"Failed to replan after {self.max_retries} attempts"
                    ) from e

        raise RuntimeError("Unexpected error in replan method")
