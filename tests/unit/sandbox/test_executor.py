"""
Unit tests for script executor
"""

import time

import pytest

from ai_designer.sandbox.executor import ScriptExecutor
from ai_designer.sandbox.result import ExecutionStatus


class TestScriptExecutor:
    """Test subprocess script execution"""

    def test_successful_execution(self):
        """Test successful script execution"""
        executor = ScriptExecutor(timeout=5)

        script = """
print("Hello from subprocess!")
result = 2 + 2
print(f"2 + 2 = {result}")
"""

        result = executor.execute(script)

        assert result.success is True
        assert result.status == ExecutionStatus.SUCCESS
        assert "Hello from subprocess!" in result.output
        assert "2 + 2 = 4" in result.output
        assert result.exit_code == 0

    def test_execution_timeout(self):
        """Test timeout protection"""
        executor = ScriptExecutor(timeout=1)

        script = """
import time
time.sleep(10)  # This should timeout
"""

        result = executor.execute(script)

        assert result.success is False
        assert result.status == ExecutionStatus.TIMEOUT
        assert "timed out" in result.error.lower()

    def test_execution_error(self):
        """Test handling of script errors"""
        executor = ScriptExecutor(timeout=5)

        script = """
# This will raise an error
undefined_variable = nonexistent_var + 10
"""

        result = executor.execute(script)

        assert result.success is False
        assert result.status == ExecutionStatus.EXECUTION_FAILED
        assert result.exit_code != 0
        assert len(result.error) > 0

    def test_context_injection(self):
        """Test context variable injection"""
        executor = ScriptExecutor(timeout=5)

        script = """
# Access injected context
name = _context['name']
value = _context['value']
print(f"Name: {name}, Value: {value}")
"""

        context = {"name": "test_param", "value": 42}
        result = executor.execute(script, context=context)

        assert result.success is True
        assert "Name: test_param" in result.output
        assert "Value: 42" in result.output

    def test_execution_time_tracking(self):
        """Test execution time is tracked"""
        executor = ScriptExecutor(timeout=5)

        script = """
import time
time.sleep(0.1)
"""

        result = executor.execute(script)

        assert result.success is True
        assert result.execution_time >= 0.1
        assert result.execution_time < 1.0

    def test_inline_execution(self):
        """Test inline execution (same process)"""
        executor = ScriptExecutor()

        script = """
result = 10 * 5
print(f"Result: {result}")
"""

        local_env = {}
        result = executor.execute_inline(script, local_env=local_env)

        assert result.success is True
        assert result.status == ExecutionStatus.SUCCESS
        assert "Result: 50" in result.output
        assert local_env.get("result") == 50

    def test_inline_error_handling(self):
        """Test inline execution error handling"""
        executor = ScriptExecutor()

        script = """
raise ValueError("Test error")
"""

        result = executor.execute_inline(script)

        assert result.success is False
        assert result.status == ExecutionStatus.EXECUTION_FAILED
        assert "ValueError" in result.error or "Test error" in result.error

    def test_restricted_builtins_inline(self):
        """Test that dangerous builtins are restricted in inline execution"""
        executor = ScriptExecutor()

        script = """
# These should not be available
try:
    exec('print("bad")')
except (NameError, TypeError):
    print("exec blocked")

try:
    eval('1+1')
except (NameError, TypeError):
    print("eval blocked")

try:
    open('/tmp/test', 'w')
except (NameError, TypeError):
    print("open blocked")
"""

        result = executor.execute_inline(script)

        assert result.success is True
        # All dangerous operations should be blocked
        assert "exec blocked" in result.output
        assert "eval blocked" in result.output
        assert "open blocked" in result.output
