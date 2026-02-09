"""
Tests for custom exception hierarchy
"""

import pytest

from ai_designer.core.exceptions import (
    AIDesignerError,
    APIAuthenticationError,
    APIConnectionError,
    APIError,
    APIRateLimitError,
    CacheError,
    ConfigurationError,
    FreeCADConnectionError,
    FreeCADError,
    FreeCADExecutionError,
    FreeCADNotFoundError,
    GeometryParseError,
    InitializationError,
    LLMAPIKeyError,
    LLMError,
    LLMProviderError,
    LLMResponseError,
    ParameterValidationError,
    ParseError,
    RedisConnectionError,
    ScriptError,
    ScriptExecutionError,
    ScriptTimeoutError,
    ScriptValidationError,
    StateError,
    StateLoadError,
    StateSaveError,
    StateValidationError,
)


class TestExceptionHierarchy:
    """Test exception class hierarchy and inheritance"""

    def test_base_exception_with_message(self):
        """Test base exception with simple message"""
        error = AIDesignerError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.details == {}

    def test_base_exception_with_details(self):
        """Test base exception with details dict"""
        details = {"code": 123, "context": "test"}
        error = AIDesignerError("Test error", details=details)
        assert error.message == "Test error"
        assert error.details == details

    def test_configuration_error_inheritance(self):
        """Test ConfigurationError inherits from AIDesignerError"""
        error = ConfigurationError("Config missing")
        assert isinstance(error, AIDesignerError)
        assert isinstance(error, ConfigurationError)

    def test_freecad_error_hierarchy(self):
        """Test FreeCAD error hierarchy"""
        # Base FreeCAD error
        base_error = FreeCADError("FreeCAD error")
        assert isinstance(base_error, AIDesignerError)

        # Specific FreeCAD errors
        not_found = FreeCADNotFoundError("Not found")
        assert isinstance(not_found, FreeCADError)
        assert isinstance(not_found, AIDesignerError)

        exec_error = FreeCADExecutionError("Execution failed")
        assert isinstance(exec_error, FreeCADError)

        conn_error = FreeCADConnectionError("Connection failed")
        assert isinstance(conn_error, FreeCADError)

    def test_script_error_hierarchy(self):
        """Test script error hierarchy"""
        validation_error = ScriptValidationError("Invalid script")
        assert isinstance(validation_error, ScriptError)
        assert isinstance(validation_error, AIDesignerError)

        exec_error = ScriptExecutionError("Execution failed")
        assert isinstance(exec_error, ScriptError)

        timeout_error = ScriptTimeoutError("Timeout")
        assert isinstance(timeout_error, ScriptError)

    def test_llm_error_hierarchy(self):
        """Test LLM error hierarchy"""
        provider_error = LLMProviderError("Provider error")
        assert isinstance(provider_error, LLMError)
        assert isinstance(provider_error, AIDesignerError)

        response_error = LLMResponseError("Invalid response")
        assert isinstance(response_error, LLMError)

        api_key_error = LLMAPIKeyError("Missing API key")
        assert isinstance(api_key_error, LLMError)

    def test_state_error_hierarchy(self):
        """Test state management error hierarchy"""
        load_error = StateLoadError("Load failed")
        assert isinstance(load_error, StateError)
        assert isinstance(load_error, AIDesignerError)

        save_error = StateSaveError("Save failed")
        assert isinstance(save_error, StateError)

        validation_error = StateValidationError("Invalid state")
        assert isinstance(validation_error, StateError)

    def test_api_error_hierarchy(self):
        """Test API error hierarchy"""
        conn_error = APIConnectionError("Connection failed")
        assert isinstance(conn_error, APIError)
        assert isinstance(conn_error, AIDesignerError)

        auth_error = APIAuthenticationError("Auth failed")
        assert isinstance(auth_error, APIError)

        rate_limit_error = APIRateLimitError("Rate limited")
        assert isinstance(rate_limit_error, APIError)

    def test_parse_error_hierarchy(self):
        """Test parsing error hierarchy"""
        geo_error = GeometryParseError("Invalid geometry")
        assert isinstance(geo_error, ParseError)
        assert isinstance(geo_error, AIDesignerError)

    def test_cache_error_hierarchy(self):
        """Test cache error hierarchy"""
        redis_error = RedisConnectionError("Redis connection failed")
        assert isinstance(redis_error, CacheError)
        assert isinstance(redis_error, AIDesignerError)

    def test_exception_details_preserved(self):
        """Test exception details are preserved"""
        details = {
            "file": "test.py",
            "line": 42,
            "context": "validation",
        }
        error = ScriptValidationError("Validation failed", details=details)

        assert error.details["file"] == "test.py"
        assert error.details["line"] == 42
        assert error.details["context"] == "validation"

    def test_exception_can_be_caught_by_base_class(self):
        """Test specific exceptions can be caught by base class"""
        try:
            raise FreeCADNotFoundError("Not found")
        except FreeCADError:
            pass  # Should catch it

        try:
            raise ScriptTimeoutError("Timeout")
        except ScriptError:
            pass  # Should catch it

        try:
            raise LLMProviderError("Provider error")
        except LLMError:
            pass  # Should catch it
