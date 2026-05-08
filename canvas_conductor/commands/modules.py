"""Module commands: list, create, update, delete, reorder, publish/unpublish."""
from __future__ import annotations

import typer

from ..client import get_client
from ..config import get_course_id
from ..utils.output import format_output
from ._common import confirm_or_abort, emit, handle_canvas_error, prefix_keys

app = typer.Typer(name="modules", help="Manage course modules")


MODULE_COLUMNS = [
    ("ID", "id"),
    ("Position", "position"),
    ("Name", "name"),
    ("Published", "published"),
    ("Items", "items_count"),
]


@app.command("list")
def list_modules(
    course: str = typer.Option(None, "-c", "--course"),
    search: str = typer.Option(None, "--search", help="Filter by name"),
    output: str = typer.Option("table", "-o", "--output"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """List modules in a course."""
    try:
        client = get_client(verbose=verbose)
        cid = get_course_id(course)
        params: dict = {}
        if search:
            params["search_term"] = search
        modules = client.get_all(f"/courses/{cid}/modules", params=params)
        emit(format_output(modules, MODULE_COLUMNS, output))
    except Exception as exc:
        raise handle_canvas_error(exc)


@app.command("show")
def show_module(
    module_id: int = typer.Option(..., "--id"),
    course: str = typer.Option(None, "-c", "--course"),
    output: str = typer.Option("table", "-o", "--output"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """Show a single module with its items inline."""
    try:
        client = get_client(verbose=verbose)
        cid = get_course_id(course)
        data = client.get(
            f"/courses/{cid}/modules/{module_id}", params={"include[]": "items"}
        )
        if output == "table":
            from ..utils.output import format_kv

            emit(format_kv(data))
        else:
            emit(format_output(data, [], output))
    except Exception as exc:
        raise handle_canvas_error(exc)


@app.command("create")
def create_module(
    name: str = typer.Option(..., "--name"),
    course: str = typer.Option(None, "-c", "--course"),
    position: int = typer.Option(None, "--position"),
    unlock_at: str = typer.Option(None, "--unlock-at"),
    sequential: bool = typer.Option(False, "--sequential"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    yes: bool = typer.Option(False, "-y", "--yes"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """Create a new module."""
    try:
        cid = get_course_id(course)
        payload = prefix_keys(
            "module",
            {
                "name": name,
                "position": position,
                "unlock_at": unlock_at,
                "require_sequential_progress": sequential or None,
            },
        )
        if dry_run:
            emit(f"DRY-RUN: POST /courses/{cid}/modules payload={payload}")
            return
        client = get_client(verbose=verbose)
        result = client.post(f"/courses/{cid}/modules", data=payload)
        emit(format_output(result, MODULE_COLUMNS, "table"))
    except Exception as exc:
        raise handle_canvas_error(exc)


@app.command("update")
def update_module(
    module_id: int = typer.Option(..., "--id"),
    course: str = typer.Option(None, "-c", "--course"),
    name: str = typer.Option(None, "--name"),
    position: int = typer.Option(None, "--position"),
    published: bool = typer.Option(None, "--published"),
    unlock_at: str = typer.Option(None, "--unlock-at"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    yes: bool = typer.Option(False, "-y", "--yes"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """Update a module."""
    try:
        cid = get_course_id(course)
        payload = prefix_keys(
            "module",
            {
                "name": name,
                "position": position,
                "published": published,
                "unlock_at": unlock_at,
            },
        )
        if not payload:
            emit("No fields supplied — nothing to update.")
            return
        if dry_run:
            emit(f"DRY-RUN: PUT /courses/{cid}/modules/{module_id} payload={payload}")
            return
        client = get_client(verbose=verbose)
        result = client.put(f"/courses/{cid}/modules/{module_id}", payload)
        emit(format_output(result, MODULE_COLUMNS, "table"))
    except Exception as exc:
        raise handle_canvas_error(exc)


@app.command("delete")
def delete_module(
    module_id: int = typer.Option(..., "--id"),
    course: str = typer.Option(None, "-c", "--course"),
    dry_run: bool = typer.Option(True, "--dry-run/--commit"),
    yes: bool = typer.Option(False, "-y", "--yes"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """Delete a module (and all its items)."""
    try:
        cid = get_course_id(course)
        confirm_or_abort(
            f"Delete module {module_id} (and all items)?", yes=yes, dry_run=dry_run
        )
        client = get_client(verbose=verbose)
        client.delete(f"/courses/{cid}/modules/{module_id}")
        emit(f"Deleted module {module_id}.")
    except typer.Exit:
        raise
    except Exception as exc:
        raise handle_canvas_error(exc)


@app.command("reorder")
def reorder_modules(
    ids: str = typer.Option(..., "--ids", help="Comma-separated module IDs in desired order"),
    course: str = typer.Option(None, "-c", "--course"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    yes: bool = typer.Option(False, "-y", "--yes"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """Reorder modules by issuing per-module position updates."""
    try:
        cid = get_course_id(course)
        ordered = [int(x) for x in ids.split(",") if x.strip()]
        if dry_run:
            for pos, mid in enumerate(ordered, start=1):
                emit(f"DRY-RUN: PUT /courses/{cid}/modules/{mid} module[position]={pos}")
            return
        client = get_client(verbose=verbose)
        for pos, mid in enumerate(ordered, start=1):
            client.put(f"/courses/{cid}/modules/{mid}", {"module[position]": pos})
        emit(f"Reordered {len(ordered)} modules.")
    except Exception as exc:
        raise handle_canvas_error(exc)


@app.command("publish")
def publish_module(
    module_id: int = typer.Option(..., "--id"),
    course: str = typer.Option(None, "-c", "--course"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """Publish a module."""
    try:
        cid = get_course_id(course)
        if dry_run:
            emit(f"DRY-RUN: would publish module {module_id}")
            return
        client = get_client(verbose=verbose)
        client.put(f"/courses/{cid}/modules/{module_id}", {"module[published]": True})
        emit(f"Published module {module_id}.")
    except Exception as exc:
        raise handle_canvas_error(exc)


@app.command("unpublish")
def unpublish_module(
    module_id: int = typer.Option(..., "--id"),
    course: str = typer.Option(None, "-c", "--course"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """Unpublish a module."""
    try:
        cid = get_course_id(course)
        if dry_run:
            emit(f"DRY-RUN: would unpublish module {module_id}")
            return
        client = get_client(verbose=verbose)
        client.put(f"/courses/{cid}/modules/{module_id}", {"module[published]": False})
        emit(f"Unpublished module {module_id}.")
    except Exception as exc:
        raise handle_canvas_error(exc)


@app.command("items")
def list_items(
    module_id: int = typer.Option(..., "--id"),
    course: str = typer.Option(None, "-c", "--course"),
    output: str = typer.Option("table", "-o", "--output"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """List items inside a module."""
    try:
        client = get_client(verbose=verbose)
        cid = get_course_id(course)
        items = client.get_all(f"/courses/{cid}/modules/{module_id}/items")
        cols = [
            ("ID", "id"),
            ("Position", "position"),
            ("Type", "type"),
            ("Title", "title"),
            ("Content ID", "content_id"),
            ("Page URL", "page_url"),
            ("Published", "published"),
        ]
        emit(format_output(items, cols, output))
    except Exception as exc:
        raise handle_canvas_error(exc)
