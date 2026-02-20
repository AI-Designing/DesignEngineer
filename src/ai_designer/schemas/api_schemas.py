"""
API-level Pydantic schemas for design creation and status endpoints.

Moved here from api/routes/design.py to provide a single source of truth
for API request/response structures that can be shared across routes and tests.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from ai_designer.schemas.design_state import ExecutionStatus


class DesignCreateRequest(BaseModel):
    """Request to create a new design (replaces inline DesignRequest in routes)."""

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
