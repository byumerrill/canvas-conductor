"""Assignment commands: list, show, create, update, delete, duplicate, bulk-dates."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

import typer

from ..client import get_client
from ..config import get_course_id
from ..utils.output import format_output
from ._common import confirm_or_abort, emit, handle_canvas_error, prefix_keys

app = typer.Typer(name="assignments", help="Manage assignments")


ASSIGNMENT_COLUMNS = [
    ("ID", "id"),
    ("Name", "name"),
    ("Points", "points_possible"),
    ("Due", "due_at"),
    ("Published", "published"),
    ("Group", "assignment_group_id"),
]


@app.command("list")
def list_assignments(
    course: str = typer.Option(None, "-c", "--course"),
    bucket: str = typer.Option(
        None,
        "--bucket",
        help="past, overdue, undated, ungraded, unsubmitted, upcoming, future",
    ),
    search: str = typer.Option(None, "--search"),
    group_id: int = typer.Option(None, "--group-id"),
    output: str = typer.Option("table", "-o", "--output"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """List assignments in a course."""
    try:
        client = get_client(verbose=verbose)
        cid = get_course_id(course)
        params: dict = {}
        if bucket:
            params["bucket"] = bucket
        if search:
            params["search_term"] = search
        if group_id:
            params["assignment_group_id"] = group_id
        items = client.get_all(f"/courses/{cid}/assignments", params=params)
        emit(format_output(items, ASSIGNMENT_COLUMNS, output))
    except Exception as exc:
        raise handle_canvas_error(exc)


@app.command("show")
def show_assignment(
    assignment_id: int = typer.Option(..., "--id"),
    course: str = typer.Option(None, "-c", "--course"),
    output: str = typer.Option("table", "-o", "--output"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """Show a single assignment."""
    try:
        client = get_client(verbose=verbose)
        cid = get_course_id(course)
        data = client.get(f"/courses/{cid}/assignments/{assignment_id}")
        if output == "table":
            from ..utils.output import format_kv

            emit(format_kv(data))
        else:
            emit(format_output(data, [], output))
    except Exception as exc:
        raise handle_canvas_error(exc)


@app.command("create")
def create_assignment(
    name: str = typer.Option(..., "--name"),
    course: str = typer.Option(None, "-c", "--course"),
    points: float = typer.Option(None, "--points"),
    submission_type: str = typer.Option(
        None,
        "--type",
        help="online_upload, online_text_entry, online_url, none, etc.",
    ),
    due: str = typer.Option(None, "--due", help="ISO 8601 datetime"),
    unlock_at: str = typer.Option(None, "--unlock-at"),
    lock_at: str = typer.Option(None, "--lock-at"),
    published: bool = typer.Option(False, "--published"),
    group_id: int = typer.Option(None, "--group-id"),
    description: str = typer.Option(None, "--description"),
    grading_type: str = typer.Option(
        None, "--grading-type", help="points, percent, pass_fail, letter_grade, gpa_scale, not_graded"
    ),
    dry_run: bool = typer.Option(False, "--dry-run"),
    yes: bool = typer.Option(False, "-y", "--yes"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """Create an assignment."""
    try:
        cid = get_course_id(course)
        payload = prefix_keys(
            "assignment",
            {
                "name": name,
                "points_possible": points,
                "submission_types": [submission_type] if submission_type else None,
                "due_at": due,
                "unlock_at": unlock_at,
                "lock_at": lock_at,
                "published": published or None,
                "assignment_group_id": group_id,
                "description": description,
                "grading_type": grading_type,
            },
        )
        if dry_run:
            emit(f"DRY-RUN: POST /courses/{cid}/assignments payload={payload}")
            return
        client = get_client(verbose=verbose)
        result = client.post(f"/courses/{cid}/assignments", data=payload)
        emit(format_output(result, ASSIGNMENT_COLUMNS, "table"))
    except Exception as exc:
        raise handle_canvas_error(exc)


@app.command("update")
def update_assignment(
    assignment_id: int = typer.Option(..., "--id"),
    course: str = typer.Option(None, "-c", "--course"),
    name: str = typer.Option(None, "--name"),
    points: float = typer.Option(None, "--points"),
    due: str = typer.Option(None, "--due"),
    unlock_at: str = typer.Option(None, "--unlock-at"),
    lock_at: str = typer.Option(None, "--lock-at"),
    published: bool = typer.Option(None, "--published"),
    group_id: int = typer.Option(None, "--group-id"),
    description: str = typer.Option(None, "--description"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    yes: bool = typer.Option(False, "-y", "--yes"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """Update an assignment."""
    try:
        cid = get_course_id(course)
        payload = prefix_keys(
            "assignment",
            {
                "name": name,
                "points_possible": points,
                "due_at": due,
                "unlock_at": unlock_at,
                "lock_at": lock_at,
                "published": published,
                "assignment_group_id": group_id,
                "description": description,
            },
        )
        if not payload:
            emit("No fields supplied — nothing to update.")
            return
        if dry_run:
            emit(
                f"DRY-RUN: PUT /courses/{cid}/assignments/{assignment_id} payload={payload}"
            )
            return
        client = get_client(verbose=verbose)
        result = client.put(f"/courses/{cid}/assignments/{assignment_id}", payload)
        emit(format_output(result, ASSIGNMENT_COLUMNS, "table"))
    except Exception as exc:
        raise handle_canvas_error(exc)


@app.command("delete")
def delete_assignment(
    assignment_id: int = typer.Option(..., "--id"),
    course: str = typer.Option(None, "-c", "--course"),
    dry_run: bool = typer.Option(True, "--dry-run/--commit"),
    yes: bool = typer.Option(False, "-y", "--yes"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """Delete an assignment."""
    try:
        cid = get_course_id(course)
        confirm_or_abort(f"Delete assignment {assignment_id}?", yes=yes, dry_run=dry_run)
        client = get_client(verbose=verbose)
        client.delete(f"/courses/{cid}/assignments/{assignment_id}")
        emit(f"Deleted assignment {assignment_id}.")
    except typer.Exit:
        raise
    except Exception as exc:
        raise handle_canvas_error(exc)


@app.command("duplicate")
def duplicate_assignment(
    assignment_id: int = typer.Option(..., "--id"),
    course: str = typer.Option(None, "-c", "--course"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """Duplicate an assignment in place."""
    try:
        cid = get_course_id(course)
        if dry_run:
            emit(f"DRY-RUN: POST /courses/{cid}/assignments/{assignment_id}/duplicate")
            return
        client = get_client(verbose=verbose)
        result = client.post(f"/courses/{cid}/assignments/{assignment_id}/duplicate")
        emit(format_output(result, ASSIGNMENT_COLUMNS, "table"))
    except Exception as exc:
        raise handle_canvas_error(exc)


_DURATION_RE = re.compile(r"^(?P<sign>-?)(?P<n>\d+)(?P<unit>[dhwm])$")


def _parse_shift(value: str) -> timedelta:
    """Parse `7d`, `-3d`, `12h`, `2w`, `30m` into a `timedelta`."""
    m = _DURATION_RE.match(value.strip())
    if not m:
        raise ValueError(
            f"Invalid shift '{value}'. Examples: 7d, -1d, 12h, 2w, 30m"
        )
    sign = -1 if m["sign"] else 1
    n = int(m["n"]) * sign
    unit = m["unit"]
    if unit == "d":
        return timedelta(days=n)
    if unit == "h":
        return timedelta(hours=n)
    if unit == "w":
        return timedelta(weeks=n)
    if unit == "m":
        return timedelta(minutes=n)
    raise ValueError(f"Unknown unit: {unit}")  # pragma: no cover


def _shift_iso(value: str | None, delta: timedelta) -> str | None:
    if not value:
        return None
    # Canvas returns datetimes in ISO 8601 with 'Z' for UTC.
    cleaned = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(cleaned)
    new = dt + delta
    if new.tzinfo is None:
        new = new.replace(tzinfo=timezone.utc)
    return new.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@app.command("bulk-dates")
def bulk_dates(
    course: str = typer.Option(None, "-c", "--course"),
    shift: str = typer.Option(..., "--shift", help="e.g., 7d, -1d, 12h, 2w"),
    fields: str = typer.Option(
        "due_at,unlock_at,lock_at",
        "--fields",
        help="Comma-separated date fields to shift",
    ),
    dry_run: bool = typer.Option(True, "--dry-run/--commit"),
    yes: bool = typer.Option(False, "-y", "--yes"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """Shift due/unlock/lock dates on every assignment by a duration."""
    try:
        cid = get_course_id(course)
        delta = _parse_shift(shift)
        target_fields = [f.strip() for f in fields.split(",") if f.strip()]
        client = get_client(verbose=verbose)
        items = client.get_all(f"/courses/{cid}/assignments")

        plan: list[tuple[int, str, dict]] = []
        for item in items:
            inner: dict = {}
            for field in target_fields:
                shifted = _shift_iso(item.get(field), delta)
                if shifted:
                    inner[field] = shifted
            if inner:
                plan.append((item["id"], item.get("name", ""), {"assignment": inner}))

        if not plan:
            emit("No assignments have dates to shift.")
            return

        if dry_run:
            emit(f"DRY-RUN: would shift {len(plan)} assignments by {shift}:")
            for aid, name, payload in plan:
                emit(f"  - [{aid}] {name}: {payload}")
            return

        if not yes and not typer.confirm(
            f"Shift {len(plan)} assignments by {shift}?", default=False
        ):
            emit("Aborted.")
            raise typer.Exit(code=1)

        for aid, _name, payload in plan:
            client.put(f"/courses/{cid}/assignments/{aid}", payload)
        emit(f"Shifted {len(plan)} assignments by {shift}.")
    except typer.Exit:
        raise
    except ValueError as exc:
        emit(f"ERROR: {exc}")
        raise typer.Exit(code=2)
    except Exception as exc:
        raise handle_canvas_error(exc)
