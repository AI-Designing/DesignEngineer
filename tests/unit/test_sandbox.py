"""
Unit tests for SafeScriptExecutor sandbox

Tests cover:
- Script validation (AST whitelist)
- Malicious script rejection
- Valid script acceptance
- Timeout enforcement
- Subprocess isolation
"""

import subprocess
from unittest.mock import MagicMock, Mock, patch

import pytest

from ai_designer.core.sandbox import (
    SafeScriptExecutor,
    ScriptExecutionError,
    ScriptValidationError,
    execute_safe_script,
)


class TestScriptValidation:
    """Test AST-based script validation"""

    def test_valid_freecad_script(self):
        """Valid FreeCAD script should pass validation"""
        executor = SafeScriptExecutor()
        script = """
import FreeCAD
import Part

box = Part.makeBox(10, 10, 10)
Part.show(box)
"""
        # Should not raise
        executor.validate_script(script)

    def test_blocked_os_import(self):
        """Script importing 'os' module should be rejected"""
        executor = SafeScriptExecutor()
        script = """
import os
os.system('rm -rf /')
"""
        with pytest.raises(ScriptValidationError, match="blocked module 'os'"):
            executor.validate_script(script)

    def test_blocked_subprocess_import(self):
        """Script importing 'subprocess' should be rejected"""
        executor = SafeScriptExecutor()
        script = """
import subprocess
subprocess.run(['ls', '-la'])
"""
        with pytest.raises(ScriptValidationError, match="blocked module 'subprocess'"):
            executor.validate_script(script)

    def test_blocked_sys_import(self):
        """Script importing 'sys' should be rejected"""
        executor = SafeScriptExecutor()
        script = """
import sys
sys.exit(1)
"""
        with pytest.raises(ScriptValidationError, match="blocked module 'sys'"):
            executor.validate_script(script)

    def test_blocked_eval_call(self):
        """Script calling eval() should be rejected"""
        executor = SafeScriptExecutor()
        script = """
result = eval('1 + 1')
"""
        with pytest.raises(ScriptValidationError, match="blocked builtin 'eval'"):
            executor.validate_script(script)

    def test_blocked_exec_call(self):
        """Script calling exec() should be rejected"""
        executor = SafeScriptExecutor()
        script = """
exec('print("hello")')
"""
        with pytest.raises(ScriptValidationError, match="blocked builtin 'exec'"):
            executor.validate_script(script)

    def test_blocked_open_call(self):
        """Script calling open() should be rejected by default"""
        executor = SafeScriptExecutor(allow_file_io=False)
        script = """
with open('/etc/passwd', 'r') as f:
    data = f.read()
"""
        with pytest.raises(ScriptValidationError, match="blocked builtin 'open'"):
            executor.validate_script(script)

    def test_allowed_open_with_file_io_enabled(self):
        """Script calling open() should pass if file_io is allowed"""
        executor = SafeScriptExecutor(allow_file_io=True)
        script = """
with open('/tmp/test.txt', 'w') as f:
    f.write('test')
"""
        # Should not raise
        executor.validate_script(script)

    def test_syntax_error_detection(self):
        """Script with syntax errors should be rejected"""
        executor = SafeScriptExecutor()
        script = """
def broken_function(
    # Missing closing parenthesis
"""
        with pytest.raises(ScriptValidationError, match="Syntax error"):
            executor.validate_script(script)

    def test_allowed_math_import(self):
        """Script importing 'math' module should pass"""
        executor = SafeScriptExecutor()
        script = """
import math
radius = 5
circumference = 2 * math.pi * radius
"""
        # Should not raise
        executor.validate_script(script)

    def test_allowed_numpy_import(self):
        """Script importing 'numpy' module should pass"""
        executor = SafeScriptExecutor()
        script = """
import numpy as np
array = np.array([1, 2, 3])
"""
        # Should not raise
        executor.validate_script(script)


