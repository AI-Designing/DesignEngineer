"""
Design creation and management endpoints.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ai_designer.agents.executor import FreeCADExecutor
from ai_designer.agents.orchestrator import OrchestratorAgent
from ai_designer.api.deps import (
    get_cad_exporter,
    get_freecad_executor,
    get_orchestrator_agent,
    get_pipeline_executor,
)
from ai_designer.export.exporter import CADExporter
from ai_designer.orchestration.pipeline import PipelineExecutor
from ai_designer.redis_utils.audit import AuditEventType
from ai_designer.schemas.api_schemas import DesignCreateRequest, DesignResponse, DesignStatusResponse
from ai_designer.schemas.design_state import DesignRequest as DesignRequestSchema
from ai_designer.schemas.design_state import DesignState, ExecutionStatus

logger = logging.getLogger(__name__)

router = APIRouter()


# Keep DesignRequest as alias for backward compatibility within this module
DesignRequest = DesignCreateRequest


class RefinementRequest(BaseModel):
    """Request to refine a design based on feedback."""

    feedback: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Specific feedback on what to improve",
        examples=["Make the bracket thicker", "Add fillets to all edges"],
    )


class ExportResponse(BaseModel):
    """Response for export status."""

    success: bool = Field(..., description="Whether export succeeded")
    format: str = Field(..., description="Export format")
    file_path: Optional[str] = Field(None, description="Path to exported file")
    file_size_bytes: Optional[int] = Field(None, description="File size in bytes")
    cache_hit: bool = Field(False, description="Whether this was a cache hit")
    error: Optional[str] = Field(None, description="Error message if failed")


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


@router.get("/design/{request_id}/export")
async def export_design(
    request_id: str,
    formats: str = Query(
        "step",
        description="Comma-separated export formats (step, stl, fcstd)",
        regex="^(step|stl|fcstd)(,(step|stl|fcstd))*$",
    ),
    exporter: CADExporter = Depends(get_cad_exporter),
) -> Dict[str, ExportResponse]:
    """
    Export design to specified format(s).

    Supports multi-format export in a single request. Results are cached
    based on prompt hash to avoid redundant exports.

    Args:
        request_id: Design request ID
        formats: Comma-separated list (e.g., "step,stl,fcstd")
        exporter: CAD exporter dependency

    Returns:
        Dictionary mapping format to export result

    Examples:
        - GET /api/v1/design/{id}/export?formats=step
        - GET /api/v1/design/{id}/export?formats=step,stl,fcstd

    Raises:
        HTTPException: If design not found or not completed
    """
    # Validate design exists
    design_state = _designs.get(request_id)
    if not design_state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Design request {request_id} not found",
        )

    # Check design is completed successfully
    if design_state.status != ExecutionStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Design must be completed before export (current status: {design_state.status})",
        )

    # Find the generated FCStd document
    # First check if there's an fcstd_path in the design state
    doc_path = None
    if hasattr(design_state, "fcstd_path") and design_state.fcstd_path:
        doc_path = Path(design_state.fcstd_path)
    else:
        # Fall back to searching outputs directory for this request_id
        outputs = exporter.outputs_dir
        fcstd_files = list(outputs.glob(f"*{request_id}*.FCStd"))
        if not fcstd_files:
            # Try auto-save pattern
            fcstd_files = list(outputs.glob("freecad_auto_save_*.FCStd"))

        if fcstd_files:
            # Use most recent
            doc_path = sorted(fcstd_files, key=lambda p: p.stat().st_mtime)[-1]

    if not doc_path or not doc_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"FreeCAD document not found for design {request_id}",
        )

    # Parse formats
    format_list = [f.strip().lower() for f in formats.split(",")]

    # Validate formats
    valid_formats = {"step", "stl", "fcstd"}
    invalid = set(format_list) - valid_formats
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid formats: {invalid}. Use step, stl, or fcstd.",
        )

    try:
        # Export to all requested formats
        export_results = await exporter.export_multiple_formats(
            doc_path=doc_path,
            formats=format_list,
            prompt=design_state.user_prompt,
            request_id=UUID(request_id),
        )

        # Convert to response format
        response = {}
        for format, result in export_results.items():
            response[format] = ExportResponse(
                success=result.success,
                format=result.format,
                file_path=str(result.file_path) if result.file_path else None,
                file_size_bytes=(
                    result.metadata.file_size_bytes if result.metadata else None
                ),
                cache_hit=result.cache_hit,
                error=result.error,
            )

            # Audit log successful exports
            if result.success:
                try:
                    _log_export_audit_event(
                        request_id=UUID(request_id),
                        format=format,
                        file_path=result.file_path,
                        file_size=result.metadata.file_size_bytes if result.metadata else 0,
                        cache_hit=result.cache_hit,
                    )
                except Exception as audit_error:
                    logger.warning(f"Audit logging failed: {audit_error}")

        logger.info(
            f"Export completed for {request_id}: {list(export_results.keys())}"
        )

        return response

    except Exception as e:
        logger.error(f"Export error for {request_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}",
        )


@router.get("/design/{request_id}/download/{format}")
async def download_design(
    request_id: str,
    format: str,
    exporter: CADExporter = Depends(get_cad_exporter),
) -> FileResponse:
    """
    Download exported design file.

    First calls export endpoint to ensure file exists, then returns file download.

    Args:
        request_id: Design request ID
        format: Export format (step, stl, fcstd)
        exporter: CAD exporter dependency

    Returns:
        File download response

    Raises:
        HTTPException: If file not found or export failed
    """
    format = format.lower()
    if format not in ["step", "stl", "fcstd"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid format: {format}. Use step, stl, or fcstd.",
        )

    # Trigger export (will use cache if available)
    export_response = await export_design(request_id, formats=format, exporter=exporter)

    # Check export succeeded
    export_result = export_response.get(format)
    if not export_result or not export_result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {export_result.error if export_result else 'Unknown error'}",
        )

    # Get file path
    file_path = Path(export_result.file_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Export file not found: {file_path}",
        )

    # Determine media type
    media_types = {
        "step": "application/step",
        "stl": "application/vnd.ms-pki.stl",
        "fcstd": "application/octet-stream",
    }

    media_type = media_types.get(format, "application/octet-stream")

    logger.info(f"Downloading {format} for {request_id}: {file_path}")

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=file_path.name,
    )


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


def _log_export_audit_event(
    request_id: UUID,
    format: str,
    file_path: Path,
    file_size: int,
    cache_hit: bool,
) -> None:
    """
    Log design export audit event.

    Uses simple logging if Redis/AuditLogger is not available.

    Args:
        request_id: Design request ID
        format: Export format (step, stl, fcstd)
        file_path: Path to exported file
        file_size: File size in bytes
        cache_hit: Whether this was a cache hit
    """
    # For now, use structured logging
    # TODO: Integrate with full AuditLogger once Redis dependency is available
    logger.info(
        "Design exported",
        extra={
            "event_type": AuditEventType.DESIGN_EXPORTED.value,
            "request_id": str(request_id),
            "format": format,
            "file_path": str(file_path),
            "file_size_bytes": file_size,
            "cache_hit": cache_hit,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )
