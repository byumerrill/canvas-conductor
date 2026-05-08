"""Output formatting helpers.

A single `format_output` function handles three formats: table (default,
human-readable via rich), JSON (machine-readable), and CSV (spreadsheet).

`columns` is a list of `(header, key)` or `(header, key, width)` tuples that
describes which fields to extract from each item. For nested keys, use dotted
paths (e.g., `"user.name"`).
"""
from __future__ import annotations

import csv
import io
import json
from typing import Any, Iterable, Sequence

from rich.console import Console
from rich.table import Table


ColumnSpec = tuple  # (header, key) or (header, key, width)


def _resolve(item: Any, key: str) -> Any:
    """Resolve a possibly-dotted key against a dict-like or attribute object."""
    if not key:
        return item
    cur = item
    for part in key.split("."):
        if cur is None:
            return None
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            cur = getattr(cur, part, None)
    return cur


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value)
    if isinstance(value, dict):
        return json.dumps(value, separators=(",", ":"))
    return str(value)


def _coerce_to_list(data: Any) -> list[dict]:
    if data is None:
        return []
    if isinstance(data, list):
        return data
    return [data]


def _to_dict(item: Any) -> dict:
    if isinstance(item, dict):
        return item
    if hasattr(item, "model_dump"):  # pydantic v2
        return item.model_dump()
    if hasattr(item, "dict"):  # pydantic v1 fallback
        return item.dict()
    return dict(item)


def format_table(
    data: Iterable[Any],
    columns: Sequence[ColumnSpec],
) -> str:
    items = [_to_dict(d) for d in data]
    table = Table(show_header=True, header_style="bold")
    for col in columns:
        header = col[0]
        table.add_column(header)
    for item in items:
        row = [_stringify(_resolve(item, col[1])) for col in columns]
        table.add_row(*row)

    buffer = io.StringIO()
    console = Console(file=buffer, force_terminal=False, width=120)
    console.print(table)
    return buffer.getvalue().rstrip("\n")


def format_json(data: Any) -> str:
    payload: Any
    if isinstance(data, list):
        payload = [_to_dict(d) for d in data]
    elif data is None:
        payload = None
    elif isinstance(data, (str, int, float, bool)):
        payload = data
    else:
        payload = _to_dict(data)
    return json.dumps(payload, indent=2, default=str)


def format_csv(data: Iterable[Any], columns: Sequence[ColumnSpec]) -> str:
    items = [_to_dict(d) for d in data]
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([c[0] for c in columns])
    for item in items:
        writer.writerow([_stringify(_resolve(item, c[1])) for c in columns])
    return buffer.getvalue().rstrip("\n")


def format_kv(item: dict) -> str:
    """Single-item key-value display for `show` commands."""
    item = _to_dict(item)
    if not item:
        return "(empty)"
    width = max(len(str(k)) for k in item.keys())
    lines = [f"{str(k).ljust(width)} : {_stringify(v)}" for k, v in item.items()]
    return "\n".join(lines)


def format_output(
    data: Any,
    columns: Sequence[ColumnSpec],
    output: str = "table",
) -> str:
    """Format `data` according to `output`. `columns` controls table/csv layout."""
    output = (output or "table").lower()
    if output not in {"table", "json", "csv"}:
        raise ValueError(f"Unknown output format: {output!r}. Use table, json, or csv.")

    if output == "json":
        return format_json(data)

    items = _coerce_to_list(data)

    if output == "csv":
        return format_csv(items, columns)

    if isinstance(data, dict) and not columns:
        return format_kv(data)

    return format_table(items, columns)
