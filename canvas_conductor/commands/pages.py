"""Page (wiki) commands: list, show, create, update, delete, set-front."""
from __future__ import annotations

from pathlib import Path

import typer

from ..client import get_client
from ..config import get_course_id
from ..utils.output import format_output
from ._common import confirm_or_abort, emit, handle_canvas_error, prefix_keys

app = typer.Typer(name="pages", help="Manage course wiki pages")


PAGE_COLUMNS = [
    ("URL", "url"),
    ("Title", "title"),
    ("Published", "published"),
    ("Front Page", "front_page"),
    ("Updated", "updated_at"),
]


@app.command("list")
def list_pages(
    course: str = typer.Option(None, "-c", "--course"),
    sort: str = typer.Option(None, "--sort", help="title, created_at, updated_at"),
    search: str = typer.Option(None, "--search"),
    published: bool = typer.Option(None, "--published"),
    output: str = typer.Option("table", "-o", "--output"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """List pages (summary only — bodies fetched via `show`)."""
    try:
        client = get_client(verbose=verbose)
        cid = get_course_id(course)
        params: dict = {}
        if sort:
            params["sort"] = sort
        if search:
            params["search_term"] = search
        if published is not None:
            params["published"] = published
        pages = client.get_all(f"/courses/{cid}/pages", params=params)
        emit(format_output(pages, PAGE_COLUMNS, output))
    except Exception as exc:
        raise handle_canvas_error(exc)


@app.command("show")
def show_page(
    url: str = typer.Option(..., "--url", help="Page URL slug or ID"),
    course: str = typer.Option(None, "-c", "--course"),
    output: str = typer.Option("table", "-o", "--output"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """Show a single page (with body)."""
    try:
        client = get_client(verbose=verbose)
        cid = get_course_id(course)
        data = client.get(f"/courses/{cid}/pages/{url}")
        if output == "table":
            from ..utils.output import format_kv

            emit(format_kv(data))
        else:
            emit(format_output(data, [], output))
    except Exception as exc:
        raise handle_canvas_error(exc)


def _read_body(body: str | None, file: str | None) -> str | None:
    if body is not None:
        return body
    if file:
        return Path(file).read_text()
    return None


@app.command("create")
def create_page(
    title: str = typer.Option(..., "--title"),
    course: str = typer.Option(None, "-c", "--course"),
    body: str = typer.Option(None, "--body", help="HTML body"),
    file: str = typer.Option(None, "--file", help="Read body from a file (HTML)"),
    published: bool = typer.Option(False, "--published"),
    front_page: bool = typer.Option(False, "--front-page"),
    editing_roles: str = typer.Option(
        None, "--editing-roles", help="teachers, students, members, public"
    ),
    dry_run: bool = typer.Option(False, "--dry-run"),
    yes: bool = typer.Option(False, "-y", "--yes"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """Create a new wiki page."""
    try:
        cid = get_course_id(course)
        payload = prefix_keys(
            "wiki_page",
            {
                "title": title,
                "body": _read_body(body, file),
                "published": published or None,
                "front_page": front_page or None,
                "editing_roles": editing_roles,
            },
        )
        if dry_run:
            emit(f"DRY-RUN: POST /courses/{cid}/pages payload={payload}")
            return
        client = get_client(verbose=verbose)
        result = client.post(f"/courses/{cid}/pages", data=payload)
        emit(format_output(result, PAGE_COLUMNS, "table"))
    except Exception as exc:
        raise handle_canvas_error(exc)


@app.command("update")
def update_page(
    url: str = typer.Option(..., "--url"),
    course: str = typer.Option(None, "-c", "--course"),
    title: str = typer.Option(None, "--title"),
    body: str = typer.Option(None, "--body"),
    file: str = typer.Option(None, "--file"),
    published: bool = typer.Option(None, "--published"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    yes: bool = typer.Option(False, "-y", "--yes"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """Update an existing wiki page."""
    try:
        cid = get_course_id(course)
        payload = prefix_keys(
            "wiki_page",
            {
                "title": title,
                "body": _read_body(body, file),
                "published": published,
            },
        )
        if not payload:
            emit("No fields supplied — nothing to update.")
            return
        if dry_run:
            emit(f"DRY-RUN: PUT /courses/{cid}/pages/{url} payload={payload}")
            return
        client = get_client(verbose=verbose)
        result = client.put(f"/courses/{cid}/pages/{url}", payload)
        emit(format_output(result, PAGE_COLUMNS, "table"))
    except Exception as exc:
        raise handle_canvas_error(exc)


@app.command("delete")
def delete_page(
    url: str = typer.Option(..., "--url"),
    course: str = typer.Option(None, "-c", "--course"),
    dry_run: bool = typer.Option(True, "--dry-run/--commit"),
    yes: bool = typer.Option(False, "-y", "--yes"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """Delete a wiki page."""
    try:
        cid = get_course_id(course)
        confirm_or_abort(f"Delete page '{url}'?", yes=yes, dry_run=dry_run)
        client = get_client(verbose=verbose)
        client.delete(f"/courses/{cid}/pages/{url}")
        emit(f"Deleted page {url}.")
    except typer.Exit:
        raise
    except Exception as exc:
        raise handle_canvas_error(exc)


@app.command("set-front")
def set_front_page(
    url: str = typer.Option(..., "--url"),
    course: str = typer.Option(None, "-c", "--course"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """Mark a page as the course's front page."""
    try:
        cid = get_course_id(course)
        if dry_run:
            emit(f"DRY-RUN: would set page '{url}' as front page in course {cid}")
            return
        client = get_client(verbose=verbose)
        client.put(
            f"/courses/{cid}/pages/{url}",
            {"wiki_page": {"front_page": True, "published": True}},
        )
        emit(f"Set page '{url}' as front page.")
    except Exception as exc:
        raise handle_canvas_error(exc)
