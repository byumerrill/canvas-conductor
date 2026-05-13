---
name: learning-suite-extractor
description: Extract course metadata from BYU Learning Suite into a portable on-disk staging area. Captures schedule, assignments, syllabus prose, and content page index, but does not download attachments. Use this skill whenever a faculty member asks to back up their Learning Suite course, save their BYU class to a folder, snapshot a Learning Suite course, get their syllabus and schedule out of Learning Suite, pull course metadata from Learning Suite, archive their course before semester end, or wants a versionable copy of their course outside the LMS. Also trigger on phrases like "extract my LS course", "export my course from Learning Suite", "snapshot my BYU course", "save my Learning Suite course to disk", or any request to capture course structure outside of Learning Suite. Requires the user to be logged into learningsuite.byu.edu in a Chrome browser with the Claude in Chrome extension active.
---

# Learning Suite Course Extractor

Extract course metadata from BYU Learning Suite and write it to disk as a
portable, diff-friendly snapshot. The goal is **metadata, not files**:
attachments (PDFs, slide decks, ZIPs) are referenced but never downloaded.

## What gets captured

- **Schedule**: class days, schedule columns, calendar items, events
- **Assignments**: every assignment with description, dates, points, category, late policy, rubric/attachment refs
- **Categories**: grading categories with weights and drop policies
- **Syllabus**: Instructor/TA Info, Course Information, University Policies (the Assignments and Schedule subsections of the syllabus duplicate Schedule data and are skipped)
- **Content**: page hierarchy with attachment filename + URL pairs (index only, no body capture by default). Pages that look like student rosters are recorded as metadata only.

## Prerequisites

Before invoking, verify:

1. The user is on a Chromium browser with the Claude in Chrome extension active.
2. They are logged into `https://learningsuite.byu.edu` (BYU SSO; do not attempt to authenticate).
3. You have file tools (Read, Write) and ideally a shell.
4. You have or can ask for the course URL (form: `https://learningsuite.byu.edu/.8NDL/cid-<COURSE_ID>/home`). The `.8NDL` prefix may redirect to a different session prefix; read the actual prefix from `location.pathname` after the first navigate and template from there. See `references/known-gotchas.md` §4.

If the Chrome extension is not connected, stop and ask the user to open their browser and enable it before continuing.

## Bundled helper scripts

The plugin ships with three Python helpers in `scripts/` that handle the
mechanical parts of the workflow. Use them rather than hand-rolling
equivalents inside the agent loop:

- `scripts/epoch_to_iso_mt.py` — converts Unix epoch seconds (or naive
  `"YYYY-MM-DD HH:MM:SS"` Mountain Time strings) to ISO 8601 with the
  correct MST/MDT offset for the moment in question. Works as a library or
  a CLI.
- `scripts/build_yaml.py` — reads the four `raw/*.json` files written
  during Phase 4 and emits `01-course.yml`, `02-categories.yml`,
  `03-assignments.yml`, and `04-schedule.yml` with proper date conversion
  and multiline description handling.
- `scripts/verify_extract.py` — reads the emitted YAML and produces the
  Phase 5 counts table, file map, and a list of detected anomalies (leaked
  `[BLOCKED]` markers, empty syllabus sections, roster-flagged pages,
  etc.). The agent still writes the spot-check sample and open-issues
  prose; this script just automates the mechanical bookkeeping.

The plugin's install location is in `${CLAUDE_PLUGIN_ROOT}` so invoke
scripts as e.g. `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/build_yaml.py <output_dir> ...`.

## Five-phase workflow

Run these in order. Each phase has a clear handoff to the next.

### Phase 1: Pre-flight

Ask the user (use AskUserQuestion):

1. **Output directory** for the extract. Default suggestion: `~/Desktop/learning-suite-extract/`. The skill never assumes a fixed location.
2. **Course URL.** Parse the `cid-XXXX` segment as `COURSE_ID`. All other URLs are templated from this.
3. **Course slug** for the output subfolder (e.g. `is-566-w26`). If the user has no preference, derive it from the course title after Phase 2.

### Phase 2: Initial scan

Navigate to the course home and report back, in one short paragraph:

- Course title and period
- Top-level nav items present
- A one-line status per target section (Schedule, Syllabus, Assignments, Content) confirming each is reachable and roughly how much content lives there
- The actual path prefix in use (e.g. `/.68kj/`) so the user knows you're templating from the live session, not the documented `/.8NDL/`

