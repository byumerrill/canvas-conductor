#!/usr/bin/env python3
"""
Convert raw JSON dumps from the Learning Suite extractor into the canonical
YAML output layout described in references/output-schema.md.

Inputs (read from <output_dir>/raw/):
  - calendar-meta.json   (categories, columns, classDays, period)
  - events.json          (events with name_text already rendered to plain text)
  - calendar-items.json  (calendar items with description plain text)
  - assignments.json     (full assignment list)

Outputs (written to <output_dir>/):
  - 01-course.yml
  - 02-categories.yml
  - 03-assignments.yml
  - 04-schedule.yml

Usage:
  python3 build_yaml.py /path/to/output_dir \
      --source "https://learningsuite.byu.edu/.8NDL/cid-XXX/home" \
      --title "IS 555 - Data Science for Organizations" \
      --period-label "Winter 2026"

If --source / --title / --period-label are omitted, sensible placeholders are
used and the agent can edit 01-course.yml afterward.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Sibling-file import (no package install needed)
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
from epoch_to_iso_mt import datestr_to_iso_mt, epoch_to_iso_mt  # noqa: E402


def _yaml_str(s) -> str:
    """Format a value for YAML; quote when needed, use literal block for multiline."""
    if s is None:
        return "null"
    if isinstance(s, bool):
        return "true" if s else "false"
    if isinstance(s, (int, float)):
        return str(s)
    if not isinstance(s, str):
        s = str(s)
    if "\n" in s:
        return None  # caller should use _emit_block instead
    needs_quote = (
        s == ""
        or s.strip() != s
        or s.lower() in ("true", "false", "null", "yes", "no", "on", "off")
        or any(c in s for c in [":", "#", "{", "}", "[", "]", "&", "*", "!", "|", ">", "'", '"', "%", "@", "`"])
    )
    if needs_quote:
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return s


def _emit_field(lines: list[str], indent: int, key: str, value) -> None:
    """Append a 'key: value' line, using literal block for multiline strings."""
    pad = " " * indent
    if isinstance(value, str) and "\n" in value:
        lines.append(f"{pad}{key}: |-")
        block_pad = " " * (indent + 2)
        for ln in value.split("\n"):
            lines.append(block_pad + ln)
    else:
        lines.append(f"{pad}{key}: {_yaml_str(value)}")


def _emit_list_dict(lines: list[str], indent: int, fields: list[tuple[str, object]]) -> None:
    """Emit one list item where the first field uses '- ' and subsequent use '  '."""
    pad = " " * indent
    for i, (key, value) in enumerate(fields):
        prefix = pad + ("- " if i == 0 else "  ")
        if isinstance(value, str) and "\n" in value:
            lines.append(f"{prefix}{key}: |-")
            block_pad = " " * (indent + 4)
            for ln in value.split("\n"):
                lines.append(block_pad + ln)
        else:
            lines.append(f"{prefix}{key}: {_yaml_str(value)}")


def build_course_yml(base: Path, meta: dict, source: str, title: str, period_label: str) -> None:
    extracted_at = datetime.now(timezone.utc).isoformat()
    period_first = epoch_to_iso_mt(meta["periodFirstDay"])
    period_last = epoch_to_iso_mt(meta["periodLastDay"])
    period_first_day = period_first.split("T")[0] if period_first else None
    period_last_day = period_last.split("T")[0] if period_last else None
    out = f"""extracted_at: {extracted_at}
source: {source}
course:
  id: {meta['courseID']}
  title: {_yaml_str(title)}
  period: "{meta['period']}"
  period_label: {_yaml_str(period_label)}
  period_first_day: {period_first_day}
  period_last_day: {period_last_day}
sections_extracted:
  - schedule
  - assignments
  - categories
  - syllabus
  - content
sections_skipped:
  - syllabus.assignments_subsection (duplicates assignments)
  - syllabus.schedule_subsection (duplicates schedule)
