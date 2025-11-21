"""Structured logging for FlowCoach with correlation IDs."""

import json
import logging
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

# Context variable for correlation ID
correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Base log structure
        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id.get(),
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)

        # Add user context if available
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id

        if hasattr(record, "action"):
            log_entry["action"] = record.action

        return json.dumps(log_entry)


class CorrelatedLogger:
    """Logger that automatically includes correlation ID."""

    def __init__(self, name: str):
        """Initialize correlated logger."""
        self.logger = logging.getLogger(name)

    def _log_with_context(
        self,
        level: int,
        message: str,
        extra_fields: dict[str, Any] | None = None,
        user_id: str | None = None,
        action: str | None = None,
    ) -> None:
        """Log message with additional context."""
        extra = {}
        if extra_fields:
            extra["extra_fields"] = extra_fields
        if user_id:
            extra["user_id"] = user_id
        if action:
            extra["action"] = action

        self.logger.log(level, message, extra=extra)

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with context."""
        self._log_with_context(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """Log info message with context."""
        self._log_with_context(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with context."""
        self._log_with_context(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        """Log error message with context."""
        self._log_with_context(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs) -> None:
        """Log critical message with context."""
        self._log_with_context(logging.CRITICAL, message, **kwargs)


def setup_structured_logging(log_level: str = "INFO") -> None:
    """Set up structured JSON logging for the application."""
    # Create structured formatter
    formatter = StructuredFormatter()

    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add console handler with structured formatting
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)


def new_correlation_id() -> str:
    """Generate a new correlation ID."""
    return str(uuid.uuid4())


def set_correlation_id(corr_id: str) -> None:
    """Set correlation ID for current context."""
    correlation_id.set(corr_id)


def get_correlation_id() -> str | None:
    """Get current correlation ID."""
    return correlation_id.get()


def with_correlation_id(func):
    """Decorator to automatically generate correlation ID for function."""

    def wrapper(*args, **kwargs):
        if correlation_id.get() is None:
            set_correlation_id(new_correlation_id())
        return func(*args, **kwargs)

    return wrapper


def get_logger(name: str) -> CorrelatedLogger:
    """Get a correlated logger for the given name."""
    return CorrelatedLogger(name)
