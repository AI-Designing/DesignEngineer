"""
LangGraph pipeline construction for the design workflow.

Builds a StateGraph that orchestrates:
- Planner → Generator → Executor → Validator
- Conditional routing based on validation scores
- Iteration limits and timeout management
- WebSocket progress callbacks
"""

from typing import Any, Callable, Optional

import structlog
from langgraph.graph import END, StateGraph

from ai_designer.agents.executor import FreeCADExecutor
from ai_designer.agents.generator import GeneratorAgent
from ai_designer.agents.planner import PlannerAgent
from ai_designer.agents.validator import ValidatorAgent
from ai_designer.orchestration.nodes import PipelineNodes
from ai_designer.orchestration.routing import (
    ROUTE_FAIL,
    ROUTE_REFINE,
    ROUTE_REPLAN,
    ROUTE_SUCCESS,
    route_after_validation,
)
from ai_designer.orchestration.state import PipelineState
from ai_designer.schemas.design_state import DesignRequest, DesignState, ExecutionStatus

logger = structlog.get_logger(__name__)


def build_design_pipeline(
    planner: PlannerAgent,
    generator: GeneratorAgent,
    validator: ValidatorAgent,
    executor: Optional[FreeCADExecutor] = None,
    websocket_callback: Optional[Callable] = None,
    max_iterations: int = 5,
) -> StateGraph:
    """
    Build the LangGraph state machine for design workflow.

    The pipeline implements:

    ```
    START
      ↓
    planner ──→ generator ──→ executor ──→ validator
                   ↑                          │
                   │                          │
                   └─────── refine ←──────────┤
                                              │
    planner ←────── replan ←──────────────────┤
                                              │
    END ←────────── success ←─────────────────┤
                                              │
    human_review ←── fail ←───────────────────┘
    ```

    Args:
        planner: Planner agent instance
        generator: Generator agent instance
        validator: Validator agent instance
        executor: Optional FreeCAD executor
        websocket_callback: Optional callback for progress updates
        max_iterations: Maximum workflow iterations (default: 5)

    Returns:
        Compiled StateGraph ready for execution
    """
    logger.info(
        "Building design pipeline",
        max_iterations=max_iterations,
        has_executor=executor is not None,
        has_websocket=websocket_callback is not None,
    )

    # Create node wrapper with agents
    nodes = PipelineNodes(
        planner=planner,
        generator=generator,
        validator=validator,
        executor=executor,
        websocket_callback=websocket_callback,
    )

    # Initialize state graph
    workflow = StateGraph(PipelineState)

    # Add nodes
    workflow.add_node("planner", nodes.planner_node)
    workflow.add_node("generator", nodes.generator_node)
    workflow.add_node("executor", nodes.executor_node)
    workflow.add_node("validator", nodes.validator_node)

    # Set entry point
    workflow.set_entry_point("planner")

    # Linear edges through initial workflow
    workflow.add_edge("planner", "generator")
    workflow.add_edge("generator", "executor")
    workflow.add_edge("executor", "validator")

    # Conditional edges from validator
    workflow.add_conditional_edges(
        "validator",
        route_after_validation,
        {
            ROUTE_SUCCESS: END,  # Design passed validation
            ROUTE_REFINE: "generator",  # Loop back with feedback
            ROUTE_REPLAN: "planner",  # Major issue, replan
            ROUTE_FAIL: END,  # Unrecoverable, end workflow
        },
    )

    logger.info("Design pipeline built successfully")

    return workflow.compile()


