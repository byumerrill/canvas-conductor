"""Course navigation tabs: list, show, hide."""
from __future__ import annotations

import typer

from ..client import get_client
from ..config import get_course_id
from ..utils.output import format_output
from ._common import emit, handle_canvas_error

app = typer.Typer(name="tabs", help="Manage course navigation tabs")


TAB_COLUMNS = [
    ("ID", "id"),
    ("Label", "label"),
    ("Type", "type"),
    ("Position", "position"),
    ("Visibility", "visibility"),
    ("Hidden", "hidden"),
]


@app.command("list")
def list_tabs(
    course: str = typer.Option(None, "-c", "--course"),
    output: str = typer.Option("table", "-o", "--output"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """List navigation tabs."""
    try:
        client = get_client(verbose=verbose)
        cid = get_course_id(course)
        items = client.get_all(f"/courses/{cid}/tabs")
        emit(format_output(items, TAB_COLUMNS, output))
    except Exception as exc:
        raise handle_canvas_error(exc)


@app.command("show")
def show_tab(
    tab: str = typer.Option(..., "--tab", help="Tab id (e.g., assignments, modules)"),
    course: str = typer.Option(None, "-c", "--course"),
    output: str = typer.Option("table", "-o", "--output"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """Show a single tab by id."""
    try:
        client = get_client(verbose=verbose)
        cid = get_course_id(course)
        items = client.get_all(f"/courses/{cid}/tabs")
        match = next((t for t in items if t.get("id") == tab), None)
        if match is None:
            emit(f"Tab '{tab}' not found.")
            raise typer.Exit(code=5)
        if output == "table":
            from ..utils.output import format_kv

            emit(format_kv(match))
        else:
            emit(format_output(match, [], output))
    except typer.Exit:
        raise
    except Exception as exc:
        raise handle_canvas_error(exc)


@app.command("hide")
def hide_tab(
    tab: str = typer.Option(..., "--tab"),
    course: str = typer.Option(None, "-c", "--course"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """Hide a navigation tab. (The Home tab cannot be hidden.)"""
    try:
        cid = get_course_id(course)
        if tab == "home":
            emit("ERROR: the Home tab cannot be hidden.")
            raise typer.Exit(code=2)
        if dry_run:
            emit(f"DRY-RUN: PUT /courses/{cid}/tabs/{tab} hidden=true")
            return
        client = get_client(verbose=verbose)
        client.put(f"/courses/{cid}/tabs/{tab}", {"hidden": True})
        emit(f"Hid tab {tab}.")
    except typer.Exit:
        raise
    except Exception as exc:
        raise handle_canvas_error(exc)


@app.command("show-tab")
def show_tab_visible(
    tab: str = typer.Option(..., "--tab"),
    course: str = typer.Option(None, "-c", "--course"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """Make a previously-hidden navigation tab visible again."""
    try:
        cid = get_course_id(course)
        if dry_run:
            emit(f"DRY-RUN: PUT /courses/{cid}/tabs/{tab} hidden=false")
            return
        client = get_client(verbose=verbose)
        client.put(f"/courses/{cid}/tabs/{tab}", {"hidden": False})
        emit(f"Showed tab {tab}.")
    except Exception as exc:
        raise handle_canvas_error(exc)
