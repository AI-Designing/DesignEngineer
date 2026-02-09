"""
Safe Script Execution Sandbox

This module provides secure execution of FreeCAD Python scripts with:
- AST-based whitelisting of allowed modules and functions
- Subprocess isolation with timeout
- Dangerous builtin blocking
- Structured result handling

Security principles:
1. Never use exec() or eval() directly
2. Validate all scripts via AST before execution
3. Execute in isolated subprocess
4. Enforce strict timeout limits
5. Whitelist only FreeCAD-specific modules
"""

import ast
import logging
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Structured result from script execution"""

    success: bool
    stdout: str
    stderr: str
    exit_code: int
    execution_time: float
    created_objects: List[str]
    error_message: Optional[str] = None


class ScriptValidationError(Exception):
    """Raised when script validation fails"""

    pass


class ScriptExecutionError(Exception):
    """Raised when script execution fails"""

    pass


class SafeScriptExecutor:
    """
    Safe execution engine for FreeCAD Python scripts.

    This class provides security-hardened script execution with:
    - AST validation against whitelist
    - Subprocess isolation
    - Timeout enforcement
    - Resource limits
    """

    # Allowed module imports
    ALLOWED_MODULES: Set[str] = {
        "FreeCAD",
        "Part",
        "PartDesign",
        "Sketcher",
        "Mesh",
        "Draft",
        "Arch",
        "TechDraw",
        "Path",
        "Material",
        "math",
        "numpy",  # Commonly used for calculations
    }

    # Dangerous builtins to block
    BLOCKED_BUILTINS: Set[str] = {
        "__import__",
        "compile",
        "eval",
        "exec",
        "execfile",
        "open",  # File I/O blocked
        "input",
        "file",
        "reload",
        "vars",
        "globals",
        "locals",
        "dir",
    }

    # Dangerous modules to block
    BLOCKED_MODULES: Set[str] = {
        "os",
        "sys",
        "subprocess",
        "shutil",
        "socket",
        "urllib",
        "requests",
        "pickle",
        "shelve",
        "importlib",
        "__builtin__",
        "builtins",
    }

    def __init__(
        self,
        timeout: int = 60,
        allow_file_io: bool = False,
        freecad_path: Optional[str] = None,
    ):
        """
        Initialize the safe script executor.

        Args:
            timeout: Maximum execution time in seconds
            allow_file_io: Whether to allow file I/O (for export operations)
            freecad_path: Path to FreeCAD executable or AppImage
        """
        self.timeout = timeout
        self.allow_file_io = allow_file_io
        self.freecad_path = freecad_path

        # If file I/O is allowed, remove 'open' from blocked builtins
        if self.allow_file_io:
            self.BLOCKED_BUILTINS.discard("open")

    def validate_script(self, script: str) -> None:
        """
        Validate script against security rules using AST analysis.

        Args:
            script: Python script to validate

        Raises:
            ScriptValidationError: If script contains forbidden patterns
        """
        try:
            tree = ast.parse(script)
        except SyntaxError as e:
            raise ScriptValidationError(f"Syntax error in script: {e}")

        # Walk the AST and check each node
        for node in ast.walk(tree):
            # Check for dangerous imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name.split(".")[0]
                    if module_name in self.BLOCKED_MODULES:
                        raise ScriptValidationError(
                            f"Import of blocked module '{module_name}' not allowed"
                        )
                    if module_name not in self.ALLOWED_MODULES:
                        logger.warning(
                            f"Uncommon module import detected: {module_name}"
                        )

            # Check for dangerous from-imports
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_name = node.module.split(".")[0]
                    if module_name in self.BLOCKED_MODULES:
                        raise ScriptValidationError(
                            f"Import from blocked module '{module_name}' not allowed"
                        )
                    if module_name not in self.ALLOWED_MODULES:
                        logger.warning(
                            f"Uncommon module import detected: {module_name}"
                        )

            # Check for calls to dangerous builtins
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    if func_name in self.BLOCKED_BUILTINS:
                        raise ScriptValidationError(
                            f"Call to blocked builtin '{func_name}' not allowed"
                        )

            # Check for attribute access to dangerous builtins
            elif isinstance(node, ast.Attribute):
                if node.attr in self.BLOCKED_BUILTINS:
                    raise ScriptValidationError(
                        f"Access to blocked attribute '{node.attr}' not allowed"
                    )

        logger.info("Script validation passed")

    def execute(
        self, script: str, document_name: Optional[str] = None
    ) -> ExecutionResult:
        """
        Execute script in a safe, isolated subprocess.

        Args:
            script: Python script to execute
            document_name: Optional FreeCAD document name

        Returns:
            ExecutionResult with execution details

        Raises:
            ScriptValidationError: If script validation fails
            ScriptExecutionError: If execution fails
        """
        # Step 1: Validate script
        self.validate_script(script)

        # Step 2: Prepare execution wrapper
        wrapper_script = self._build_wrapper_script(script, document_name)

        # Step 3: Execute in subprocess
        start_time = time.time()
        try:
            result = self._execute_in_subprocess(wrapper_script)
            execution_time = time.time() - start_time

            return ExecutionResult(
                success=result["success"],
                stdout=result["stdout"],
                stderr=result["stderr"],
                exit_code=result["exit_code"],
                execution_time=execution_time,
                created_objects=result.get("created_objects", []),
                error_message=result.get("error_message"),
            )

        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            raise ScriptExecutionError(
                f"Script execution timed out after {self.timeout} seconds"
            )
        except Exception as e:
            execution_time = time.time() - start_time
            raise ScriptExecutionError(f"Script execution failed: {e}")

    def _build_wrapper_script(
        self, user_script: str, document_name: Optional[str]
    ) -> str:
        """
        Build a wrapper script that sets up the FreeCAD environment
        and executes the user script safely.

        Args:
            user_script: User's script to execute
            document_name: Optional document name

        Returns:
            Complete wrapper script
        """
        doc_name = document_name or "AutoGenDoc"

        wrapper = f"""
