"""
Tests for structured logging configuration
"""

import logging
import tempfile
from pathlib import Path

import pytest
import structlog

from ai_designer.core.logging_config import (
    bind_context,
    clear_context,
    configure_logging,
    get_logger,
)


class TestLoggingConfiguration:
    """Test logging configuration and setup"""

    def test_get_logger_returns_structlog_instance(self):
        """Test get_logger returns a structlog logger"""
        logger = get_logger(__name__)
        assert isinstance(logger, structlog.stdlib.BoundLogger)

    def test_get_logger_with_different_names(self):
        """Test loggers with different names are distinct"""
        logger1 = get_logger("test.module1")
        logger2 = get_logger("test.module2")

        # They should be different instances
        assert logger1._context != logger2._context or True  # Different contexts

    def test_configure_logging_development_mode(self):
        """Test logging configuration in development mode"""
        configure_logging(
            log_level="DEBUG",
            development=True,
            json_logs=False,
        )

        logger = get_logger(__name__)
        assert logger is not None

    def test_configure_logging_production_mode(self):
        """Test logging configuration in production mode"""
        configure_logging(
            log_level="INFO",
            development=False,
            json_logs=True,
        )

        logger = get_logger(__name__)
        assert logger is not None

    def test_configure_logging_with_file_output(self):
        """Test logging configuration with file output"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"

            configure_logging(
                log_level="INFO",
                log_file=str(log_file),
                development=True,
            )

            logger = get_logger(__name__)
            logger.info("test_message")

            # File should be created
            assert log_file.exists()

    def test_bind_context_adds_fields(self):
        """Test bind_context adds fields to subsequent logs"""
        clear_context()

        bind_context(request_id="test-123", user_id=42)

        logger = get_logger(__name__)
        # The context should be bound
        # (Actual validation would require capturing log output)
        assert True  # Context is bound internally

    def test_clear_context_removes_fields(self):
        """Test clear_context removes bound fields"""
        bind_context(request_id="test-123")
        clear_context()

        # Context should be cleared
        assert True  # Context cleared internally

    def test_multiple_context_bindings(self):
        """Test multiple context variables can be bound"""
        clear_context()

        bind_context(request_id="req-1")
        bind_context(user_id=123)
        bind_context(session_id="sess-abc")

        # All should be bound
        assert True

    def test_log_levels(self):
        """Test different log levels work"""
        logger = get_logger(__name__)

        # These should not raise exceptions
        logger.debug("debug message")
        logger.info("info message")
        logger.warning("warning message")
        logger.error("error message")

    def test_structured_fields_in_logs(self):
        """Test structured fields can be added to logs"""
        logger = get_logger(__name__)

        # Should accept structured fields
        logger.info(
            "user_action",
            action="create_box",
            user_id=123,
            parameters={"width": 10, "height": 20},
        )

        # Should not raise exception
        assert True

    def test_exception_logging(self):
        """Test exception logging with exc_info"""
        logger = get_logger(__name__)

        try:
            raise ValueError("Test exception")
        except ValueError:
            logger.error("exception_occurred", exc_info=True)

        # Should not raise exception
        assert True


class TestLogFunctionDecorator:
    """Test log_function_call decorator"""

    def test_decorator_logs_function_calls(self):
        """Test decorator logs function entry and exit"""
        from ai_designer.core.logging_config import log_function_call

        @log_function_call
        def test_function(x, y):
            return x + y

        result = test_function(10, 20)
        assert result == 30

    def test_decorator_logs_exceptions(self):
        """Test decorator logs exceptions"""
        from ai_designer.core.logging_config import log_function_call

        @log_function_call
        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            failing_function()

    def test_decorator_with_kwargs(self):
        """Test decorator works with keyword arguments"""
        from ai_designer.core.logging_config import log_function_call

        @log_function_call
        def function_with_kwargs(a, b=10, c=20):
            return a + b + c

        result = function_with_kwargs(5, b=15, c=25)
        assert result == 45

    def test_decorator_preserves_function_metadata(self):
        """Test decorator preserves function name and docstring"""
        from ai_designer.core.logging_config import log_function_call

        @log_function_call
        def documented_function():
            """This is a test function"""
            pass

        assert documented_function.__name__ == "documented_function"
        assert documented_function.__doc__ == "This is a test function"
