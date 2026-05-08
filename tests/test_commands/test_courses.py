"""Smoke tests for the `courses` command group via the Typer CLI runner."""
from __future__ import annotations

import json

from typer.testing import CliRunner

from canvas_conductor.cli import app


runner = CliRunner()


def _config(write_config):
    write_config(
        """
[courses.t]
id = 99
name = "Test"
"""
    )


def test_courses_list_table(write_config, mock_responses, api):
    _config(write_config)
    mock_responses.get(
        f"{api}/courses",
        json=[
            {"id": 1, "name": "C1", "course_code": "X", "workflow_state": "available"}
        ],
    )
    result = runner.invoke(app, ["courses", "list"])
    assert result.exit_code == 0, result.output
    assert "C1" in result.output


def test_courses_list_json(write_config, mock_responses, api):
    _config(write_config)
    mock_responses.get(f"{api}/courses", json=[{"id": 7, "name": "C7"}])
    result = runner.invoke(app, ["courses", "list", "-o", "json"])
    assert result.exit_code == 0, result.output
    parsed = json.loads(result.output)
    assert parsed[0]["id"] == 7


def test_courses_show_uses_default_course(write_config, mock_responses, api):
    _config(write_config)
    mock_responses.get(f"{api}/courses/99", json={"id": 99, "name": "Test"})
    result = runner.invoke(app, ["courses", "show"])
    assert result.exit_code == 0, result.output
    assert "Test" in result.output


def test_courses_update_dry_run_makes_no_calls(write_config, mock_responses):
    _config(write_config)
    result = runner.invoke(
        app, ["courses", "update", "--name", "New", "--dry-run"]
    )
    assert result.exit_code == 0, result.output
    assert "DRY-RUN" in result.output
    # Zero registered HTTP calls means the CLI did not hit Canvas.
    assert len(mock_responses.calls) == 0
