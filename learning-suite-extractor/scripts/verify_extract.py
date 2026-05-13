#!/usr/bin/env python3
"""
Read an extractor output directory and print a Phase 5 verification report:
counts table, file map, and a list of detected anomalies.

This is meant to automate the mechanical parts of `00-summary.md`. The agent
still writes the spot-check sample and open-issues prose by hand.

Usage:
  python3 verify_extract.py /path/to/output_dir
  python3 verify_extract.py /path/to/output_dir --json   # emit JSON instead

Counts are derived by parsing the emitted YAML files. We use a minimal
hand-rolled YAML parser (no PyYAML dependency) that just counts top-level
list items per known section.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def count_list_items(yml_text: str, section_name: str) -> int:
    """Count list items immediately under a top-level mapping key.

    e.g. for 'assignments:\\n  - id: ...\\n  - id: ...', count_list_items(..., 'assignments') -> 2.
    """
    pattern = rf"(?m)^{re.escape(section_name)}:\s*$"
    m = re.search(pattern, yml_text)
    if not m:
        return 0
    start = m.end()
    count = 0
    for line in yml_text[start:].splitlines():
        if not line:
            continue
        # End of section: a new top-level key
        if re.match(r"^[A-Za-z_][\w]*:\s", line) or re.match(r"^[A-Za-z_][\w]*:\s*$", line):
            break
        if re.match(r"^\s{2}-\s", line):
            count += 1
    return count


def file_size_safe(p: Path) -> int:
    try:
        return p.stat().st_size
    except FileNotFoundError:
        return 0


def gather(base: Path) -> dict:
    """Read every relevant file and return structured counts + file map."""
    results: dict = {
        "course_dir": str(base),
        "files": {},
        "counts": {},
        "anomalies": [],
    }

    files_to_check = [
        "00-summary.md",
        "01-course.yml",
        "02-categories.yml",
        "03-assignments.yml",
        "04-schedule.yml",
        "06-content-index.yml",
        "05-syllabus/instructor_ta.md",
        "05-syllabus/course.md",
        "05-syllabus/policies.md",
        "raw/calendar-meta.json",
        "raw/events.json",
        "raw/calendar-items.json",
        "raw/assignments.json",
    ]
    for rel in files_to_check:
        p = base / rel
        results["files"][rel] = {
            "exists": p.exists(),
            "bytes": file_size_safe(p),
        }

    cats_yml = (base / "02-categories.yml")
    if cats_yml.exists():
        text = cats_yml.read_text()
        results["counts"]["categories"] = count_list_items(text, "categories")

    assigns_yml = base / "03-assignments.yml"
    if assigns_yml.exists():
        text = assigns_yml.read_text()
        results["counts"]["assignments"] = count_list_items(text, "assignments")

    sched_yml = base / "04-schedule.yml"
    if sched_yml.exists():
        text = sched_yml.read_text()
        results["counts"]["columns"] = count_list_items(text, "columns")
        results["counts"]["class_days"] = count_list_items(text, "class_days")
        results["counts"]["calendar_items"] = count_list_items(text, "calendar_items")
        results["counts"]["events"] = count_list_items(text, "events")

    content_yml = base / "06-content-index.yml"
    if content_yml.exists():
        text = content_yml.read_text()
        results["counts"]["content_pages"] = count_list_items(text, "pages")
        # Anomaly: pages that look like rosters
        if "[Student roster" in text or "looksLikeRoster" in text:
            results["anomalies"].append(
                "Content pages: at least one page flagged as student roster (body omitted)."
            )
        # Anomaly: any [BLOCKED] markers leaking through
        if "[BLOCKED" in text:
            results["anomalies"].append(
                "Content pages: [BLOCKED] marker present, some field never recovered."
            )

    for yml in ["02-categories.yml", "03-assignments.yml", "04-schedule.yml", "06-content-index.yml"]:
        p = base / yml
        if p.exists():
            text = p.read_text()
            if "[BLOCKED" in text:
                results["anomalies"].append(f"{yml}: [BLOCKED] marker present.")
            if "[TRUNCATED" in text:
                results["anomalies"].append(f"{yml}: [TRUNCATED] marker present.")

    # Syllabus checks
    for section in ("instructor_ta", "course", "policies"):
        p = base / "05-syllabus" / f"{section}.md"
        if p.exists():
            text = p.read_text()
            char_count = len(text)
            if "empty: true" in text or char_count < 100:
                results["anomalies"].append(
                    f"Syllabus {section}: marked empty or under 100 bytes."
                )

    return results


def render_text(results: dict) -> str:
    lines: list[str] = []
    lines.append(f"# Verification report for {results['course_dir']}")
    lines.append("")
    lines.append("## Counts")
    lines.append("")
    lines.append("| Item            | Extracted |")
    lines.append("|-----------------|-----------|")
    for key in ("categories", "assignments", "columns", "class_days", "calendar_items", "events", "content_pages"):
        if key in results["counts"]:
            lines.append(f"| {key:<15} | {results['counts'][key]:<9} |")
    lines.append("")
    lines.append("## File map")
    lines.append("")
    lines.append("| Path | Exists | Bytes |")
    lines.append("|------|--------|-------|")
    for rel, info in results["files"].items():
        mark = "yes" if info["exists"] else "MISSING"
        lines.append(f"| {rel} | {mark} | {info['bytes']} |")
    lines.append("")
    if results["anomalies"]:
        lines.append("## Anomalies")
        lines.append("")
        for a in results["anomalies"]:
            lines.append(f"- {a}")
    else:
        lines.append("## Anomalies")
        lines.append("")
        lines.append("None detected.")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Verify a Learning Suite extract")
    ap.add_argument("output_dir", help="Course-slug directory to verify")
    ap.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    args = ap.parse_args(argv)

    base = Path(args.output_dir).expanduser().resolve()
    if not base.is_dir():
        print(f"error: {base} is not a directory", file=sys.stderr)
        return 1

    results = gather(base)
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(render_text(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
