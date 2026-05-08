"""Example extension — copy this file (without the leading underscore) and
edit it to add your own commands.

Files starting with `_` are ignored by the discovery loader, so this file
serves as a template only.

Quickstart:
1. Copy this file to `extensions/my_extension.py`.
2. Rename `app = typer.Typer(name="example", ...)` to your group name.
3. Add commands beneath the `@app.command()` decorators.
4. Run `conductor my-name --help` to see your commands.

Useful imports:
    from canvas_conductor.client import get_client
    from canvas_conductor.config import get_course_id
    from canvas_conductor.utils.output import format_output
"""
from __future__ import annotations

import typer

from canvas_conductor.client import get_client
from canvas_conductor.config import get_course_id

app = typer.Typer(name="example", help="Example extension showcasing the pattern")


@app.command("hello")
def hello(
    course: str = typer.Option(None, "-c", "--course"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """Print a small report about the resolved course (no API calls)."""
    cid = get_course_id(course)
    typer.echo(f"Hello! You'd operate against course id={cid}.")


@app.command("module-count")
def module_count(
    course: str = typer.Option(None, "-c", "--course"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """Count modules in a course (demonstrates a real API call)."""
    client = get_client(verbose=verbose)
    cid = get_course_id(course)
    modules = client.get_all(f"/courses/{cid}/modules")
    typer.echo(f"Course {cid} has {len(modules)} modules.")
