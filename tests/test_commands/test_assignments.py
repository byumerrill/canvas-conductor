"""Assignment command smoke tests, including bulk-dates date math."""
from __future__ import annotations

from datetime import timedelta

import pytest
from typer.testing import CliRunner

from canvas_conductor.cli import app
from canvas_conductor.commands.assignments import _parse_shift, _shift_iso


runner = CliRunner()


def _config(write_config):
    write_config(
        """
[courses.t]
id = 99
"""
    )


def test_parse_shift_units():
    assert _parse_shift("7d") == timedelta(days=7)
    assert _parse_shift("-1d") == timedelta(days=-1)
    assert _parse_shift("12h") == timedelta(hours=12)
    assert _parse_shift("2w") == timedelta(weeks=2)
    assert _parse_shift("30m") == timedelta(minutes=30)
    with pytest.raises(ValueError):
        _parse_shift("nonsense")


def test_shift_iso_round_trips():
    out = _shift_iso("2026-07-01T23:59:00Z", timedelta(days=1))
    assert out == "2026-07-02T23:59:00Z"


def test_assignments_list(write_config, mock_responses, api):
    _config(write_config)
    mock_responses.get(
        f"{api}/courses/99/assignments",
        json=[
            {"id": 1, "name": "HW1", "points_possible": 10, "due_at": None, "published": True}
        ],
    )
    result = runner.invoke(app, ["assignments", "list"])
    assert result.exit_code == 0, result.output
    assert "HW1" in result.output


def test_bulk_dates_dry_run(write_config, mock_responses, api):
    _config(write_config)
    mock_responses.get(
        f"{api}/courses/99/assignments",
        json=[
            {"id": 1, "name": "HW1", "due_at": "2026-07-01T23:59:00Z"},
            {"id": 2, "name": "HW2", "due_at": None},  # skipped — no dates
        ],
    )
    result = runner.invoke(
        app, ["assignments", "bulk-dates", "--shift", "7d"]
    )
    assert result.exit_code == 0, result.output
    assert "DRY-RUN" in result.output
    assert "HW1" in result.output
    assert "2026-07-08T23:59:00Z" in result.output
