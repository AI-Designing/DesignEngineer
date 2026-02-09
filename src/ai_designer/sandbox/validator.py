"""
AST-based script validator

Validates Python scripts against a whitelist of allowed operations
before execution to prevent dangerous code from running.
"""

import ast
from typing import List, Set

from .result import ValidationResult


class ASTValidator:
    """
    Validates Python scripts using Abstract Syntax Tree analysis.

    Checks scripts against whitelists of allowed:
    - Module imports (FreeCAD, Part, Sketcher, etc.)
    - Built-in functions (print, range, len, etc.)
    - Operations (no file I/O, no network, no subprocess)
    """

    # Allowed FreeCAD modules
    ALLOWED_MODULES: Set[str] = {
        "FreeCAD",
        "Part",
        "Sketcher",
        "PartDesign",
        "Draft",
        "Arch",
        "Mesh",
        "Points",
        "Drawing",
        "TechDraw",
        "Path",
        "Fem",
        "Material",
        "Units",
        "Base",
        # Standard library (safe subset)
        "math",
        "datetime",
        "json",
        "re",
        "itertools",
        "functools",
        "collections",
    }

    # Allowed built-in functions
    ALLOWED_BUILTINS: Set[str] = {
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
    }

    # Dangerous operations to block
    BLOCKED_OPERATIONS: Set[str] = {
        "__import__",
        "compile",
        "eval",
        "exec",
        "execfile",
        "open",
        "file",
        "input",
        "raw_input",
        "reload",
        "vars",
        "globals",
        "locals",
        "dir",
        "help",
    }

    # Dangerous modules to block
    BLOCKED_MODULES: Set[str] = {
        "os",
        "sys",
        "subprocess",
        "socket",
        "urllib",
        "urllib2",
        "urllib3",
        "requests",
        "http",
        "httplib",
        "ftplib",
        "telnetlib",
        "pickle",
        "shelve",
        "dbm",
        "sqlite3",
        "ctypes",
        "multiprocessing",
        "threading",
        "importlib",
        "imp",
        "__builtin__",
        "__builtins__",
    }

    def __init__(
        self,
        allowed_modules: Set[str] = None,
        blocked_modules: Set[str] = None,
        strict: bool = True,
    ):
        """
        Initialize validator.

        Args:
            allowed_modules: Custom set of allowed modules (extends defaults)
            blocked_modules: Custom set of blocked modules (extends defaults)
            strict: If True, only explicitly allowed modules are permitted
        """
        self.allowed_modules = self.ALLOWED_MODULES.copy()
        if allowed_modules:
            self.allowed_modules.update(allowed_modules)

        self.blocked_modules = self.BLOCKED_MODULES.copy()
        if blocked_modules:
            self.blocked_modules.update(blocked_modules)

        self.strict = strict

    def validate(self, script: str) -> ValidationResult:
        """
        Validate script using AST analysis.

        Args:
            script: Python script to validate

        Returns:
            ValidationResult with validation status and details
        """
        errors: List[str] = []
        warnings: List[str] = []
        allowed_imports: List[str] = []
        blocked_ops: List[str] = []

        # Parse the script into AST
        try:
            tree = ast.parse(script)
        except SyntaxError as e:
            return ValidationResult(
                valid=False,
                errors=[f"Syntax error: {e.msg} at line {e.lineno}"],
            )

        # Walk the AST and check nodes
        for node in ast.walk(tree):
            # Check imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name.split(".")[0]
                    if module_name in self.blocked_modules:
                        errors.append(f"Blocked module import: {alias.name}")
                        blocked_ops.append(f"import {alias.name}")
                    elif module_name in self.allowed_modules:
                        allowed_imports.append(alias.name)
                    elif self.strict:
                        errors.append(f"Unauthorized module: {alias.name}")
                    else:
                        warnings.append(f"Unusual module import: {alias.name}")

            # Check from-imports
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_name = node.module.split(".")[0]
                    if module_name in self.blocked_modules:
                        errors.append(f"Blocked module import: {node.module}")
                        blocked_ops.append(f"from {node.module} import ...")
                    elif module_name in self.allowed_modules:
                        allowed_imports.append(node.module)
                    elif self.strict:
                        errors.append(f"Unauthorized module: {node.module}")
                    else:
                        warnings.append(f"Unusual module import: {node.module}")

            # Check function calls
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    if func_name in self.BLOCKED_OPERATIONS:
                        errors.append(f"Blocked operation: {func_name}()")
                        blocked_ops.append(func_name)

        # Validation summary
        is_valid = len(errors) == 0

        return ValidationResult(
            valid=is_valid,
            errors=errors,
            warnings=warnings,
            allowed_modules=allowed_imports,
            blocked_operations=blocked_ops,
        )

    def validate_quick(self, script: str) -> bool:
        """
        Quick validation - returns True/False only.

        Args:
            script: Python script to validate

        Returns:
            True if script passes validation, False otherwise
        """
        return self.validate(script).valid