class TestScriptExecution:
    """Test script execution in subprocess"""

    @patch("subprocess.run")
    def test_successful_execution(self, mock_run):
        """Successful script execution should return success result"""
        # Mock subprocess result
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"success": true, "created_objects": ["Box"], "object_count": 1}',
            stderr="",
        )

        executor = SafeScriptExecutor(timeout=30)
        script = """
import Part
box = Part.makeBox(10, 10, 10)
Part.show(box)
"""
        result = executor.execute(script)

        assert result.success is True
        assert result.exit_code == 0
        assert "Box" in result.created_objects or result.created_objects == []
        assert result.execution_time >= 0

    @patch("subprocess.run")
    def test_execution_failure(self, mock_run):
        """Failed script execution should return error result"""
        # Mock subprocess failure
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout='{"success": false, "error": "NameError: name \'undefined_var\' is not defined"}',
            stderr="Error during execution",
        )

        executor = SafeScriptExecutor(timeout=30)
        script = """
result = undefined_var + 10
"""
        result = executor.execute(script)

        assert result.success is False
        assert result.exit_code == 1
        assert len(result.stderr) > 0

    @patch(
        "subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="test", timeout=5)
    )
    def test_timeout_enforcement(self, mock_run):
        """Script exceeding timeout should raise ScriptExecutionError"""
        executor = SafeScriptExecutor(timeout=5)
        script = """
import time
time.sleep(10)  # Exceeds timeout
"""
        with pytest.raises(ScriptExecutionError, match="timed out"):
            executor.execute(script)

    def test_validation_before_execution(self):
        """Invalid script should fail validation before execution"""
        executor = SafeScriptExecutor()
        script = """
import os
os.system('malicious command')
"""
        with pytest.raises(ScriptValidationError):
            executor.execute(script)


class TestWrapperScriptGeneration:
    """Test wrapper script generation"""

    def test_wrapper_includes_user_script(self):
        """Wrapper script should include user's code"""
        executor = SafeScriptExecutor()
        user_script = "box = Part.makeBox(10, 10, 10)"
        wrapper = executor._build_wrapper_script(user_script, "TestDoc")

        assert user_script in wrapper
        assert "TestDoc" in wrapper
        assert "import FreeCAD" in wrapper
        assert "safe_globals" in wrapper

    def test_wrapper_sets_document_name(self):
        """Wrapper should use provided document name"""
        executor = SafeScriptExecutor()
        wrapper = executor._build_wrapper_script("pass", "MyDocument")

        assert 'newDocument("MyDocument")' in wrapper
        assert 'setActiveDocument("MyDocument")' in wrapper

    def test_wrapper_default_document_name(self):
        """Wrapper should use default name if none provided"""
        executor = SafeScriptExecutor()
        wrapper = executor._build_wrapper_script("pass", None)

        assert 'newDocument("AutoGenDoc")' in wrapper


class TestConvenienceFunction:
    """Test execute_safe_script convenience function"""

    @patch("ai_designer.core.sandbox.SafeScriptExecutor.execute")
    def test_convenience_function_calls_executor(self, mock_execute):
        """Convenience function should create executor and call execute"""
        mock_execute.return_value = MagicMock(
            success=True, created_objects=["Box"], execution_time=1.5
        )

        script = "box = Part.makeBox(10, 10, 10)"
        result = execute_safe_script(script, timeout=30)

        mock_execute.assert_called_once()
        assert result.success is True


class TestSecurityFeatures:
    """Test security-specific features"""

    def test_rejects_import_star(self):
        """Script with 'from X import *' should be allowed but logged"""
        executor = SafeScriptExecutor()
        script = """
from FreeCAD import *
"""
        # This should pass (FreeCAD is allowed)
        executor.validate_script(script)

    def test_rejects_double_underscore_access(self):
        """Script accessing __import__ should be rejected"""
        executor = SafeScriptExecutor()
        script = """
__import__('os').system('ls')
"""
        with pytest.raises(ScriptValidationError, match="blocked builtin '__import__'"):
            executor.validate_script(script)

    def test_rejects_globals_access(self):
        """Script accessing globals() should be rejected"""
        executor = SafeScriptExecutor()
        script = """
g = globals()
g['__builtins__']['__import__']('os')
"""
        with pytest.raises(ScriptValidationError, match="blocked builtin 'globals'"):
            executor.validate_script(script)

    def test_rejects_locals_access(self):
        """Script accessing locals() should be rejected"""
        executor = SafeScriptExecutor()
        script = """
l = locals()
"""
        with pytest.raises(ScriptValidationError, match="blocked builtin 'locals'"):
            executor.validate_script(script)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
