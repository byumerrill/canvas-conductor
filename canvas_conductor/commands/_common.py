"""Shared helpers for command modules.

These keep each command short and consistent. The CLI surface lives in
each `commands/<group>.py` file; helpers here only handle plumbing
(error formatting, confirmation prompts, etc.).
"""
from __future__ import annotations

import sys
from typing import Any

import typer
from rich.console import Console

from ..exceptions import (
    CanvasAuthError,
    CanvasError,
    CanvasNotFoundError,
    CanvasPermissionError,
    CanvasRateLimitError,
    CanvasValidationError,
    ConfigError,
)


err_console = Console(stderr=True)


def emit(text: str) -> None:
    """Print user-facing output to stdout (no markup interpretation)."""
    sys.stdout.write(text)
    if not text.endswith("\n"):
        sys.stdout.write("\n")


def handle_canvas_error(exc: Exception) -> "typer.Exit":
    """Format a Canvas/Config error for the user and return an Exit code."""
    if isinstance(exc, ConfigError):
        err_console.print(f"[red]ERROR:[/red] {exc}")
        return typer.Exit(code=2)

    if isinstance(exc, CanvasAuthError):
        err_console.print(
            "[red]ERROR:[/red] Authentication failed (401).\n"
            "Your Canvas token may have expired. Regenerate it under "
            "Account > Settings > Approved Integrations, then update your "
            ".env file."
        )
        return typer.Exit(code=3)

    if isinstance(exc, CanvasPermissionError):
        err_console.print(
            f"[red]ERROR:[/red] Permission denied (403). {exc.message}"
        )
        return typer.Exit(code=4)

    if isinstance(exc, CanvasNotFoundError):
        err_console.print(
            f"[red]ERROR:[/red] Resource not found (404). {exc.message}"
        )
        return typer.Exit(code=5)

    if isinstance(exc, CanvasValidationError):
        err_console.print(
            f"[red]ERROR:[/red] Canvas rejected the request (422): {exc.message}"
        )
        return typer.Exit(code=6)

    if isinstance(exc, CanvasRateLimitError):
        err_console.print(
            "[red]ERROR:[/red] Rate limit exceeded (429). Wait a few minutes "
            "and try again."
        )
        return typer.Exit(code=7)

    if isinstance(exc, CanvasError):
        err_console.print(f"[red]ERROR:[/red] {exc}")
        return typer.Exit(code=8)

    raise exc


def confirm_or_abort(message: str, yes: bool, dry_run: bool) -> None:
    """Standard confirmation flow for destructive ops."""
    if dry_run:
        err_console.print(f"[yellow]DRY-RUN:[/yellow] {message}")
        raise typer.Exit(code=0)
    if yes:
        return
    if not typer.confirm(message, default=False):
        err_console.print("Aborted.")
        raise typer.Exit(code=1)


def parse_kv_list(value: str | None) -> dict[str, str]:
    """Parse `key=value,key2=value2` into a dict. Returns {} on empty input."""
    if not value:
        return {}
    out: dict[str, str] = {}
    for part in value.split(","):
        if not part.strip():
            continue
        key, _, val = part.partition("=")
        out[key.strip()] = val.strip()
    return out


def prefix_keys(prefix: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Wrap each key in `prefix[key]` form (Canvas's standard request format)."""
    result: dict[str, Any] = {}
    for k, v in payload.items():
        if v is None:
            continue
        if isinstance(v, list):
            result[f"{prefix}[{k}][]"] = v
        else:
            result[f"{prefix}[{k}]"] = v
    return result
