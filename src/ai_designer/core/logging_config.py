"""
Structured Logging Configuration for AI Designer

Provides centralized, production-ready logging with:
- Structured JSON logs for production
- Human-readable colored output for development
- Contextual logging with request IDs and user info
- Log levels per module
- Performance tracking
"""

import logging
import logging.config
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import structlog


def configure_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    json_logs: bool = False,
    development: bool = True,
) -> None:
    """
    Configure structured logging for the application.

    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for log output
        json_logs: Use JSON format for logs (recommended for production)
        development: Enable development-friendly features (colors, pretty print)
    """
    # Configure standard library logging
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.processors.JSONRenderer(),
            },
            "colored": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.dev.ConsoleRenderer(colors=True),
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "colored" if development and not json_logs else "json",
                "stream": sys.stdout,
            },
        },
        "root": {
            "level": log_level,
            "handlers": ["console"],
        },
    }

    # Add file handler if log_file specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        logging_config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": log_level,
            "formatter": "json",
            "filename": str(log_path),
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
        }
        logging_config["root"]["handlers"].append("file")

    logging.config.dictConfig(logging_config)

    # Configure structlog processors
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # Add development-friendly processors
    if development and not json_logs:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structlog logger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("user_action", action="create_box", user_id=123)
    """
    return structlog.get_logger(name)


def bind_context(**kwargs: Any) -> None:
    """
    Bind context variables that will be included in all subsequent logs.

    Args:
        **kwargs: Context variables to bind (e.g., request_id, user_id, session_id)

    Example:
        >>> bind_context(request_id="abc123", user_id=42)
        >>> logger.info("processing_request")  # Will include request_id and user_id
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_context() -> None:
    """Clear all bound context variables."""
    structlog.contextvars.clear_contextvars()


def log_function_call(func):
    """
    Decorator to automatically log function calls with parameters and execution time.

    Example:
        >>> @log_function_call
        >>> def create_box(width, height, depth):
        >>>     # Implementation
        >>>     pass
    """
    import functools
    import time

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start_time = time.time()

        logger.debug(
            "function_call_start",
            function=func.__name__,
            args=args[:3],  # Limit args to avoid huge logs
            kwargs={k: v for k, v in list(kwargs.items())[:5]},
        )

        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time

            logger.debug(
                "function_call_success",
                function=func.__name__,
                duration_seconds=round(duration, 3),
            )

            return result
        except Exception as e:
            duration = time.time() - start_time

            logger.error(
                "function_call_error",
                function=func.__name__,
                error=str(e),
                error_type=type(e).__name__,
                duration_seconds=round(duration, 3),
                exc_info=True,
            )
            raise

    return wrapper


# Initialize with sensible defaults
configure_logging(
    log_level="INFO",
    development=True,
    json_logs=False,
)
