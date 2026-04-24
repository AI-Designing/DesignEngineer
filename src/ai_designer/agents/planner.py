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
    >>> print(f"Generated {len(task_graph.nodes)} tasks")
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import ValidationError

from ai_designer.agents.base import BaseAgent
from ai_designer.agents.prompts.system_prompts import get_planner_system_prompt
from ai_designer.core.llm_provider import LLMRequest, LLMRole, UnifiedLLMProvider
from ai_designer.schemas.design_state import AgentType, DesignRequest
from ai_designer.schemas.planner_plan import parse_and_validate_plan_dict
from ai_designer.schemas.task_graph import (
    TaskDependency,
    TaskGraph,
    TaskNode,
    TaskStatus,
)

logger = logging.getLogger(__name__)


class PlannerAgent(BaseAgent):
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

    def __init__(
        self,
        llm_provider: UnifiedLLMProvider,
        temperature: float = 0.3,
        max_retries: int = 3,
    ):
        """Initialize the Planner Agent."""
        super().__init__(
            llm_provider=llm_provider,
            agent_type=AgentType.PLANNER,
            max_retries=max_retries,
            temperature=temperature,
        )

    async def execute(self, *args: Any, **kwargs: Any) -> Any:  # noqa: D102
        """Delegate to plan() to satisfy BaseAgent contract."""
        return await self.plan(*args, **kwargs)

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
                    "content": get_planner_system_prompt(),
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
                response = await self.llm_provider.agenerate(llm_request)

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

            except (json.JSONDecodeError, ValueError, KeyError, ValidationError) as e:
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
        # Extract JSON from markdown code block (which may be preceded by prose text)
        content = content.strip()
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if fence_match:
            content = fence_match.group(1).strip()
        else:
            # No code fence — try to find the first '{' and extract from there
            brace_idx = content.find("{")
            if brace_idx != -1:
                content = content[brace_idx:]

        # Parse JSON
        data = json.loads(content)

        envelope = parse_and_validate_plan_dict(data)
        return envelope.to_task_graph_dict()

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
        plan_version = task_data.get("plan_version")
        task_graph = TaskGraph(request_id=request_id, plan_version=plan_version)

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
            "plan_version": previous_graph.plan_version or 1,
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
maintaining the original design intent. Include "plan_version": 1 in the JSON."""

        llm_request = LLMRequest(
            messages=[
                {
                    "role": LLMRole.SYSTEM,
                    "content": get_planner_system_prompt(),
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
                response = await self.llm_provider.agenerate(llm_request)
                task_data = self._parse_llm_response(response.content)
                task_graph = self._build_task_graph(
                    task_data, design_request.request_id
                )

                logger.info(
                    f"Successfully replanned with {len(task_graph.nodes)} tasks"
                )

                return task_graph

            except (json.JSONDecodeError, ValueError, KeyError, ValidationError) as e:
                logger.warning(
                    f"Replan attempt {attempt}/{self.max_retries} failed: {e}",
                    exc_info=True,
                )

                if attempt == self.max_retries:
                    raise RuntimeError(
                        f"Failed to replan after {self.max_retries} attempts"
                    ) from e

        raise RuntimeError("Unexpected error in replan method")
