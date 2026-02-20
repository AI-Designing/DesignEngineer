"""
Pydantic schemas for AI Designer multi-agent system.

This package provides type-safe data structures for:
- Design states and requests
- Task graphs and execution plans
- Validation results
- Agent communication
"""

from ai_designer.schemas.api_schemas import (
    DesignCreateRequest,
    DesignResponse,
    DesignStatusResponse,
)
from ai_designer.schemas.design_state import (
    AgentType,
    DesignRequest,
    DesignState,
    ExecutionStatus,
    IterationState,
)
from ai_designer.schemas.llm_schemas import (
    LLMMessage,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    LLMRole,
)
from ai_designer.schemas.task_graph import (
    TaskDependency,
    TaskGraph,
    TaskNode,
    TaskStatus,
)
from ai_designer.schemas.validation import (
    GeometricValidation,
    LLMReviewResult,
    SemanticValidation,
    ValidationResult,
    ValidationSeverity,
)

__all__ = [
    # Design state
    "DesignRequest",
    "DesignState",
    "ExecutionStatus",
    "IterationState",
    "AgentType",
    # Task graph
    "TaskNode",
    "TaskDependency",
    "TaskGraph",
    "TaskStatus",
    # Validation
    "ValidationResult",
    "GeometricValidation",
    "SemanticValidation",
    "LLMReviewResult",
    "ValidationSeverity",
    # LLM schemas
    "LLMProvider",
    "LLMRole",
    "LLMMessage",
    "LLMRequest",
    "LLMResponse",
    # API schemas
    "DesignCreateRequest",
    "DesignResponse",
    "DesignStatusResponse",
]
