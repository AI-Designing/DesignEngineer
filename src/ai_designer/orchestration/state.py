"""
LangGraph state schema for the design pipeline.

Extends DesignState with additional LangGraph-specific fields for
tracking node execution, routing decisions, and intermediate results.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from ai_designer.schemas.design_state import DesignState, ExecutionStatus
from ai_designer.schemas.task_graph import TaskGraph
from ai_designer.schemas.validation import ValidationResult


class PipelineState(BaseModel):
    """
    LangGraph state that wraps DesignState with pipeline-specific metadata.
    
    This state flows through all nodes in the pipeline. Each node reads from
    and writes to this state, enabling:
    - Conditional routing based on validation scores
    - Iteration tracking and limits
    - Node-specific metadata
    - Checkpointing for recovery
    """
    
    # Core design state
    design_state: DesignState
    
    # Pipeline execution metadata
    current_node: Optional[str] = None
    previous_node: Optional[str] = None
    node_history: List[str] = Field(default_factory=list)
    
    # Iteration control
    workflow_iteration: int = 0
    max_workflow_iterations: int = 5
    
    # Intermediate results (shared between nodes)
    task_graph: Optional[TaskGraph] = None
    generated_scripts: Optional[Dict[str, str]] = None
    execution_result: Optional[Dict[str, Any]] = None
    validation_result: Optional[ValidationResult] = None
    
    # Routing control
    next_action: Optional[str] = None  # "success", "refine", "replan", "fail"
    routing_reason: Optional[str] = None
    
    # Timing and performance
    node_start_time: Optional[datetime] = None
    node_durations: Dict[str, float] = Field(default_factory=dict)
    
    # Error handling
    error_count: int = 0
    last_error: Optional[str] = None
    retry_count: Dict[str, int] = Field(default_factory=dict)
    
    class Config:
        arbitrary_types_allowed = True
    
    def enter_node(self, node_name: str) -> None:
        """Mark entry into a pipeline node."""
        self.previous_node = self.current_node
        self.current_node = node_name
        self.node_history.append(node_name)
        self.node_start_time = datetime.utcnow()
    
    def exit_node(self) -> None:
        """Mark exit from a pipeline node and record duration."""
        if self.current_node and self.node_start_time:
            duration = (datetime.utcnow() - self.node_start_time).total_seconds()
            self.node_durations[self.current_node] = duration
            self.node_start_time = None
    
    def increment_iteration(self) -> None:
        """Increment workflow iteration counter."""
        self.workflow_iteration += 1
        self.design_state.current_iteration = self.workflow_iteration
    
    def has_exceeded_iterations(self) -> bool:
        """Check if maximum iterations exceeded."""
        return self.workflow_iteration >= self.max_workflow_iterations
    
    def record_error(self, error: str, node: Optional[str] = None) -> None:
        """Record an error in the pipeline."""
        self.error_count += 1
        self.last_error = error
        if node:
            self.retry_count[node] = self.retry_count.get(node, 0) + 1
    
    @classmethod
    def from_design_state(
        cls, 
        design_state: DesignState,
        max_iterations: int = 5
    ) -> "PipelineState":
        """Create pipeline state from existing design state."""
        return cls(
            design_state=design_state,
            max_workflow_iterations=max_iterations,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "design_state": self.design_state.model_dump(),
            "current_node": self.current_node,
            "workflow_iteration": self.workflow_iteration,
            "node_history": self.node_history,
            "next_action": self.next_action,
            "routing_reason": self.routing_reason,
            "error_count": self.error_count,
            "last_error": self.last_error,
        }
