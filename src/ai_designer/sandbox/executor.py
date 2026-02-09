"""
Script executor with subprocess isolation

Executes validated Python scripts in an isolated subprocess with
timeout protection and structured result capture.
"""

import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .result import ExecutionResult, ExecutionStatus


class ScriptExecutor:
    """
    Executes Python scripts in isolated subprocess.

    Provides timeout protection, output capture, and error handling.
    Scripts run in a clean environment with only specified context.
    """

    def __init__(
        self,
        timeout: int = 30,
        python_executable: str = "python3",
        capture_output: bool = True,
    ):
        """
        Initialize executor.

        Args:
            timeout: Maximum execution time in seconds
            python_executable: Path to Python interpreter
            capture_output: Whether to capture stdout/stderr
        """
        self.timeout = timeout
        self.python_executable = python_executable
        self.capture_output = capture_output

    def execute(
        self,
        script: str,
        context: Optional[Dict[str, Any]] = None,
        working_dir: Optional[Path] = None,
    ) -> ExecutionResult:
        """
        Execute script in subprocess.

        Args:
            script: Python script to execute
            context: Context variables to inject (as JSON-serializable dict)
            working_dir: Working directory for execution

        Returns:
            ExecutionResult with status, output, and errors
        """
        start_time = time.time()

        # Create temporary script file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as tmp_file:
            # Inject context if provided
            if context:
                import json

                context_str = json.dumps(context)
                tmp_file.write(f"# Injected context\n")
                tmp_file.write(f"import json\n")
                tmp_file.write(f"_context = json.loads('{context_str}')\n\n")

            tmp_file.write(script)
            tmp_path = tmp_file.name

        try:
            # Execute subprocess
            result = subprocess.run(
                [self.python_executable, tmp_path],
                capture_output=self.capture_output,
                text=True,
                timeout=self.timeout,
                cwd=working_dir,
            )

            execution_time = time.time() - start_time

            # Check success
            if result.returncode == 0:
                return ExecutionResult(
                    success=True,
                    status=ExecutionStatus.SUCCESS,
                    output=result.stdout if self.capture_output else "",
                    execution_time=execution_time,
                    exit_code=result.returncode,
                )
            else:
                return ExecutionResult(
                    success=False,
                    status=ExecutionStatus.EXECUTION_FAILED,
                    output=result.stdout if self.capture_output else "",
                    error=result.stderr if self.capture_output else "",
                    execution_time=execution_time,
                    exit_code=result.returncode,
                )

        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            return ExecutionResult(
                success=False,
                status=ExecutionStatus.TIMEOUT,
                error=f"Execution timed out after {self.timeout} seconds",
                execution_time=execution_time,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            return ExecutionResult(
                success=False,
                status=ExecutionStatus.UNKNOWN_ERROR,
                error=f"Execution error: {str(e)}",
                execution_time=execution_time,
            )

        finally:
            # Clean up temporary file
            try:
                Path(tmp_path).unlink()
            except Exception:
                pass  # Best effort cleanup

    def execute_inline(
        self, script: str, local_env: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """
        Execute script inline (same process) - LESS SAFE.

        Use only when subprocess isolation is not needed.
        Still safer than raw exec() due to environment control.

        Args:
            script: Python script to execute
            local_env: Local environment dictionary

        Returns:
            ExecutionResult with status and captured output
        """
        import io
        import sys

        start_time = time.time()

        # Prepare environment
        if local_env is None:
            local_env = {}

        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = captured_output = io.StringIO()

        try:
            # Execute with restricted builtins
            safe_builtins = {
                "__builtins__": {
                    k: __builtins__[k]
                    for k in [
                        "abs",
                        "all",
                        "any",
                        "bool",
                        "dict",
                        "enumerate",
                        "filter",
                        "float",
                        "int",
                        "len",
                        "list",
                        "map",
                        "max",
                        "min",
                        "print",
                        "range",
                        "round",
                        "set",
                        "sorted",
                        "str",
                        "sum",
                        "tuple",
                        "type",
                        "zip",
                    ]
                    if k in __builtins__
                }
            }

            exec(script, safe_builtins, local_env)

            execution_time = time.time() - start_time
            output = captured_output.getvalue()

            return ExecutionResult(
                success=True,
                status=ExecutionStatus.SUCCESS,
                output=output,
                execution_time=execution_time,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            return ExecutionResult(
                success=False,
                status=ExecutionStatus.EXECUTION_FAILED,
                error=str(e),
                execution_time=execution_time,
            )

        finally:
            sys.stdout = old_stdout
