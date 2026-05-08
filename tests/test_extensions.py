"""Test the extension auto-discovery loader."""
from __future__ import annotations

import importlib
import sys
import textwrap
from pathlib import Path

import typer
from typer.testing import CliRunner

from canvas_conductor import extensions as ext_pkg


def test_underscore_files_are_skipped():
    """`_example.py` ships with the package and must NOT register a group."""
    main = typer.Typer()
    registered = ext_pkg.discover_extensions(main)
    assert "example" not in registered  # `_example.py` is filtered


def test_loader_picks_up_real_extension(tmp_path, monkeypatch):
    """Drop a fresh extension into the package dir and confirm it registers."""
    pkg_dir = Path(ext_pkg.__file__).parent
    new_file = pkg_dir / "_loader_smoke_extension.py"

    # Use a name that does NOT start with underscore for the actual test file:
    real_file = pkg_dir / "loader_smoke_extension.py"
    real_file.write_text(
        textwrap.dedent(
            """
            import typer
            app = typer.Typer(name="loader-smoke", help="smoke test extension")

            @app.command("ping")
            def ping() -> None:
                typer.echo("pong")
            """
        )
    )

    try:
        # Drop any cached module so re-import sees the new file.
        sys.modules.pop(
            "canvas_conductor.extensions.loader_smoke_extension", None
        )
        importlib.invalidate_caches()
        main = typer.Typer()
        registered = ext_pkg.discover_extensions(main)
        assert "loader-smoke" in registered
    finally:
        real_file.unlink(missing_ok=True)
        new_file.unlink(missing_ok=True)
        sys.modules.pop(
            "canvas_conductor.extensions.loader_smoke_extension", None
        )
