"""
Safe Script Execution Sandbox

A security-focused module for validating and executing FreeCAD Python scripts
with AST-based whitelisting and subprocess isolation.

This module replaces dangerous exec() calls with a safer alternative that:
- Validates scripts against an AST whitelist
- Blocks dangerous operations (file I/O, network, process spawning)
- Executes in isolated subprocess with timeout
- Returns structured results

Usage:
    from ai_designer.sandbox import ScriptSandbox

    sandbox = ScriptSandbox(timeout=30)
    result = sandbox.execute(script_code, context={"doc_name": "Part"})

    if result.success:
        print(result.output)
    else:
        print(result.error)
"""

from .executor import ScriptExecutor
from .result import ExecutionResult, ExecutionStatus
from .sandbox import ScriptSandbox
from .validator import ASTValidator, ValidationResult

__all__ = [
    "ScriptSandbox",
    "ScriptExecutor",
    "ASTValidator",
    "ExecutionResult",
    "ExecutionStatus",
    "ValidationResult",
]
