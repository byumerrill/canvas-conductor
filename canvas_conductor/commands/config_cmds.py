"""Config commands: show, validate, courses."""
from __future__ import annotations

import typer

from ..client import get_client
from ..config import (
    find_config_file,
    find_env_file,
    get_courses,
    get_defaults,
    redact_token,
    require_credentials,
)
from ..utils.output import format_output
from ._common import emit, handle_canvas_error

app = typer.Typer(name="config", help="Inspect and validate configuration")


@app.command("show")
def show_config():
    """Pretty-print current config (token redacted)."""
    try:
        env_path = find_env_file()
        cfg_path = find_config_file()
        emit(f".env file:    {env_path or '(not found)'}")
        emit(f"config.toml:  {cfg_path or '(not found)'}")
        emit("")

        try:
            base_url, token = require_credentials()
            emit(f"CANVAS_BASE_URL = {base_url}")
            emit(f"CANVAS_TOKEN    = {redact_token(token)}")
        except Exception as exc:
            emit(f"Credentials:    (not configured) — {exc}")

        emit("")
        defaults = get_defaults()
        if defaults:
            emit("[defaults]")
            for k, v in defaults.items():
                emit(f"  {k} = {v}")
            emit("")

        courses = get_courses()
        if courses:
            emit("[courses]")
            for key, entry in courses.items():
                emit(
                    f"  {key:<12} id={entry.get('id')}  "
                    f"name={entry.get('name', '')}  "
                    f"term={entry.get('term', '')}"
                )
        else:
            emit("[courses] (none configured)")
    except Exception as exc:
        raise handle_canvas_error(exc)


@app.command("validate")
def validate_config(verbose: bool = typer.Option(False, "-v", "--verbose")):
    """Confirm the API token works and list accessible courses."""
    try:
        client = get_client(verbose=verbose)
        me = client.get("/users/self")
        emit(
            f"OK — authenticated as {me.get('name')} "
            f"(id={me.get('id')}, login={me.get('login_id')})"
        )
        emit("")
        emit("Accessible courses (first page):")
        courses = client.get(
            "/courses",
            params={"per_page": 25, "enrollment_state": "active"},
        )
        if not courses:
            emit("  (none)")
            return
        cols = [("ID", "id"), ("Name", "name"), ("Code", "course_code")]
        emit(format_output(courses, cols, "table"))
    except Exception as exc:
        raise handle_canvas_error(exc)


@app.command("courses")
def list_configured_courses(
    output: str = typer.Option("table", "-o", "--output"),
):
    """List the courses defined in config.toml with their Canvas IDs."""
    try:
        courses = get_courses()
        if not courses:
            emit("No courses configured. Add a [courses.<key>] block to config.toml.")
            raise typer.Exit(code=0)
        rows = [
            {"key": k, "id": v.get("id"), "name": v.get("name"), "term": v.get("term")}
            for k, v in courses.items()
        ]
        cols = [("Key", "key"), ("Canvas ID", "id"), ("Name", "name"), ("Term", "term")]
        emit(format_output(rows, cols, output))
    except typer.Exit:
        raise
    except Exception as exc:
        raise handle_canvas_error(exc)
