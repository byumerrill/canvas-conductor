"""Assignment group commands: list, create, update, delete."""
from __future__ import annotations

import typer

from ..client import get_client
from ..config import get_course_id
from ..utils.output import format_output
from ._common import confirm_or_abort, emit, handle_canvas_error

app = typer.Typer(name="groups", help="Manage assignment groups (categories with weights)")


GROUP_COLUMNS = [
    ("ID", "id"),
    ("Position", "position"),
    ("Name", "name"),
    ("Weight (%)", "group_weight"),
]


@app.command("list")
def list_groups(
    course: str = typer.Option(None, "-c", "--course"),
    output: str = typer.Option("table", "-o", "--output"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """List assignment groups."""
    try:
        client = get_client(verbose=verbose)
        cid = get_course_id(course)
        items = client.get_all(f"/courses/{cid}/assignment_groups")
        emit(format_output(items, GROUP_COLUMNS, output))
    except Exception as exc:
        raise handle_canvas_error(exc)


@app.command("create")
def create_group(
    name: str = typer.Option(..., "--name"),
    course: str = typer.Option(None, "-c", "--course"),
    position: int = typer.Option(None, "--position"),
    weight: float = typer.Option(None, "--weight", help="Group weight as a percentage"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """Create an assignment group."""
    try:
        cid = get_course_id(course)
        payload = {"name": name, "position": position, "group_weight": weight}
        payload = {k: v for k, v in payload.items() if v is not None}
        if dry_run:
            emit(f"DRY-RUN: POST /courses/{cid}/assignment_groups payload={payload}")
            return
        client = get_client(verbose=verbose)
        result = client.post(f"/courses/{cid}/assignment_groups", data=payload)
        emit(format_output(result, GROUP_COLUMNS, "table"))
    except Exception as exc:
        raise handle_canvas_error(exc)


@app.command("update")
def update_group(
    group_id: int = typer.Option(..., "--id"),
    course: str = typer.Option(None, "-c", "--course"),
    name: str = typer.Option(None, "--name"),
    position: int = typer.Option(None, "--position"),
    weight: float = typer.Option(None, "--weight"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """Update an assignment group."""
    try:
        cid = get_course_id(course)
        payload = {"name": name, "position": position, "group_weight": weight}
        payload = {k: v for k, v in payload.items() if v is not None}
        if not payload:
            emit("No fields supplied — nothing to update.")
            return
        if dry_run:
            emit(f"DRY-RUN: PUT /courses/{cid}/assignment_groups/{group_id} payload={payload}")
            return
        client = get_client(verbose=verbose)
        result = client.put(f"/courses/{cid}/assignment_groups/{group_id}", payload)
        emit(format_output(result, GROUP_COLUMNS, "table"))
    except Exception as exc:
        raise handle_canvas_error(exc)


@app.command("delete")
def delete_group(
    group_id: int = typer.Option(..., "--id"),
    course: str = typer.Option(None, "-c", "--course"),
    move_to: int = typer.Option(
        None, "--move-to", help="Move existing assignments to this group ID"
    ),
    dry_run: bool = typer.Option(True, "--dry-run/--commit"),
    yes: bool = typer.Option(False, "-y", "--yes"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """Delete an assignment group, optionally moving its assignments."""
    try:
        cid = get_course_id(course)
        confirm_or_abort(
            f"Delete assignment group {group_id}?", yes=yes, dry_run=dry_run
        )
        path = f"/courses/{cid}/assignment_groups/{group_id}"
        if move_to:
            path += f"?move_assignments_to={move_to}"
        client = get_client(verbose=verbose)
        client.delete(path)
        emit(f"Deleted assignment group {group_id}.")
    except typer.Exit:
        raise
    except Exception as exc:
        raise handle_canvas_error(exc)
