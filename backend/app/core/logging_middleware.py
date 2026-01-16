"""
Logging Middleware for OccultaShield FastAPI Application.

Provides request/response logging with automatic request ID generation
and propagation for distributed tracing.

Features:
- Automatic X-Request-ID header generation/extraction
- Request duration measurement
- Structured logging of request/response details
- Context propagation for async request tracing

Example:
    >>> from fastapi import FastAPI
    >>> from app.core.logging_middleware import LoggingMiddleware
    >>> app = FastAPI()
    >>> app.add_middleware(LoggingMiddleware)
"""

import time
import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from config.logging_config import (
    get_logger,
    set_request_id,
    clear_request_id,
)

logger = get_logger("app.middleware.logging")


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for request/response logging.

    Intercepts all HTTP requests to:
    - Generate or extract X-Request-ID
    - Log request details on entry
    - Log response details with timing on exit
    - Propagate request ID via context variables
    """

    # Paths to exclude from logging (health checks, metrics, etc.)
    EXCLUDED_PATHS = {
        "/health",
        "/healthz",
        "/ready",
        "/metrics",
        "/favicon.ico",
    }

    # Paths to log at DEBUG level instead of INFO
    DEBUG_PATHS = {
        "/api/v1/video/",  # Progress SSE endpoints are noisy
    }

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """
        Process request through the logging pipeline.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/route handler

        Returns:
            HTTP response with X-Request-ID header added
        """
        # Skip logging for excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        # Extract or generate request ID
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())

        # Set request ID in context for downstream logging
        set_request_id(request_id)

        # Determine log level based on path
        is_debug_path = any(
            request.url.path.startswith(p) for p in self.DEBUG_PATHS
            if "progress" in request.url.path
        )

        # Log request start
        client_ip = self._get_client_ip(request)

        if not is_debug_path:
            logger.info(
                f"→ {request.method} {request.url.path}",
                extra={
                    "extra_data": {
                        "method": request.method,
                        "path": request.url.path,
                        "client_ip": client_ip,
                        "query": str(request.query_params) if request.query_params else None,
                    }
                },
            )

        # Process request and measure time
        start_time = time.perf_counter()
        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            # Log response
            log_method = logger.debug if is_debug_path else logger.info
            status_emoji = self._get_status_emoji(response.status_code)

            log_method(
                f"← {status_emoji} {response.status_code} {request.method} {request.url.path} ({duration_ms:.1f}ms)",
                extra={
                    "extra_data": {
                        "status_code": response.status_code,
                        "duration_ms": round(duration_ms, 2),
                        "method": request.method,
                        "path": request.url.path,
                    }
                },
            )

            return response

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"✗ Exception during {request.method} {request.url.path}: {e}",
                exc_info=True,
                extra={
                    "extra_data": {
                        "duration_ms": round(duration_ms, 2),
                        "method": request.method,
                        "path": request.url.path,
                        "error": str(e),
                    }
                },
            )
            raise

        finally:
            # Clear request ID from context
            clear_request_id()

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request, handling proxies."""
        # Check X-Forwarded-For header (from reverse proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to direct client
        if request.client:
            return request.client.host

        return "unknown"

    def _get_status_emoji(self, status_code: int) -> str:
        """Get an emoji indicator for the status code."""
        if status_code < 300:
            return "✓"
        elif status_code < 400:
            return "↪"
        elif status_code < 500:
            return "⚠"
        else:
            return "✗"
