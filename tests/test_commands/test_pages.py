"""Page command smoke tests."""
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


def test_pages_list(write_config, mock_responses, api):
    _config(write_config)
    mock_responses.get(
        f"{api}/courses/99/pages",
        json=[{"page_id": 1, "url": "welcome", "title": "Welcome", "published": True}],
    )
    result = runner.invoke(app, ["pages", "list"])
    assert result.exit_code == 0, result.output
    assert "Welcome" in result.output


def test_pages_create_dry_run(write_config, mock_responses):
    _config(write_config)
    result = runner.invoke(
        app, ["pages", "create", "--title", "X", "--body", "<p>y</p>", "--dry-run"]
    )
    assert result.exit_code == 0, result.output
    assert "DRY-RUN" in result.output
    assert "wiki_page[title]" in result.output


def test_pages_set_front(write_config, mock_responses, api):
    _config(write_config)
    mock_responses.put(
        f"{api}/courses/99/pages/welcome",
        json={"url": "welcome", "title": "Welcome", "front_page": True},
    )
    result = runner.invoke(app, ["pages", "set-front", "--url", "welcome"])
    assert result.exit_code == 0, result.output
    assert "Set page 'welcome' as front page" in result.output
