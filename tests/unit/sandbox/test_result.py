"""
Unit tests for sandbox result structures
"""

from datetime import datetime

import pytest

from ai_designer.sandbox.result import (
    ExecutionResult,
    ExecutionStatus,
    ValidationResult,
)


class TestExecutionResult:
    """Test ExecutionResult dataclass"""

    def test_success_result(self):
        """Test successful execution result"""
        result = ExecutionResult(
            success=True,
            status=ExecutionStatus.SUCCESS,
            output="Hello, World!",
            execution_time=0.123,
        )

        assert result.success is True
        assert result.status == ExecutionStatus.SUCCESS
        assert result.output == "Hello, World!"
        assert result.error == ""
        assert result.execution_time == 0.123
        assert isinstance(result.timestamp, datetime)

    def test_failed_result(self):
        """Test failed execution result"""
        result = ExecutionResult(
            success=False,
            status=ExecutionStatus.EXECUTION_FAILED,
            error="Script crashed",
            exit_code=1,
        )

        assert result.success is False
        assert result.status == ExecutionStatus.EXECUTION_FAILED
        assert result.error == "Script crashed"
        assert result.exit_code == 1

    def test_to_dict_serialization(self):
        """Test result serialization to dict"""
        result = ExecutionResult(
            success=True,
            status=ExecutionStatus.SUCCESS,
            output="test output",
            created_objects=["Box001", "Cylinder001"],
        )

        data = result.to_dict()

        assert data["success"] is True
        assert data["status"] == "success"
        assert data["output"] == "test output"
        assert data["created_objects"] == ["Box001", "Cylinder001"]
        assert "timestamp" in data


class TestValidationResult:
    """Test ValidationResult dataclass"""

    def test_valid_script(self):
        """Test validation result for valid script"""
        result = ValidationResult(
            valid=True,
            allowed_modules=["FreeCAD", "Part"],
        )

        assert result.valid is True
        assert len(result.errors) == 0
        assert result.allowed_modules == ["FreeCAD", "Part"]

    def test_invalid_script(self):
        """Test validation result for invalid script"""
        result = ValidationResult(
            valid=False,
            errors=["Blocked module: os", "Blocked operation: exec()"],
            blocked_operations=["exec"],
        )

        assert result.valid is False
        assert len(result.errors) == 2
        assert "Blocked module: os" in result.errors
        assert "exec" in result.blocked_operations

    def test_warnings(self):
        """Test validation with warnings"""
        result = ValidationResult(
            valid=True,
            warnings=["Unusual import detected"],
        )

        assert result.valid is True
        assert len(result.warnings) == 1
        assert result.warnings[0] == "Unusual import detected"

    def test_to_dict_serialization(self):
        """Test validation result serialization"""
        result = ValidationResult(
            valid=False,
            errors=["Error 1"],
            warnings=["Warning 1"],
        )

        data = result.to_dict()

        assert data["valid"] is False
        assert data["errors"] == ["Error 1"]
        assert data["warnings"] == ["Warning 1"]