"""
    (base / "01-course.yml").write_text(out)


def build_categories_yml(base: Path, meta: dict, assigns: list[dict]) -> None:
    cat_weights: dict[str, float] = {}
    for a in assigns:
        cid = a.get("categoryID")
        if cid is None:
            continue
        cat_weights[cid] = cat_weights.get(cid, 0) + (a.get("weight") or 0)
    cat_by_id = {c["id"]: c for c in meta["categories"]}
    total_graded_weight = sum(
        w for cid, w in cat_weights.items()
        if cid in cat_by_id
        and not cat_by_id[cid].get("extraCredit", False)
        and not cat_by_id[cid].get("calendarOnly", False)
    )

    lines: list[str] = ["categories:"]
    for c in meta["categories"]:
        wt = cat_weights.get(c["id"], 0)
        pct = (
            round(100 * wt / total_graded_weight, 1)
            if total_graded_weight and not c.get("calendarOnly") and not c.get("extraCredit")
            else None
        )
        _emit_list_dict(lines, 2, [
            ("id", c["id"]),
            ("title", c["title"]),
            ("display_order", c["displayOrder"]),
            ("raw_weight_sum", wt),
            ("weight_pct", pct),
            ("equal_assign_weight", bool(c["equalAssignWeight"])),
            ("low_scores_to_drop", c["lowScoresToDrop"]),
            ("extra_credit", bool(c["extraCredit"])),
            ("graded", bool(c["graded"])),
            ("calendar_only", bool(c["calendarOnly"])),
        ])
    (base / "02-categories.yml").write_text("\n".join(lines) + "\n")


def build_assignments_yml(base: Path, meta: dict, assigns: list[dict]) -> None:
    cat_title_by_id = {c["id"]: c["title"] for c in meta["categories"]}
    lines: list[str] = ["assignments:"]
    for a in assigns:
        fields: list[tuple[str, object]] = [
            ("id", a["id"]),
            ("name", a["name"]),
        ]
        if a.get("shortName"):
            fields.append(("short_name", a["shortName"]))
        fields.extend([
            ("category_id", a.get("categoryID")),
            ("category_title", cat_title_by_id.get(a.get("categoryID"), "")),
            ("type", a.get("type", "assignment")),
            ("points", a.get("points")),
            ("weight", a.get("weight")),
            ("begin_date", datestr_to_iso_mt(a.get("beginDate"))),
            ("due_date", datestr_to_iso_mt(a.get("dueDate"))),
            ("visible_date", datestr_to_iso_mt(a.get("visibleDate"))),
            ("display_order", a.get("displayOrder", 0)),
            ("extra_credit", bool(a.get("extraCredit", False))),
            ("graded", bool(a.get("graded", True))),
            ("allow_late_submission", bool(a.get("allowLateSubmission", False))),
            ("late_penalty", a.get("latePenalty")),
            ("online_submission", a.get("onlineSubmission", "none")),
            ("score_entry", a.get("scoreEntry", "points")),
            ("allow_score_drop", bool(a.get("allowScoreDrop", False))),
            ("has_attachment", bool(a.get("hasAttachment", False))),
            ("has_rubric", bool(a.get("hasRubric", False))),
            ("url_slug", a.get("url") or ""),
            ("description", a.get("description") or ""),
        ])
        _emit_list_dict(lines, 2, fields)
    (base / "03-assignments.yml").write_text("\n".join(lines) + "\n")


def build_schedule_yml(base: Path, meta: dict, events: list[dict], cal: list[dict]) -> None:
    lines: list[str] = []
    lines.append(f'period: "{meta["period"]}"')
    period_first = epoch_to_iso_mt(meta["periodFirstDay"])
    period_last = epoch_to_iso_mt(meta["periodLastDay"])
    lines.append(f'period_first_day: {period_first.split("T")[0] if period_first else "null"}')
    lines.append(f'period_last_day: {period_last.split("T")[0] if period_last else "null"}')

    lines.append("columns:")
    for c in meta["columns"]:
        _emit_list_dict(lines, 2, [
            ("id", c["id"]),
            ("title", c["title"]),
            ("display_order", c["displayOrder"]),
        ])

    lines.append("class_days:")
    for cd in sorted(meta["classDays"], key=lambda x: x["date"]):
        iso = epoch_to_iso_mt(cd["date"]) or ""
        _emit_list_dict(lines, 2, [
            ("date", iso.split("T")[0] if iso else None),
            ("visible", bool(cd["visible"])),
            ("id", cd["id"]),
        ])

    lines.append("calendar_items:")
    for ci in sorted(cal, key=lambda x: x.get("endDate") or ""):
        fields: list[tuple[str, object]] = [
            ("id", ci["id"]),
            ("heading_id", ci.get("headingID", "")),
            ("begin_date", datestr_to_iso_mt(ci.get("beginDate"))),
            ("end_date", datestr_to_iso_mt(ci.get("endDate"))),
            ("description", ci.get("description") or ""),
        ]
        _emit_list_dict(lines, 2, fields)

    lines.append("events:")
    for e in sorted(events, key=lambda x: (x.get("serverDate") or "", x.get("displayOrder", 0))):
        fields = [
            ("date", e.get("serverDate")),
            ("epoch", e.get("date")),
            ("column", e.get("column", "")),
            ("display_order", e.get("displayOrder", 0)),
            ("name", e.get("name_text") or ""),
        ]
        _emit_list_dict(lines, 2, fields)

    (base / "04-schedule.yml").write_text("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build canonical YAML from raw extractor dumps")
    ap.add_argument("output_dir", help="Path to the course-slug directory containing raw/")
    ap.add_argument("--source", default="", help="Source URL for 01-course.yml")
    ap.add_argument("--title", default="", help="Course title for 01-course.yml")
    ap.add_argument("--period-label", default="", help="Human period label (e.g. Winter 2026)")
    args = ap.parse_args(argv)

    base = Path(args.output_dir).expanduser().resolve()
    raw = base / "raw"
    if not raw.is_dir():
        print(f"error: {raw} does not exist", file=sys.stderr)
        return 1

    meta = json.loads((raw / "calendar-meta.json").read_text())
    assigns = json.loads((raw / "assignments.json").read_text())
    events = json.loads((raw / "events.json").read_text())
    cal = json.loads((raw / "calendar-items.json").read_text())

    build_course_yml(base, meta, args.source, args.title, args.period_label)
    build_categories_yml(base, meta, assigns)
    build_assignments_yml(base, meta, assigns)
    build_schedule_yml(base, meta, events, cal)

    print(f"Wrote 01-course.yml, 02-categories.yml, 03-assignments.yml, 04-schedule.yml in {base}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
