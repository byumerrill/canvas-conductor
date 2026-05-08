"""Course-level commands: list, show, update, settings."""
from __future__ import annotations

import typer

from ..client import get_client
from ..config import get_course_id
from ..utils.output import format_output
from ._common import emit, handle_canvas_error, prefix_keys

app = typer.Typer(name="courses", help="Manage courses (list, show, update, settings)")


COURSE_COLUMNS = [
    ("ID", "id"),
    ("Name", "name"),
    ("Code", "course_code"),
    ("State", "workflow_state"),
    ("Default View", "default_view"),
]


@app.command("list")
def list_courses(
    enrollment_type: str = typer.Option(
        None, "--type", help="teacher, student, ta, observer, designer"
    ),
    enrollment_state: str = typer.Option(
        None, "--state", help="active, invited, completed"
    ),
    output: str = typer.Option("table", "-o", "--output"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """List the authenticated user's courses."""
    try:
        client = get_client(verbose=verbose)
        params: dict = {}
        if enrollment_type:
            params["enrollment_type"] = enrollment_type
        if enrollment_state:
            params["enrollment_state"] = enrollment_state
        params["include[]"] = "term"
        courses = client.get_all("/courses", params=params)
        emit(format_output(courses, COURSE_COLUMNS, output))
    except Exception as exc:
        raise handle_canvas_error(exc)


@app.command("show")
def show_course(
    course: str = typer.Option(None, "-c", "--course"),
    output: str = typer.Option("table", "-o", "--output"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """Show full details for a single course."""
    try:
        client = get_client(verbose=verbose)
        cid = get_course_id(course)
        data = client.get(f"/courses/{cid}", params={"include[]": ["term", "permissions"]})
        emit(format_output(data, COURSE_COLUMNS, output))
    except Exception as exc:
        raise handle_canvas_error(exc)


@app.command("update")
def update_course(
    course: str = typer.Option(None, "-c", "--course"),
    name: str = typer.Option(None, "--name"),
    default_view: str = typer.Option(
        None, "--default-view", help="modules, syllabus, wiki, assignments, feed"
    ),
    syllabus_body: str = typer.Option(None, "--syllabus", help="HTML body for syllabus"),
    start_at: str = typer.Option(None, "--start-at", help="ISO 8601 datetime"),
    end_at: str = typer.Option(None, "--end-at", help="ISO 8601 datetime"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    yes: bool = typer.Option(False, "-y", "--yes"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """Update course-level settings."""
    try:
        cid = get_course_id(course)
        payload = prefix_keys(
            "course",
            {
                "name": name,
                "default_view": default_view,
                "syllabus_body": syllabus_body,
                "start_at": start_at,
                "end_at": end_at,
            },
        )
        if not payload:
            emit("No fields supplied — nothing to update.")
            raise typer.Exit(code=0)

        if dry_run:
            emit(f"DRY-RUN: PUT /courses/{cid} payload={payload}")
            return

        client = get_client(verbose=verbose)
        result = client.put(f"/courses/{cid}", payload)
        emit(format_output(result, COURSE_COLUMNS, "table"))
    except typer.Exit:
        raise
    except Exception as exc:
        raise handle_canvas_error(exc)


@app.command("settings")
def course_settings(
    course: str = typer.Option(None, "-c", "--course"),
    output: str = typer.Option("table", "-o", "--output"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """View course settings (discussion policies, visibility, etc.)."""
    try:
        client = get_client(verbose=verbose)
        cid = get_course_id(course)
        data = client.get(f"/courses/{cid}/settings")
        if output == "table":
            from ..utils.output import format_kv

            emit(format_kv(data))
        else:
            emit(format_output(data, [], output))
    except Exception as exc:
        raise handle_canvas_error(exc)
