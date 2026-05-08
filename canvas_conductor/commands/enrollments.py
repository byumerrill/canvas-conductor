"""Enrollment commands: list, summary."""
from __future__ import annotations

from collections import Counter

import typer

from ..client import get_client
from ..config import get_course_id
from ..utils.output import format_output
from ._common import emit, handle_canvas_error

app = typer.Typer(name="enrollments", help="View course enrollments")


ENROLL_COLUMNS = [
    ("ID", "id"),
    ("User", "user.name"),
    ("Email", "user.email"),
    ("Login", "user.login_id"),
    ("Type", "type"),
    ("State", "enrollment_state"),
]


_TYPE_ALIASES = {
    "student": "StudentEnrollment",
    "teacher": "TeacherEnrollment",
    "ta": "TaEnrollment",
    "observer": "ObserverEnrollment",
    "designer": "DesignerEnrollment",
}


@app.command("list")
def list_enrollments(
    course: str = typer.Option(None, "-c", "--course"),
    type_: str = typer.Option(
        None,
        "--type",
        help="student, teacher, ta, observer, designer (or full Canvas type)",
    ),
    state: str = typer.Option(
        None, "--state", help="active, invited, completed, inactive, rejected"
    ),
    output: str = typer.Option("table", "-o", "--output"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """List enrollments in a course."""
    try:
        client = get_client(verbose=verbose)
        cid = get_course_id(course)
        params: dict = {}
        if type_:
            canvas_type = _TYPE_ALIASES.get(type_.lower(), type_)
            params["type[]"] = canvas_type
        if state:
            params["state[]"] = state
        items = client.get_all(f"/courses/{cid}/enrollments", params=params)
        emit(format_output(items, ENROLL_COLUMNS, output))
    except Exception as exc:
        raise handle_canvas_error(exc)


@app.command("summary")
def summary(
    course: str = typer.Option(None, "-c", "--course"),
    output: str = typer.Option("table", "-o", "--output"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """Show enrollment counts grouped by type and state."""
    try:
        client = get_client(verbose=verbose)
        cid = get_course_id(course)
        items = client.get_all(f"/courses/{cid}/enrollments")
        counts: Counter[tuple[str, str]] = Counter()
        for e in items:
            counts[(e.get("type", "?"), e.get("enrollment_state", "?"))] += 1
        rows = [
            {"type": t, "state": s, "count": n}
            for (t, s), n in sorted(counts.items())
        ]
        cols = [("Type", "type"), ("State", "state"), ("Count", "count")]
        emit(format_output(rows, cols, output))
    except Exception as exc:
        raise handle_canvas_error(exc)
