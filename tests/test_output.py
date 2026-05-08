"""Tests for output formatting."""
from __future__ import annotations

import json

import pytest

from canvas_conductor.utils.output import (
    format_csv,
    format_json,
    format_kv,
    format_output,
    format_table,
)


COLUMNS = [("ID", "id"), ("Name", "name"), ("Published", "published")]


def test_format_table_renders_rows():
    rows = [{"id": 1, "name": "A", "published": True}]
    out = format_table(rows, COLUMNS)
    assert "A" in out
    assert "Yes" in out
    assert "ID" in out


def test_format_table_handles_dotted_keys():
    rows = [{"user": {"name": "Alice"}}]
    out = format_table(rows, [("Name", "user.name")])
    assert "Alice" in out


def test_format_json_list_round_trips():
    rows = [{"id": 1, "name": "A"}]
    parsed = json.loads(format_json(rows))
    assert parsed == rows


def test_format_json_single_item():
    parsed = json.loads(format_json({"id": 1}))
    assert parsed == {"id": 1}


def test_format_csv_has_header_and_rows():
    rows = [{"id": 1, "name": "A", "published": False}]
    out = format_csv(rows, COLUMNS)
    lines = out.splitlines()
    assert lines[0] == "ID,Name,Published"
    assert lines[1] == "1,A,No"


def test_format_kv_shows_pairs():
    out = format_kv({"id": 1, "name": "X"})
    assert "id   : 1" in out
    assert "name : X" in out


def test_format_output_unknown_format_raises():
    with pytest.raises(ValueError):
        format_output([], COLUMNS, output="xml")


def test_format_output_dispatch():
    rows = [{"id": 1, "name": "A", "published": True}]
    table = format_output(rows, COLUMNS, "table")
    js = format_output(rows, COLUMNS, "json")
    csvy = format_output(rows, COLUMNS, "csv")
    assert "A" in table
    assert json.loads(js) == rows
    assert "ID,Name,Published" in csvy