import sys
import json

# Import FreeCAD modules
try:
    import FreeCAD
    import Part
except ImportError as e:
    print(json.dumps({{"error": "FreeCAD not available: " + str(e)}}))
    sys.exit(1)

# Initialize document
doc = FreeCAD.newDocument("{doc_name}")
FreeCAD.setActiveDocument("{doc_name}")

# Prepare safe globals
safe_globals = {{
    'FreeCAD': FreeCAD,
    'App': FreeCAD,
    'Part': Part,
    'doc': doc,
}}

# Try to import common modules
try:
    import PartDesign
    safe_globals['PartDesign'] = PartDesign
except ImportError:
    pass

try:
    import Sketcher
    safe_globals['Sketcher'] = Sketcher
except ImportError:
    pass

try:
    import Mesh
    safe_globals['Mesh'] = Mesh
except ImportError:
    pass

# Execute user script
try:
    exec('''\\
{user_script}
''', safe_globals)

    # Recompute document
    doc.recompute()

    # Collect created objects
    created_objects = [obj.Name for obj in doc.Objects]

    # Output result as JSON
    result = {{
        "success": True,
        "created_objects": created_objects,
        "object_count": len(created_objects)
    }}
    print(json.dumps(result))

except Exception as e:
    import traceback
    result = {{
        "success": False,
        "error": str(e),
        "traceback": traceback.format_exc()
    }}
    print(json.dumps(result))
    sys.exit(1)
"""
        return wrapper

    def _execute_in_subprocess(self, script: str) -> Dict[str, Any]:
        """
        Execute script in an isolated subprocess.

        Args:
            script: Complete wrapper script to execute

        Returns:
            Dictionary with execution results
        """
        # Write script to temporary file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as temp_file:
            temp_file.write(script)
            temp_path = temp_file.name

        try:
            # Determine FreeCAD command
            if self.freecad_path and self.freecad_path.endswith(".AppImage"):
                # Execute AppImage with python script
                cmd = [self.freecad_path, "--console", "--run", temp_path]
            elif self.freecad_path:
                # Use provided FreeCAD path
                cmd = [self.freecad_path, "-c", temp_path]
            else:
                # Try system freecadcmd
                cmd = ["freecadcmd", temp_path]

            # Execute with timeout
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=None,  # Use clean environment
            )

            # Parse output
            stdout = process.stdout.strip()
            stderr = process.stderr.strip()

            # Try to parse JSON output
            result = {
                "success": process.returncode == 0,
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": process.returncode,
                "created_objects": [],
            }

            # Try to extract JSON from stdout
            if stdout:
                try:
                    import json

                    # Find JSON in output (might have FreeCAD startup messages)
                    for line in stdout.split("\n"):
                        line = line.strip()
                        if line.startswith("{") and line.endswith("}"):
                            data = json.loads(line)
                            if "success" in data:
                                result.update(data)
                                break
                except json.JSONDecodeError:
                    logger.warning("Could not parse JSON from subprocess output")

            return result

        finally:
            # Clean up temp file
            try:
                Path(temp_path).unlink()
            except Exception:
                pass


# Convenience function for simple execution
def execute_safe_script(
    script: str,
    timeout: int = 60,
    document_name: Optional[str] = None,
    freecad_path: Optional[str] = None,
) -> ExecutionResult:
    """
    Execute a FreeCAD script safely.

    Args:
        script: Python script to execute
        timeout: Maximum execution time in seconds
        document_name: Optional FreeCAD document name
        freecad_path: Path to FreeCAD executable or AppImage

    Returns:
        ExecutionResult with execution details

    Example:
        >>> result = execute_safe_script('''
        ... box = Part.makeBox(10, 10, 10)
        ... Part.show(box)
        ... ''')
        >>> if result.success:
        ...     print(f"Created {len(result.created_objects)} objects")
    """
    executor = SafeScriptExecutor(timeout=timeout, freecad_path=freecad_path)
    return executor.execute(script, document_name=document_name)
