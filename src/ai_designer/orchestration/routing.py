"""
Conditional routing logic for the LangGraph pipeline.

Determines the next action based on validation results:
- score >= 0.8: SUCCESS (end workflow)
- 0.4 <= score < 0.8: REFINE (regenerate with feedback)
- 0.2 <= score < 0.4: REPLAN (planning issue, start over)
- score < 0.2: FAIL (unrecoverable)
"""

from typing import Literal

import structlog

from ai_designer.orchestration.state import PipelineState
from ai_designer.schemas.validation import ValidationResult

logger = structlog.get_logger(__name__)

# Routing constants
ROUTE_SUCCESS = "success"
ROUTE_REFINE = "refine"
ROUTE_REPLAN = "replan"
ROUTE_FAIL = "fail"

# Score thresholds
THRESHOLD_SUCCESS = 0.8
THRESHOLD_REFINE = 0.4
THRESHOLD_REPLAN = 0.2

# Type for routing decisions
RoutingDecision = Literal["success", "refine", "replan", "fail"]


def route_after_validation(state: PipelineState) -> RoutingDecision:
    """
    Determine next action based on validation result.

    This is the core conditional edge in the LangGraph pipeline that decides
    whether to:
    - End successfully
    - Loop back to generator for refinement
    - Loop back to planner for replanning
    - Fail and require human intervention

    Args:
        state: Current pipeline state with validation result

    Returns:
        Routing decision: "success", "refine", "replan", or "fail"
    """
    validation = state.validation_result

    # Safety check
    if not validation:
        logger.error("No validation result available for routing")
        state.routing_reason = "No validation result"
        return ROUTE_FAIL

    score = validation.overall_score

    # Check iteration limit first
    if state.has_exceeded_iterations():
        logger.warning(
            "Maximum iterations exceeded",
            iterations=state.workflow_iteration,
            max_iterations=state.max_workflow_iterations,
            score=score,
        )
        state.routing_reason = (
            f"Max iterations ({state.max_workflow_iterations}) exceeded"
        )
        return ROUTE_FAIL

    # Route based on score thresholds
    if score >= THRESHOLD_SUCCESS:
        logger.info(
            "Validation passed - routing to success",
            score=score,
            threshold=THRESHOLD_SUCCESS,
        )
        state.routing_reason = f"Validation passed (score: {score:.2f})"
        return ROUTE_SUCCESS

    elif score >= THRESHOLD_REFINE:
        logger.info(
            "Validation suggests refinement",
            score=score,
            threshold_min=THRESHOLD_REFINE,
            threshold_max=THRESHOLD_SUCCESS,
            iteration=state.workflow_iteration,
        )
        state.routing_reason = f"Refinement needed (score: {score:.2f})"
        return ROUTE_REFINE

    elif score >= THRESHOLD_REPLAN:
        logger.info(
            "Validation suggests replanning",
            score=score,
            threshold_min=THRESHOLD_REPLAN,
            threshold_max=THRESHOLD_REFINE,
            iteration=state.workflow_iteration,
        )
        state.routing_reason = f"Replanning needed (score: {score:.2f})"
        return ROUTE_REPLAN

    else:
        logger.warning(
            "Validation failed - unrecoverable",
            score=score,
            threshold=THRESHOLD_REPLAN,
        )
        state.routing_reason = f"Validation failed (score: {score:.2f})"
        return ROUTE_FAIL


def should_continue_iteration(state: PipelineState) -> bool:
    """
    Check if another iteration should be attempted.

    Args:
        state: Current pipeline state

    Returns:
        True if should continue, False otherwise
    """
    # Check iteration limit
    if state.has_exceeded_iterations():
        return False

    # Check if we have validation result
    if not state.validation_result:
        return True  # First iteration

    # Check if validation passed
    if state.validation_result.overall_score >= THRESHOLD_SUCCESS:
        return False

    # Continue if score is in refinement range
    return state.validation_result.overall_score >= THRESHOLD_REFINE


def get_routing_explanation(score: float, iteration: int, max_iterations: int) -> str:
    """
    Get human-readable explanation of routing decision.

    Args:
        score: Validation score
        iteration: Current iteration number
        max_iterations: Maximum allowed iterations

    Returns:
        Explanation string
    """
    if iteration >= max_iterations:
        return f"Maximum iterations ({max_iterations}) reached without achieving target quality"

    if score >= THRESHOLD_SUCCESS:
        return f"Design meets quality standards (score: {score:.2f} >= {THRESHOLD_SUCCESS})"

    elif score >= THRESHOLD_REFINE:
        return (
            f"Design needs refinement (score: {score:.2f}, target: {THRESHOLD_SUCCESS})"
        )

    elif score >= THRESHOLD_REPLAN:
        return f"Design requires replanning (score: {score:.2f} below refinement threshold)"

    else:
        return f"Design quality unacceptable (score: {score:.2f} < {THRESHOLD_REPLAN})"
