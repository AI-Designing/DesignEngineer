"""
Design creation and management endpoints.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ai_designer.agents.executor import FreeCADExecutor
from ai_designer.agents.orchestrator import OrchestratorAgent
from ai_designer.api.deps import get_freecad_executor, get_orchestrator_agent, get_pipeline_executor
from ai_designer.orchestration.pipeline import PipelineExecutor
from ai_designer.schemas.design_state import DesignRequest as DesignRequestSchema
from ai_designer.schemas.design_state import DesignState, ExecutionStatus

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response schemas
class DesignRequest(BaseModel):
    """Request to create a new design."""

    prompt: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Natural language description of the design to create",
        examples=[
            "Create a 10x10x10mm cube",
            "Design a gear wheel with 20 teeth and 50mm diameter",
        ],
    )
    max_iterations: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum refinement iterations",
    )
    enable_execution: bool = Field(
        default=True,
        description="Whether to execute generated scripts in FreeCAD",
    )


class DesignResponse(BaseModel):
    """Response after submitting a design request."""

    request_id: str = Field(..., description="Unique design request ID")
    status: ExecutionStatus = Field(..., description="Current design status")
    message: str = Field(..., description="Human-readable status message")
    created_at: datetime = Field(..., description="Request creation timestamp")


class DesignStatusResponse(BaseModel):
    """Detailed status of a design request."""

    request_id: str
    status: ExecutionStatus
    prompt: str
    current_iteration: int
    max_iterations: int
    created_at: datetime
    updated_at: datetime
    plan_summary: Optional[str] = None
    generated_script: Optional[str] = None
    execution_result: Optional[Dict[str, Any]] = None
    validation_score: Optional[float] = None
    error_message: Optional[str] = None


class RefinementRequest(BaseModel):
    """Request to refine a design based on feedback."""

    feedback: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Specific feedback on what to improve",
        examples=["Make the bracket thicker", "Add fillets to all edges"],
    )


# Temporary in-memory storage (will be replaced with Redis)
_designs: Dict[str, DesignState] = {}


@router.post(
    "/design", status_code=status.HTTP_202_ACCEPTED, response_model=DesignResponse
)
async def create_design(
    request: DesignRequest,
    background_tasks: BackgroundTasks,
    pipeline: PipelineExecutor = Depends(get_pipeline_executor),
) -> DesignResponse:
    """
    Submit a new design request.

    The design pipeline runs asynchronously using LangGraph orchestration:
    1. Planner Agent: Create task graph
    2. Generator Agent: Generate FreeCAD scripts
    3. Executor: Run scripts (if enabled)
    4. Validator Agent: Check results
    5. Conditional routing: success/refine/replan/fail
    6. Iterate if needed (up to max_iterations)

    Args:
        request: Design parameters
        background_tasks: FastAPI background tasks
        pipeline: LangGraph pipeline executor

    Returns:
        Design request ID and initial status
    """
    request_id = uuid4()
    now = datetime.utcnow()

    # Create initial design state
    design_state = DesignState(
        request_id=request_id,
        user_prompt=request.prompt,
        max_iterations=request.max_iterations,
    )

    # Store in temporary storage
    _designs[str(request_id)] = design_state

    # Add background task to process the design via LangGraph pipeline
    background_tasks.add_task(
        _process_design_pipeline,
        request_id,
        request.prompt,
        request.max_iterations,
        pipeline,
    )

    logger.info(f"Created design request {request_id}: {request.prompt[:50]}...")

    return DesignResponse(
        request_id=str(request_id),
        status=ExecutionStatus.PENDING,
        message="Design request accepted and queued for processing (LangGraph pipeline)",
        created_at=now,
    )


@router.get("/design/{request_id}", response_model=DesignStatusResponse)
async def get_design_status(request_id: str) -> DesignStatusResponse:
    """
    Get the current status of a design request.

    Args:
        request_id: Design request ID

    Returns:
        Detailed design status and results

    Raises:
        HTTPException: If design request not found
    """
    design_state = _designs.get(request_id)

    if not design_state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Design request {request_id} not found",
        )

    # Extract relevant information
    plan_summary = None
    if design_state.task_graph_id:
        plan_summary = f"Task graph: {design_state.task_graph_id}"

    validation_score = None
    if design_state.validation_results:
        validation_score = design_state.validation_results.get("overall_score")

    execution_result = None
    if design_state.freecad_script:
        execution_result = {
            "script_generated": True,
            "validation_status": design_state.is_valid,
        }

    return DesignStatusResponse(
        request_id=str(design_state.request_id),
        status=design_state.status,
        prompt=design_state.user_prompt,
        current_iteration=design_state.current_iteration,
        max_iterations=design_state.max_iterations,
        created_at=design_state.created_at,
        updated_at=design_state.updated_at,
        plan_summary=plan_summary,
        generated_script=design_state.freecad_script,
        execution_result=execution_result,
        validation_score=validation_score,
        error_message=design_state.error_message,
    )


@router.post("/design/{request_id}/refine", status_code=status.HTTP_202_ACCEPTED)
async def refine_design(
    request_id: str,
    refinement: RefinementRequest,
    background_tasks: BackgroundTasks,
    pipeline: PipelineExecutor = Depends(get_pipeline_executor),
) -> Dict[str, str]:
    """
    Submit refinement feedback for a design.

    Args:
        request_id: Design request ID
        refinement: Refinement feedback
        background_tasks: FastAPI background tasks
        pipeline: LangGraph pipeline executor

    Returns:
        Acknowledgment message

    Raises:
        HTTPException: If design not found or cannot be refined
    """
    design_state = _designs.get(request_id)

    if not design_state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Design request {request_id} not found",
        )

    if design_state.status not in [ExecutionStatus.COMPLETED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Design must be completed before refinement (current status: {design_state.status})",
        )

    # Update prompt with refinement feedback
    updated_prompt = f"{design_state.user_prompt}\n\nRefinement: {refinement.feedback}"
    
    # Add background task to reprocess via pipeline
    background_tasks.add_task(
        _process_design_pipeline,
        design_state.request_id,
        updated_prompt,
        design_state.max_iterations,
        pipeline,
    )

    logger.info(f"Refinement requested for {request_id}: {refinement.feedback[:50]}...")

    return {"message": "Refinement request accepted", "request_id": request_id}


@router.delete("/design/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_design(request_id: str) -> None:
    """
    Delete a design request and its artifacts.

    Args:
        request_id: Design request ID

    Raises:
        HTTPException: If design not found
    """
    if request_id not in _designs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Design request {request_id} not found",
        )

    # TODO: Also delete from Redis and clean up files
    del _designs[request_id]

    logger.info(f"Deleted design request {request_id}")


async def _process_design_pipeline(
    request_id: UUID,
    prompt: str,
    max_iterations: int,
    pipeline: PipelineExecutor,
) -> None:
    """
    Background task to process a design request through the LangGraph pipeline.

    Args:
        request_id: Design request ID
        prompt: User's design prompt
        max_iterations: Maximum iterations
        pipeline: LangGraph pipeline executor instance
    """
    str_request_id = str(request_id)
    design_state = _designs.get(str_request_id)
    if not design_state:
        logger.error(f"Design {str_request_id} not found in processing")
        return

    try:
        logger.info(f"Processing design {str_request_id} with LangGraph pipeline...")

        # Create design request for pipeline
        request_schema = DesignRequestSchema(
            request_id=request_id,
            user_prompt=prompt,
        )

        # Execute pipeline
        result_state = await pipeline.execute(request_schema)

        # Update stored state with results
        _designs[str_request_id] = result_state

        logger.info(
            f"Design {str_request_id} completed via pipeline",
            status=result_state.status.value,
            iterations=result_state.current_iteration,
            is_valid=result_state.is_valid,
        )

    except Exception as e:
        logger.exception(f"Error processing design {str_request_id} via pipeline: {e}")
        design_state.mark_failed(f"Pipeline execution failed: {str(e)}")
        _designs[str_request_id] = design_state

