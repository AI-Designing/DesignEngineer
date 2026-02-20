"""
Integration tests for complete sandbox
"""

import pytest

from ai_designer.sandbox import ExecutionStatus, ScriptSandbox


class TestScriptSandbox:
    """Test complete sandbox integration"""

    def test_successful_validated_execution(self):
        """Test successful validation and execution"""
        sandbox = ScriptSandbox(timeout=5, strict_validation=True)

        script = """
import FreeCAD
print("FreeCAD script running")
"""

        result = sandbox.execute(script)

        # In test environment FreeCAD may not be available,
        # but the script should at least pass validation
        # (FreeCAD is in the whitelist)
        assert result.status != ExecutionStatus.VALIDATION_FAILED

    def test_validation_blocks_dangerous_code(self):
        """Test that validation blocks dangerous operations"""
        sandbox = ScriptSandbox(timeout=5, strict_validation=True)

        script = """
import os
os.system('rm -rf /')
"""

        result = sandbox.execute(script)

        assert result.success is False
        assert result.status == ExecutionStatus.VALIDATION_FAILED
        assert "validation" in result.error.lower()

    def test_skip_validation_option(self):
        """Test skipping validation (not recommended)"""
        sandbox = ScriptSandbox(timeout=5)

        script = """
print("Skipped validation")
"""

        result = sandbox.execute(script, skip_validation=True)

        assert result.success is True

    def test_validation_only(self):
        """Test validation without execution"""
        sandbox = ScriptSandbox()

        good_script = "import FreeCAD\nprint('good')"
        bad_script = "import os\nos.system('bad')"

        good_validation = sandbox.validate(good_script)
        bad_validation = sandbox.validate(bad_script)

        assert good_validation.valid is True
        assert bad_validation.valid is False

    def test_freecad_script_execution(self):
        """Test FreeCAD-specific script execution"""
        sandbox = ScriptSandbox(use_subprocess=False)

        # Mock FreeCAD environment
        mock_freecad = type(
            "FreeCAD",
            (),
            {
                "Vector": lambda x, y, z: f"Vector({x}, {y}, {z})",
                "Console": type("Console", (), {"PrintMessage": print})(),
            },
        )()

        script = """
v = FreeCAD.Vector(1, 2, 3)
print(f"Created vector: {v}")
"""

        result = sandbox.execute_freecad_script(
            script, freecad_env={"FreeCAD": mock_freecad}
        )

        assert result.success is True
        assert "Vector(1, 2, 3)" in result.output

    def test_custom_allowed_modules(self):
        """Test sandbox with custom allowed modules"""
        sandbox = ScriptSandbox(
            allowed_modules={"custom_module"}, strict_validation=True
        )

        script = """
import custom_module
print("Custom module imported")
"""

        validation = sandbox.validate(script)
        assert validation.valid is True

    def test_context_passing(self):
        """Test context variable passing through sandbox"""
        sandbox = ScriptSandbox(use_subprocess=True, timeout=5)

        script = """
name = _context['project']
value = _context['count']
print(f"Project: {name}, Count: {value}")
"""

        context = {"project": "TestProject", "count": 10}
        result = sandbox.execute(script, context=context)

        assert result.success is True
        assert "Project: TestProject" in result.output
        assert "Count: 10" in result.output

    def test_timeout_protection(self):
        """Test timeout protection in sandbox"""
        sandbox = ScriptSandbox(timeout=1)

        # Use a busy loop instead of time.sleep since time may be blocked
        script = """
i = 0
while True:
    i += 1
"""

        result = sandbox.execute(script)

        assert result.success is False
        assert result.status == ExecutionStatus.TIMEOUT

    def test_multiple_validation_errors(self):
        """Test script with multiple validation errors"""
        sandbox = ScriptSandbox(strict_validation=True)

        script = """
import os
import subprocess
exec('print("bad")')
eval('1+1')
"""

        result = sandbox.execute(script)

        assert result.success is False
        assert result.status == ExecutionStatus.VALIDATION_FAILED

        # Should have multiple errors detected
        validation_metadata = result.metadata.get("validation", {})
        errors = validation_metadata.get("errors", [])
        assert len(errors) >= 2  # Should catch os, subprocess, exec, eval

    def test_subprocess_vs_inline_execution(self):
        """Test difference between subprocess and inline execution"""
        subprocess_sandbox = ScriptSandbox(use_subprocess=True, timeout=5)
        inline_sandbox = ScriptSandbox(use_subprocess=False, timeout=5)

        script = """
x = 42
print(f"Value: {x}")
"""

        subprocess_result = subprocess_sandbox.execute(script)
        inline_result = inline_sandbox.execute(script)

        # Both should succeed
        assert subprocess_result.success is True
        assert inline_result.success is True

        # Both should have output
        assert "Value: 42" in subprocess_result.output
        assert "Value: 42" in inline_result.output
