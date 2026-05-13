# learning-suite-extractor

A Cowork plugin that extracts course metadata from BYU Learning Suite into a
portable, on-disk staging area. Designed for faculty who teach in Learning
Suite and want a versionable snapshot of their course outside the LMS.

The plugin captures schedule, assignments, syllabus prose, and a content page
index. It does **not** download attachments (PDFs, slide decks, ZIPs); those
are referenced by filename and URL, on the assumption you already have them
on disk.

## What it does

When a colleague asks Claude (in Cowork) to back up a Learning Suite course,
this plugin's skill auto-triggers and walks them through a five-phase
workflow:

1. **Pre-flight** — confirms the output directory and course URL
2. **Initial scan** — visits the course home and reports what's visible
3. **Scope confirmation** — lets the user opt out of any of the four sections
4. **Extraction** — pulls each chosen section to disk
5. **Verification** — counts records, samples for spot-checking, asks the user to confirm against Learning Suite

Output is written as YAML for structured data plus markdown for prose, with
raw HTML/JSON dumps preserved alongside.

## Trigger phrases

The skill fires automatically when a colleague says things like:

- "back up my Learning Suite course"
- "save my BYU class to a folder"
- "snapshot my Learning Suite course"
- "get my syllabus and schedule out of Learning Suite"
- "archive my course before the semester ends"
- "extract my LS course"

## Prerequisites

Before installing:

- **Cowork** desktop app installed and signed in (this plugin targets Cowork; it can run in Claude Code too but the UX is built around Cowork's question/answer surface)
- **Claude in Chrome** browser extension installed and connected
- BYU SSO login active in the Chrome window (the plugin does not authenticate)

## Installation

### Option A: Install the .plugin file

Drop the `.plugin` file into Cowork (drag onto the chat or use the plugin
manager). Cowork unpacks it into your plugins directory and activates the
skill.

### Option B: Install from this directory

If you have this repo cloned locally, you can also point Cowork at the folder
directly. See Cowork's plugin documentation for the local-folder install
flow.

## Sharing with colleagues

For BYU IS faculty: drop the `.plugin` file in a shared Box folder with a
one-line install instruction. Colleagues download, drag into Cowork, done.

For broader sharing (other LS-using faculty): push to a public GitHub repo
and share the URL. Cowork can install plugins from URLs.

## What's in here

```
learning-suite-extractor/
├── .claude-plugin/
│   └── plugin.json                       # Plugin manifest
├── skills/
│   └── learning-suite-extractor/
│       ├── SKILL.md                      # Main playbook (the agent reads this first)
│       └── references/
│           ├── extraction-snippets.md    # Copy-paste JS for window.data extraction
│           ├── url-templates.md          # All Learning Suite URL patterns
│           ├── output-schema.md          # File layout and YAML structure
│           └── known-gotchas.md          # The Chrome plugin filter, async loads, etc.
├── scripts/
│   ├── epoch_to_iso_mt.py                # Epoch / naive-string -> ISO 8601 with MT offset (DST-aware)
│   ├── build_yaml.py                     # Convert raw/*.json -> 01..04 YAML files
│   └── verify_extract.py                 # Phase 5 counts/file-map/anomaly report
└── README.md                              # This file
```

The skill calls the scripts via `${CLAUDE_PLUGIN_ROOT}/scripts/...` so they're
available wherever the plugin is installed.

## What gets captured (and what doesn't)

**In scope:**
- Schedule: class days, columns, calendar items, events
- Assignments: ~50 fields each including description, dates, points, late policy
- Categories: weights, drop policies
- Syllabus: Instructor/TA Info, Course Information, University Policies (the Assignments and Schedule subsections of the syllabus duplicate Schedule data, so they're skipped)
- Content: page hierarchy + attachment filename/URL pairs (index only by default)

**Out of scope:**
- Attachment binaries (PDFs, slides, ZIPs) — references only
- Path / Modules
- Grades, exam scores, student-identifying data
- Discussions / Dialog
- Online (Zoom links)

## Limitations

- **BYU-specific.** All URL templates target `learningsuite.byu.edu`. If your institution uses a different LMS that exposes structured data via similar globals (some Canvas instances, D2L, Moodle), the same five-phase shape applies but the URL templates and field-picking JavaScript need to change.
- **Single-course-per-run.** Multi-semester extraction means re-running the skill per course. The skill won't try to merge.
- **Chrome plugin required.** No headless browser support; this is interactive.
- **Read-only.** The plugin extracts but doesn't write back to Learning Suite.

## Author

Dave Wilson, BYU Marriott School of Business
