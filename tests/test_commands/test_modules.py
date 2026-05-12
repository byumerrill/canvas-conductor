"""Module command smoke tests."""
from __future__ import annotations

from typer.testing import CliRunner

from canvas_conductor.cli import app


runner = CliRunner()


def _config(write_config):
    write_config(
        """
[courses.t]
id = 99
"""
    )


def test_modules_list(write_config, mock_responses, api):
    _config(write_config)
    mock_responses.get(
        f"{api}/courses/99/modules",
        json=[
            {"id": 1, "name": "Week 1", "position": 1, "published": True, "items_count": 5},
            {"id": 2, "name": "Week 2", "position": 2, "published": False, "items_count": 3},
        ],
    )
    result = runner.invoke(app, ["modules", "list"])
    assert result.exit_code == 0, result.output
    assert "Week 1" in result.output
    assert "Week 2" in result.output


def test_modules_create_dry_run(write_config, mock_responses):
    _config(write_config)
    result = runner.invoke(app, ["modules", "create", "--name", "Test", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "DRY-RUN" in result.output
    assert len(mock_responses.calls) == 0


def test_modules_publish(write_config, mock_responses, api):
    _config(write_config)
    mock_responses.put(
        f"{api}/courses/99/modules/5",
        json={"id": 5, "name": "M5", "published": True},
    )
    result = runner.invoke(app, ["modules", "publish", "--id", "5"])
    assert result.exit_code == 0, result.output
    assert "Published module 5" in result.output


def test_modules_delete_default_dry_run(write_config, mock_responses):
    _config(write_config)
    # Default behavior is dry-run; no API calls should be made.
    result = runner.invoke(app, ["modules", "delete", "--id", "5"])
    assert result.exit_code == 0, result.output
    assert "DRY-RUN" in result.output
    assert len(mock_responses.calls) == 0


def test_modules_delete_commit_with_yes(write_config, mock_responses, api):
    _config(write_config)
    mock_responses.delete(f"{api}/courses/99/modules/5", status=204)
    result = runner.invoke(
        app, ["modules", "delete", "--id", "5", "--commit", "-y"]
    )
    assert result.exit_code == 0, result.output
    assert "Deleted module 5" in result.output


def test_modules_reorder_dry_run(write_config, mock_responses):
    _config(write_config)
    result = runner.invoke(
        app, ["modules", "reorder", "--ids", "3,1,2", "--dry-run"]
    )
    assert result.exit_code == 0, result.output
    assert "module.position=1" in result.output
    assert "module.position=2" in result.output
    assert "module.position=3" in result.output