URL templates are in `references/url-templates.md`. Use them to probe each section without extracting yet.

### Phase 3: Scope confirmation

Ask the user (multi-select, default all checked) which of the four sections to extract. Honor their choices in Phase 4.

### Phase 4: Extraction

Extract each chosen section to disk. Detailed JavaScript snippets, output schemas, and per-section instructions are in:

- `references/extraction-snippets.md` — copy-paste JS for each section, broken into chunks that stay under the 50KB tool-result ceiling
- `references/output-schema.md` — exact file layout, YAML structure, date conversion rules (mixed epoch / pre-formatted strings)
- `references/known-gotchas.md` — Chrome filter behavior (blocking AND truncation), 50KB ceiling, path prefix variability, sidebar indent classes, content-page PII handling, attachment markup quirks

The general approach per section:

- **Schedule + Assignments + Categories.** `/calendar` exposes a `window.data` global with everything, but the full payload exceeds the tool-result ceiling. Split into four extractions: (a) categories + columns + classDays + period metadata, (b) events, (c) calendarItems, (d) assignments. Save each to `raw/*.json`, then run `scripts/build_yaml.py` to produce the structured YAML.
- **Syllabus.** Visit the student-view subroutes (`instructor_ta`, `course`, `policies`) and capture rendered text. The instructor-view URLs redirect to the editor and don't render content. Chunk long pages at 800-char windows to avoid filter truncation.
- **Content.** Walk the `.sideNavList` sidebar (capturing `pl-N` indent for parent/child tree), click each node, and harvest attachment filename/href pairs from the body. **Before capturing a page body, scan for roster patterns**; if detected, record metadata only and flag it in the summary. Write `06-content-index.yml`.

Always keep raw dumps (`raw/calendar-meta.json`, `raw/events.json`, `raw/calendar-items.json`, `raw/assignments.json`, and optionally `raw/syllabus-<section>.html`) so the user can recover anything the structured outputs missed.

### Phase 5: Verification and summary

Run `scripts/verify_extract.py <output_dir>` first to get the counts table,
file map, and machine-detected anomalies. Then write `00-summary.md`
combining that report with:

1. **Counts table** — what was extracted vs. what Phase 2 advertised. Flag any mismatch.
2. **Skipped items** — explicitly note that Syllabus Assignments and Syllabus Schedule were skipped because they duplicate Schedule data. Also note any content pages skipped for PII reasons.
3. **Spot-check sample** — three random assignments, three syllabus sections, three content pages, each as a one-line summary the user can verify against Learning Suite by eye.
4. **File map** — every file written with byte counts (auto-generated by `verify_extract.py`).
5. **Open issues** — fields you expected but didn't find, any `[BLOCKED]` or `[TRUNCATED]` artifacts still in raw dumps, pages with zero attachments worth a manual look, lecture/assignment numbering gaps that look intentional, etc.

End the summary with: "Open Learning Suite in a side window and confirm the counts and the spot-check. Reply with anything that looks off."

Then present the user with a link to the output directory and the summary file path.

## Performance: batch your browser calls

The Claude in Chrome plugin's `browser_batch` is significantly faster than separate calls. Group your work:

1. (navigate to course home) + (read interactive nav)
2. (navigate to `/calendar`) + (wait + extract metadata, then events, then calendarItems, then assignments as separate calls to stay under the 50KB ceiling)
3. (navigate to syllabus `instructor_ta`) + (wait + read main text)
4. Repeat 3 for `course` and `policies`
5. (navigate to `/pages`) + (read sidebar tree with `pl-N` indent)
6. For each content page: (click + wait + capture URL + capture attachment links via regex on innerText). Sidebar items must be clicked sequentially because `location.pathname` only updates after each click.

## Out of scope (do not extract)

- Attachment binaries (slides, PDFs, ZIPs) — capture references only
- Path / Modules (`/path` app)
- Grades, exam scores, or any student-identifying data (including content pages that contain student rosters; record metadata only)
- Discussions / Dialog
- Online (Zoom links)

## When the user wants different scope

If the user asks for body capture of content pages, full HTML (not markdown) of syllabus sections, or extraction across multiple semesters, accommodate but note it in the Phase 5 summary so they remember they asked for the heavier mode. For multi-semester runs, treat each semester as a separate extraction with its own course slug; do not try to merge.

If the user explicitly asks to capture a roster page body, override the PII guard but make it loud in the summary so they know what's now in the snapshot.