async def run_design_pipeline(
    request: DesignRequest,
    planner: PlannerAgent,
    generator: GeneratorAgent,
    validator: ValidatorAgent,
    executor: Optional[FreeCADExecutor] = None,
    websocket_callback: Optional[Callable] = None,
    max_iterations: int = 5,
) -> DesignState:
    """
    Execute the design pipeline for a request.

    This is a high-level convenience function that:
    1. Builds the pipeline
    2. Initializes state
    3. Executes the workflow
    4. Returns final design state

    Args:
        request: Design request from user
        planner: Planner agent
        generator: Generator agent
        validator: Validator agent
        executor: Optional FreeCAD executor
        websocket_callback: Optional WebSocket callback
        max_iterations: Maximum iterations

    Returns:
        Final design state with results
    """
    logger.info(
        "Starting design pipeline execution",
        request_id=str(request.request_id),
        prompt=request.user_prompt[:100],
        max_iterations=max_iterations,
    )

    try:
        # Build pipeline
        pipeline = build_design_pipeline(
            planner=planner,
            generator=generator,
            validator=validator,
            executor=executor,
            websocket_callback=websocket_callback,
            max_iterations=max_iterations,
        )

        # Initialize design state
        design_state = DesignState(
            request_id=request.request_id,
            user_prompt=request.user_prompt,
            max_iterations=max_iterations,
        )

        # Create pipeline state
        pipeline_state = PipelineState.from_design_state(
            design_state=design_state,
            max_iterations=max_iterations,
        )

        # Execute pipeline
        logger.info("Invoking pipeline", request_id=str(request.request_id))
        final_state = await pipeline.ainvoke(pipeline_state)

        # Update design state based on final routing decision
        if final_state.next_action == ROUTE_SUCCESS:
            final_state.design_state.mark_completed()
        elif final_state.next_action == ROUTE_FAIL:
            if not final_state.design_state.error_message:
                final_state.design_state.mark_failed(
                    final_state.routing_reason or "Pipeline failed"
                )

        logger.info(
            "Pipeline execution completed",
            request_id=str(request.request_id),
            status=final_state.design_state.status.value,
            iterations=final_state.workflow_iteration,
            next_action=final_state.next_action,
        )

        return final_state.design_state

    except Exception as e:
        logger.error(
            "Pipeline execution failed",
            request_id=str(request.request_id),
            error=str(e),
            exc_info=True,
        )

        # Create failed state
        design_state = DesignState(
            request_id=request.request_id,
            user_prompt=request.user_prompt,
            max_iterations=max_iterations,
        )
        design_state.mark_failed(f"Pipeline execution failed: {str(e)}")

        return design_state


class PipelineExecutor:
    """
    Reusable pipeline executor that maintains compiled pipeline.

    This class compiles the pipeline once and reuses it for multiple executions,
    improving performance by avoiding repeated compilation.
    """

    def __init__(
        self,
        planner: PlannerAgent,
        generator: GeneratorAgent,
        validator: ValidatorAgent,
        executor: Optional[FreeCADExecutor] = None,
        websocket_callback: Optional[Callable] = None,
        max_iterations: int = 5,
    ):
        """
        Initialize pipeline executor.

        Args:
            planner: Planner agent
            generator: Generator agent
            validator: Validator agent
            executor: Optional FreeCAD executor
            websocket_callback: Optional WebSocket callback
            max_iterations: Maximum iterations
        """
        self.planner = planner
        self.generator = generator
        self.validator = validator
        self.executor = executor
        self.websocket_callback = websocket_callback
        self.max_iterations = max_iterations

        # Compile pipeline once
        self.pipeline = build_design_pipeline(
            planner=planner,
            generator=generator,
            validator=validator,
            executor=executor,
            websocket_callback=websocket_callback,
            max_iterations=max_iterations,
        )

        logger.info("Pipeline executor initialized")

    async def execute(self, request: DesignRequest) -> DesignState:
        """
        Execute pipeline for a design request.

        Args:
            request: Design request

        Returns:
            Final design state
        """
        logger.info(
            "Executing pipeline",
            request_id=str(request.request_id),
        )

        try:
            # Initialize states
            design_state = DesignState(
                request_id=request.request_id,
                user_prompt=request.user_prompt,
                max_iterations=self.max_iterations,
            )

            pipeline_state = PipelineState.from_design_state(
                design_state=design_state,
                max_iterations=self.max_iterations,
            )

            # Execute
            final_state = await self.pipeline.ainvoke(pipeline_state)

            # Update final status
            if final_state.next_action == ROUTE_SUCCESS:
                final_state.design_state.mark_completed()
            elif final_state.next_action == ROUTE_FAIL:
                if not final_state.design_state.error_message:
                    final_state.design_state.mark_failed(
                        final_state.routing_reason or "Pipeline failed"
                    )

            return final_state.design_state

        except Exception as e:
            logger.error("Pipeline execution failed", error=str(e), exc_info=True)
            design_state = DesignState(
                request_id=request.request_id,
                user_prompt=request.user_prompt,
                max_iterations=self.max_iterations,
            )
            design_state.mark_failed(f"Pipeline execution failed: {str(e)}")
            return design_state
