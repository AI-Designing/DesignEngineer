"""
Main sandbox interface

Combines AST validation and safe execution into a single, easy-to-use interface.
"""

from typing import Any, Dict, Optional, Set

from .executor import ScriptExecutor
from .result import ExecutionResult, ExecutionStatus
from .validator import ASTValidator


class ScriptSandbox:
    """
    Complete sandbox for safe script execution.

    Validates scripts before execution and provides subprocess isolation.
    This is the main entry point for replacing dangerous exec() calls.

    Example:
        sandbox = ScriptSandbox(timeout=30)
        result = sandbox.execute(user_script)
        if result.success:
            print(result.output)
        else:
            print(f"Error: {result.error}")
    """

    def __init__(
        self,
        timeout: int = 30,
        strict_validation: bool = True,
        allowed_modules: Optional[Set[str]] = None,
        use_subprocess: bool = True,
    ):
        """
        Initialize sandbox.

        Args:
            timeout: Maximum execution time in seconds
            strict_validation: If True, only whitelisted modules allowed
            allowed_modules: Additional modules to allow (extends defaults)
            use_subprocess: If True, execute in subprocess (safer)
        """
        self.validator = ASTValidator(
            allowed_modules=allowed_modules, strict=strict_validation
        )
        self.executor = ScriptExecutor(timeout=timeout)
        self.use_subprocess = use_subprocess
        self.timeout = timeout

    def validate(self, script: str):
        """
        Validate script without executing.

        Args:
            script: Python script to validate

        Returns:
            ValidationResult with details
        """
        return self.validator.validate(script)

    def execute(
        self,
        script: str,
        context: Optional[Dict[str, Any]] = None,
        skip_validation: bool = False,
    ) -> ExecutionResult:
        """
        Validate and execute script safely.

        Args:
            script: Python script to execute
            context: Context variables to inject
            skip_validation: Skip AST validation (NOT RECOMMENDED)

        Returns:
            ExecutionResult with status, output, and errors
        """
        # Step 1: Validate
        if not skip_validation:
            validation = self.validator.validate(script)
            if not validation.valid:
                return ExecutionResult(
                    success=False,
                    status=ExecutionStatus.VALIDATION_FAILED,
                    error=f"Validation failed: {', '.join(validation.errors)}",
                    metadata={"validation": validation.to_dict()},
                )

        # Step 2: Execute
        if self.use_subprocess:
            return self.executor.execute(script, context=context)
        else:
            # Inline execution (less safe but sometimes necessary)
            return self.executor.execute_inline(script, local_env=context)

    def execute_freecad_script(
        self, script: str, freecad_env: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """
        Execute FreeCAD-specific script with proper environment.

        Args:
            script: FreeCAD Python script
            freecad_env: FreeCAD modules (FreeCAD, Part, etc.)

        Returns:
            ExecutionResult with FreeCAD execution details
        """
        # For FreeCAD scripts, we typically need inline execution
        # because FreeCAD modules aren't available in subprocess
        validation = self.validator.validate(script)
        if not validation.valid:
            return ExecutionResult(
                success=False,
                status=ExecutionStatus.VALIDATION_FAILED,
                error=f"Validation failed: {', '.join(validation.errors)}",
                metadata={"validation": validation.to_dict()},
            )

        # Execute inline with FreeCAD environment
        return self.executor.execute_inline(script, local_env=freecad_env)
