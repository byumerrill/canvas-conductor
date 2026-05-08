"""Typed exceptions for Canvas API errors.

Each exception carries the HTTP status code and the response body (when
available) so callers can produce actionable error messages.
"""
from __future__ import annotations


class CanvasError(Exception):
    """Base class for all Canvas API errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        body: str | dict | list | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.body = body

    def __str__(self) -> str:
        if self.status_code is not None:
            return f"[{self.status_code}] {self.message}"
        return self.message


class CanvasAuthError(CanvasError):
    """401 Unauthorized: token missing, invalid, or expired."""


class CanvasPermissionError(CanvasError):
    """403 Forbidden: token lacks required scope or role."""


class CanvasNotFoundError(CanvasError):
    """404 Not Found: resource does not exist or is not visible."""


class CanvasValidationError(CanvasError):
    """422 Unprocessable Entity: request body failed Canvas validation."""


class CanvasRateLimitError(CanvasError):
    """429 Too Many Requests: rate limit exceeded after retries."""


class CanvasServerError(CanvasError):
    """5xx Server Error after retries exhausted."""


class ConfigError(Exception):
    """Configuration error (missing .env, malformed config.toml, etc)."""
