"""
Unified Logging Configuration for OccultaShield Backend.

Provides centralized logging setup with environment-aware formatting:
- Development: Colored text output with timestamps
- Production: JSON structured logs for aggregation

Features:
- Color-coded log levels for terminal output
- JSON formatter for production environments
- Request ID propagation via contextvars
- Configurable log levels per module

Example:
    >>> from app.config.logging_config import setup_logging, get_logger
    >>> setup_logging()
    >>> logger = get_logger(__name__)
    >>> logger.info("Processing started", extra={"video_id": "vid_123"})
"""

import logging
import logging.config
import os
import sys
from contextvars import ContextVar
from datetime import datetime
from typing import Any

# Context variable for request ID propagation across async calls
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


# =============================================================================
# FORMATTERS
# =============================================================================

class ColoredFormatter(logging.Formatter):
    """
    Colored console formatter for development environments.

    Applies ANSI color codes to log levels for improved readability
    in terminal output.
    """

    COLORS = {
        "DEBUG": "\033[36m",    # Cyan
        "INFO": "\033[32m",     # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",    # Red
        "CRITICAL": "\033[35m", # Magenta
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    def format(self, record: logging.LogRecord) -> str:
        # Get request ID from context if available
        req_id = request_id_var.get()
        req_id_str = f" [{req_id[:8]}]" if req_id else ""

        # Apply colors
        level_color = self.COLORS.get(record.levelname, "")
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        # Format: HH:MM:SS.mmm LEVEL [req_id] logger_name: message
        formatted = (
            f"{self.DIM}{timestamp}{self.RESET} "
            f"{level_color}{self.BOLD}{record.levelname:8}{self.RESET}"
            f"{self.DIM}{req_id_str}{self.RESET} "
            f"{self.DIM}{record.name}:{self.RESET} "
            f"{record.getMessage()}"
        )

        # Add exception info if present
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"

        return formatted


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for production environments.

    Outputs structured JSON logs suitable for log aggregation
    systems like ELK, Datadog, or CloudWatch.
    """

    def format(self, record: logging.LogRecord) -> str:
        import json

        log_entry: dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add request ID if available
        req_id = request_id_var.get()
        if req_id:
            log_entry["request_id"] = req_id

        # Add extra fields from record
        if hasattr(record, "video_id"):
            log_entry["video_id"] = record.video_id
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id
        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms
        if hasattr(record, "extra_data"):
            log_entry.update(record.extra_data)

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


# =============================================================================
# CONFIGURATION
# =============================================================================

def get_log_level() -> str:
    """Get log level from environment, defaulting to INFO."""
    return os.getenv("LOG_LEVEL", "INFO").upper()


def is_production() -> bool:
    """Check if running in production mode."""
    env = os.getenv("ENVIRONMENT", "development").lower()
    return env in ("production", "prod")


def setup_logging() -> None:
    """
    Initialize the logging system with environment-appropriate settings.

    Call this once at application startup (in main.py).

    Environment Variables:
        LOG_LEVEL: Set to DEBUG, INFO, WARNING, ERROR (default: INFO)
        ENVIRONMENT: Set to 'production' for JSON output (default: development)
    """
    log_level = get_log_level()
    use_json = is_production()

    # Choose formatter based on environment
    if use_json:
        formatter = JSONFormatter()
    else:
        formatter = ColoredFormatter()

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Configure specific loggers
    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("neo4j").setLevel(logging.WARNING)

    # Application loggers at configured level
    logging.getLogger("app").setLevel(log_level)

    # Log startup message
    logger = logging.getLogger("app.config.logging")
    logger.info(
        f"Logging initialized: level={log_level}, format={'JSON' if use_json else 'colored'}"
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Configured logger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Operation completed", extra={"items": 42})
    """
    return logging.getLogger(name)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def set_request_id(request_id: str) -> None:
    """Set the current request ID in context."""
    request_id_var.set(request_id)


def get_request_id() -> str | None:
    """Get the current request ID from context."""
    return request_id_var.get()


def clear_request_id() -> None:
    """Clear the request ID from context."""
    request_id_var.set(None)
