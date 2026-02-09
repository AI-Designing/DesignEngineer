"""
Unit tests for AST validator
"""

import pytest

from ai_designer.sandbox.validator import ASTValidator


class TestASTValidator:
    """Test AST-based script validation"""

    def test_valid_freecad_script(self):
        """Test validation of valid FreeCAD script"""
        validator = ASTValidator()

        script = """
import FreeCAD
import Part

doc = FreeCAD.activeDocument()
box = doc.addObject("Part::Box", "MyBox")
box.Length = 10
doc.recompute()
"""

        result = validator.validate(script)

        assert result.valid is True
        assert len(result.errors) == 0
        assert "FreeCAD" in result.allowed_modules
        assert "Part" in result.allowed_modules

    def test_block_dangerous_imports(self):
        """Test blocking of dangerous module imports"""
        validator = ASTValidator()

        script = """
import os
import subprocess

os.system('rm -rf /')
"""

        result = validator.validate(script)

        assert result.valid is False
        assert any("os" in error for error in result.errors)
        assert any("subprocess" in error for error in result.errors)
        assert "os" in result.blocked_operations or len(result.errors) > 0

    def test_block_exec_eval(self):
        """Test blocking of exec() and eval()"""
        validator = ASTValidator()

        script = """
user_input = input()
exec(user_input)
eval("__import__('os').system('ls')")
"""

        result = validator.validate(script)

        assert result.valid is False
        assert any("exec" in error or "eval" in error for error in result.errors)

    def test_syntax_error(self):
        """Test handling of syntax errors"""
        validator = ASTValidator()

        script = """
def broken_function(
    # Missing closing parenthesis
"""

        result = validator.validate(script)

        assert result.valid is False
        assert len(result.errors) > 0
        assert any("Syntax error" in error for error in result.errors)

    def test_allow_safe_builtins(self):
        """Test that safe builtins are allowed"""
        validator = ASTValidator()

        script = """
numbers = [1, 2, 3, 4, 5]
total = sum(numbers)
length = len(numbers)
maximum = max(numbers)
print(f"Total: {total}, Length: {length}, Max: {maximum}")
"""

        result = validator.validate(script)

        assert result.valid is True
        assert len(result.errors) == 0

    def test_block_file_operations(self):
        """Test blocking of file operations"""
        validator = ASTValidator()

        script = """
with open('/etc/passwd', 'r') as f:
    data = f.read()
"""

        result = validator.validate(script)

        assert result.valid is False
        assert any("open" in error for error in result.errors)

    def test_strict_mode(self):
        """Test strict validation mode"""
        validator = ASTValidator(strict=True)

        script = """
import random  # Not in whitelist
print(random.randint(1, 10))
"""

        result = validator.validate(script)

        assert result.valid is False
        assert any("random" in error for error in result.errors)

    def test_non_strict_mode(self):
        """Test non-strict validation mode (warnings instead of errors)"""
        validator = ASTValidator(strict=False)

        script = """
import random
print(random.randint(1, 10))
"""

        result = validator.validate(script)

        # In non-strict mode, unusual imports generate warnings, not errors
        # (unless they're explicitly blocked like os, sys)
        assert len(result.warnings) > 0 or result.valid is True

    def test_custom_allowed_modules(self):
        """Test custom allowed modules"""
        validator = ASTValidator(allowed_modules={"numpy", "pandas"})

        script = """
import numpy as np
import pandas as pd
"""

        result = validator.validate(script)

        assert result.valid is True
        assert len(result.errors) == 0

    def test_quick_validation(self):
        """Test quick validation method"""
        validator = ASTValidator()

        good_script = "import FreeCAD\\nprint('hello')"
        bad_script = "import os\\nos.system('rm')"

        assert validator.validate_quick(good_script) is True
        assert validator.validate_quick(bad_script) is False

    def test_from_imports(self):
        """Test validation of from-imports"""
        validator = ASTValidator()

        good_script = """
from FreeCAD import Base
from Part import Shape
"""

        bad_script = """
from os import system
from subprocess import call
"""

        good_result = validator.validate(good_script)
        bad_result = validator.validate(bad_script)

        assert good_result.valid is True
        assert bad_result.valid is False
        assert any(
            "os" in error or "subprocess" in error for error in bad_result.errors
        )

    def test_nested_dangerous_calls(self):
        """Test detection of nested dangerous operations"""
        validator = ASTValidator()

        script = """
def sneaky_function():
    globals()['__builtins__']['exec']('print("hacked")')
"""

        result = validator.validate(script)

        assert result.valid is False
        # Should catch both globals() and exec()
        assert any("globals" in error or "exec" in error for error in result.errors)
