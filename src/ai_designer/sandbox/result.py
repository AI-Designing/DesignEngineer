"""
Execution result data structures

Defines structured result objects for script execution and validation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ExecutionStatus(Enum):
    """Status of script execution"""

    SUCCESS = "success"
    VALIDATION_FAILED = "validation_failed"
    EXECUTION_FAILED = "execution_failed"
    TIMEOUT = "timeout"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ExecutionResult:
    """
    Result of script execution.

    Attributes:
        success: Whether execution completed successfully
        status: Detailed execution status
        output: Script stdout output
        error: Error message if failed
        execution_time: Time taken to execute (seconds)
        exit_code: Process exit code (None if not subprocess)
        created_objects: List of FreeCAD objects created
        metadata: Additional execution metadata
    """

    success: bool
    status: ExecutionStatus
    output: str = ""
    error: str = ""
    execution_time: float = 0.0
    exit_code: Optional[int] = None
    created_objects: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "success": self.success,
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "execution_time": self.execution_time,
            "exit_code": self.exit_code,
            "created_objects": self.created_objects,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ValidationResult:
    """
    Result of AST validation.

    Attributes:
        valid: Whether script passed validation
        errors: List of validation error messages
        warnings: List of validation warnings
        allowed_modules: Modules that were imported (approved)
        blocked_operations: Operations that were blocked
    """

    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    allowed_modules: List[str] = field(default_factory=list)
    blocked_operations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "allowed_modules": self.allowed_modules,
            "blocked_operations": self.blocked_operations,
        }
