"""
Design state schemas for tracking multi-agent design workflows.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class ExecutionStatus(str, Enum):
    """Status of design execution."""

    PENDING = "pending"
    PLANNING = "planning"
    GENERATING = "generating"
    VALIDATING = "validating"
    REFINING = "refining"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentType(str, Enum):
    """Types of agents in the multi-agent system."""

    PLANNER = "planner"
    GENERATOR = "generator"
    VALIDATOR = "validator"


class DesignRequest(BaseModel):
    """Incoming design request from user."""

    model_config = {"frozen": True}  # Pydantic v2 immutable config

    request_id: UUID = Field(default_factory=uuid4, description="Unique request ID")
    user_prompt: str = Field(
        ..., min_length=1, description="Natural language design description"
    )
    constraints: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional constraints (dimensions, materials, etc.)"
    )
    preferences: Optional[Dict[str, str]] = Field(
        default=None, description="User preferences (complexity, style, etc.)"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Request timestamp"
    )

    @field_validator("user_prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        """Ensure prompt is meaningful."""
        if len(v.strip()) < 5:
            raise ValueError("Prompt must be at least 5 characters")
        return v.strip()


class IterationState(BaseModel):
    """State of a single design iteration."""

    iteration_number: int = Field(..., ge=1, description="Iteration count (1-indexed)")
    agent: AgentType = Field(..., description="Agent responsible for this iteration")
    started_at: datetime = Field(
        default_factory=datetime.utcnow, description="Iteration start time"
    )
    completed_at: Optional[datetime] = Field(
        default=None, description="Iteration completion time"
    )
    output: Optional[Dict[str, Any]] = Field(
        default=None, description="Agent output (plan, script, validation)"
    )
    errors: List[str] = Field(default_factory=list, description="Errors encountered")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class DesignState(BaseModel):
    """Complete state of a design workflow across all agents."""

    request_id: UUID = Field(..., description="Links to original DesignRequest")
    user_prompt: str = Field(..., description="Original user prompt")
    status: ExecutionStatus = Field(
        default=ExecutionStatus.PENDING, description="Current execution status"
    )

    # Task decomposition from Planner
    task_graph_id: Optional[str] = Field(
        default=None, description="Reference to TaskGraph"
    )
    execution_plan: Optional[Dict[str, Any]] = Field(
        default=None, description="High-level execution plan from Planner"
    )

    # Generation from Generator
    freecad_script: Optional[str] = Field(
        default=None, description="Generated FreeCAD Python script"
    )
    script_artifacts: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Intermediate generation artifacts (CAD operations, parameters)",
    )

    # Validation from Validator
    validation_results: Optional[Dict[str, Any]] = Field(
        default=None, description="Validation results (geometric, semantic, LLM review)"
    )
    is_valid: Optional[bool] = Field(
        default=None, description="Overall validation status"
    )

    # Iteration tracking
    iterations: List[IterationState] = Field(
        default_factory=list, description="History of all agent iterations"
    )
    max_iterations: int = Field(
        default=5, ge=1, le=10, description="Maximum refinement iterations"
    )
    current_iteration: int = Field(
        default=0, ge=0, description="Current iteration count"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="State creation time"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update time"
    )
    completed_at: Optional[datetime] = Field(
        default=None, description="Workflow completion time"
    )

    # Error handling
    error_message: Optional[str] = Field(
        default=None, description="Error message if failed"
    )
    error_details: Optional[Dict[str, Any]] = Field(
        default=None, description="Detailed error context"
    )

    def add_iteration(
        self, agent: AgentType, output: Optional[Dict[str, Any]] = None
    ) -> IterationState:
        """Add a new iteration to the state."""
        self.current_iteration += 1
        iteration = IterationState(
            iteration_number=self.current_iteration,
            agent=agent,
            output=output,
        )
        self.iterations.append(iteration)
        self.updated_at = datetime.utcnow()
        return iteration

    def mark_completed(self) -> None:
        """Mark the design workflow as completed."""
        self.status = ExecutionStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def mark_failed(self, error: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Mark the design workflow as failed."""
        self.status = ExecutionStatus.FAILED
        self.error_message = error
        self.error_details = details
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def should_continue_iterating(self) -> bool:
        """Check if workflow should continue iterating."""
        return (
            self.status
            not in {
                ExecutionStatus.COMPLETED,
                ExecutionStatus.FAILED,
                ExecutionStatus.CANCELLED,
            }
            and self.current_iteration < self.max_iterations
        )
