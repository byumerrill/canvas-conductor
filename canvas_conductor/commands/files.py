"""File commands: list, upload (two-step), delete, quota."""
from __future__ import annotations

import typer

from ..client import get_client
from ..config import get_course_id
from ..utils.output import format_output
from ._common import confirm_or_abort, emit, handle_canvas_error

app = typer.Typer(name="files", help="Manage course files")


FILE_COLUMNS = [
    ("ID", "id"),
    ("Name", "display_name"),
    ("Size", "size"),
    ("Type", "content-type"),
    ("Folder", "folder_id"),
    ("Updated", "updated_at"),
]


@app.command("list")
def list_files(
    course: str = typer.Option(None, "-c", "--course"),
    search: str = typer.Option(None, "--search"),
    sort: str = typer.Option(None, "--sort", help="name, size, created_at, updated_at"),
    output: str = typer.Option("table", "-o", "--output"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """List files in the course's root files area."""
    try:
        client = get_client(verbose=verbose)
        cid = get_course_id(course)
        params: dict = {}
        if search:
            params["search_term"] = search
        if sort:
            params["sort"] = sort
        items = client.get_all(f"/courses/{cid}/files", params=params)
        emit(format_output(items, FILE_COLUMNS, output))
    except Exception as exc:
        raise handle_canvas_error(exc)


@app.command("upload")
def upload_file(
    file: str = typer.Option(..., "--file", help="Local path"),
    course: str = typer.Option(None, "-c", "--course"),
    folder: str = typer.Option(None, "--folder", help="Target folder path"),
    content_type: str = typer.Option(None, "--content-type"),
    on_duplicate: str = typer.Option(
        "rename", "--on-duplicate", help="rename or overwrite"
    ),
    dry_run: bool = typer.Option(False, "--dry-run"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """Upload a file using Canvas's two-step protocol."""
    try:
        cid = get_course_id(course)
        if dry_run:
            emit(
                f"DRY-RUN: would upload {file} to course {cid} folder={folder} "
                f"on_duplicate={on_duplicate}"
            )
            return
        client = get_client(verbose=verbose)
        result = client.upload_file(
            course_id=cid,
            local_path=file,
            folder_path=folder,
            content_type=content_type,
            on_duplicate=on_duplicate,
        )
        emit(format_output(result, FILE_COLUMNS, "table"))
    except Exception as exc:
        raise handle_canvas_error(exc)


@app.command("delete")
def delete_file(
    file_id: int = typer.Option(..., "--id"),
    dry_run: bool = typer.Option(True, "--dry-run/--commit"),
    yes: bool = typer.Option(False, "-y", "--yes"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """Delete a file by its Canvas file ID."""
    try:
        confirm_or_abort(f"Delete file {file_id}?", yes=yes, dry_run=dry_run)
        client = get_client(verbose=verbose)
        client.delete(f"/files/{file_id}")
        emit(f"Deleted file {file_id}.")
    except typer.Exit:
        raise
    except Exception as exc:
        raise handle_canvas_error(exc)


@app.command("quota")
def quota(
    course: str = typer.Option(None, "-c", "--course"),
    output: str = typer.Option("table", "-o", "--output"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """Show file storage quota and usage."""
    try:
        client = get_client(verbose=verbose)
        cid = get_course_id(course)
        data = client.get(f"/courses/{cid}/files/quota")
        # Add a calculated percentage for convenience.
        if isinstance(data, dict) and "quota" in data and "quota_used" in data:
            quota_b = data["quota"] or 0
            used_b = data["quota_used"] or 0
            data["percent_used"] = (
                round(used_b / quota_b * 100, 2) if quota_b else None
            )
        if output == "table":
            from ..utils.output import format_kv

            emit(format_kv(data))
        else:
            emit(format_output(data, [], output))
    except Exception as exc:
        raise handle_canvas_error(exc)


@app.command("folders")
def list_folders(
    course: str = typer.Option(None, "-c", "--course"),
    output: str = typer.Option("table", "-o", "--output"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """List folders in a course."""
    try:
        client = get_client(verbose=verbose)
        cid = get_course_id(course)
        items = client.get_all(f"/courses/{cid}/folders")
        cols = [
            ("ID", "id"),
            ("Name", "name"),
            ("Full Path", "full_name"),
            ("Files", "files_count"),
            ("Folders", "folders_count"),
        ]
        emit(format_output(items, cols, output))
    except Exception as exc:
        raise handle_canvas_error(exc)
