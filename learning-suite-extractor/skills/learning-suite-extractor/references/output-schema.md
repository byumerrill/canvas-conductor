# Output Schema

The extractor writes to an output directory chosen by the user at runtime
(default suggestion: `~/Desktop/learning-suite-extract/`). Inside, the layout
is fixed.

## Directory layout

```
<output_dir>/
  <course-slug>/                 # e.g. is-566-w26
    <period>/                    # e.g. 20261 (optional nesting)
      00-summary.md              # human rollup + verification report
      01-course.yml              # course id, name, period, sections
      02-categories.yml          # grading categories + weights
      03-assignments.yml         # full assignment list
      04-schedule.yml            # class days, columns, calendar items, events
      05-syllabus/
        instructor_ta.md
        course.md
        policies.md
      06-content-index.yml       # pages tree with attachment refs
      raw/
        calendar-meta.json         # categories, columns, classDays, period
        events.json                # event names rendered to plain text
        calendar-items.json        # calendar item descriptions rendered to plain text
        assignments.json           # full assignment list with descriptions
        syllabus-instructor_ta.html
        syllabus-course.html
        syllabus-policies.html
```

YAML is the structured-data format (more diff-friendly and human-skimmable
than JSON). Always preserve the `raw/` snapshots so the user can recover
fields the structured outputs omitted.

> **Tip.** The bundled `scripts/build_yaml.py` reads the `raw/*.json` files
> and emits all four top-level YAML files in one pass. Use it instead of
> hand-rolling YAML emission from inside the agent loop.

## File contents

### 01-course.yml

```yaml
extracted_at: 2026-05-13T15:42:00Z
source: https://learningsuite.byu.edu/.8NDL/cid-G0MT9FJSKEkO/home
course:
  id: G0MT9FJSKEkO
  title: IS 566 - Data Engineering
  period: "20261"
  period_label: Winter 2026
  period_first_day: 2026-01-04
  period_last_day: 2026-04-25
  sections:
    - "IS 566 Section 001 (TTh 12:30-1:45, 184 TNRB)"
    - "IS 566 Section 002 (TTh 2:00-3:15, 2107 JKB)"
    - "IS 566 Section 003 (TTh 3:30-4:45, 180 TNRB)"
sections_extracted:
  - schedule
  - assignments
  - categories
  - syllabus
  - content
sections_skipped:
  - syllabus.assignments_subsection (duplicates assignments)
  - syllabus.schedule_subsection (duplicates schedule)
```

### 02-categories.yml

```yaml
categories:
  - id: <category_id>
    title: Lab Assignments
    display_order: 1
    raw_weight_sum: 200       # sum of weight values across assignments in this category
    weight_pct: 40.0          # raw_weight_sum / total_graded_weight, rounded to 1 decimal
    equal_assign_weight: true
    low_scores_to_drop: 0
    extra_credit: false
    graded: true
    calendar_only: false
  - ...
```

### 03-assignments.yml

```yaml
assignments:
  - id: <assignment_id>
    name: "Lab: Environment Setup"
    short_name: "Lab 01"
    category_id: <category_id>
    category_title: Lab Assignments
    type: assignment           # or Exam, StudentRating, etc.
    points: 10
    weight: 10
    begin_date: 2026-01-07T08:00:00-07:00
    due_date: 2026-01-14T23:59:00-07:00
    visible_date: null
    display_order: 1
    extra_credit: false
    graded: true
    allow_late_submission: true
    late_penalty: null
    online_submission: file
    score_entry: points
    allow_score_drop: false
    has_attachment: false
    has_rubric: false
    url_slug: "abc-"
    description: |-
      <prose, preserved as-is from Learning Suite with URLs replaced by [link]>
  - ...
```

### 04-schedule.yml

```yaml
period: "20261"
period_first_day: 2026-01-04
period_last_day: 2026-04-25
columns:
  - id: <col_id>
    title: Topic
    display_order: 1
class_days:
  - date: 2026-01-06
    visible: true
    id: <class_day_id>
calendar_items:
  - id: <item_id>
    heading_id: <column_id>
    begin_date: null
    end_date: 2026-01-06T23:59:00-07:00
    description: |-
      Lecture 1: Intro to the course
events:
  - date: 2026-01-14
    epoch: 1736899140
    column: "Class Topics"
    display_order: 1
    name: |-
      Lab: Environment Setup due
```

### 05-syllabus/<section>.md

Each section gets a markdown file with YAML front-matter:

```markdown
---
section: instructor_ta
source_url: https://learningsuite.byu.edu/.8NDL/cid-G0MT9FJSKEkO/student/syllabus/instructor_ta
extracted_at: 2026-05-13
char_count: 418
empty: false
---

# Instructor/TA Info

(rendered text content here)
```

If the section is empty, set `empty: true` and leave the body blank.

### 06-content-index.yml

```yaml
pages:
  - id: id-IH0C
    title: Lecture Slides and Recordings
    parent: null
    published: true
    display_order: 1
    indent: 4                # raw pl-N value from the sidebar
    excerpt: "Lecture Slides:"
    attachments:
      - filename: "2026-01-13 Lecture 2 - Data Engineering.pdf"
        href: "plugins/Upload/fileDownload.php?fileId=..."
      - filename: "2026-01-15 Lecture 3 - Docker.pdf"
        href: "plugins/Upload/fileDownload.php?fileId=..."
    external_links:
      - title: "R for Data Science"
        href: "https://r4ds.hadley.nz"
  - id: id-XXXX
    title: Assignment Solutions
    parent: null
    children: [id-YYYY, id-ZZZZ, ...]
    published: true
    display_order: 2
    indent: 4
    attachments: []
  - id: id-YYYY
    title: is-566-02-docker-mastery-solution
    parent: id-XXXX
    published: true
    display_order: 3
    indent: 8
    attachments: [...]
```

When a content page contains student-identifying data (a roster, a list of
groups by name, etc.), capture only metadata and write:

```yaml
  - id: id-PIiI
    title: Group Assignments
    parent: null
    excerpt: "[Student roster — body intentionally not captured per privacy scope]"
    attachments: []
```

Flag the page in the Phase 5 summary so the user knows it was intentionally
skipped, not missed.

### 00-summary.md

Plain markdown with the verification report. See SKILL.md Phase 5 for the
required sections (counts table, skipped items, spot-check sample, file
map, open issues).

The bundled `scripts/verify_extract.py` reads the emitted YAML files and
generates the counts table and file map automatically. The spot-check and
open-issues sections are still up to the agent to write.

## Date conversion rules

`window.data` returns dates in TWO formats. Trust this list, not the field
name:

**Epoch seconds (Unix; multiply by 1000 for JavaScript Date):**
- `periodFirstDay`, `periodLastDay`
- `classDays[].date`
- `events[].date`

**Pre-formatted `"YYYY-MM-DD HH:MM:SS"` strings (Mountain Time, no offset
included):**
- `assignments[].beginDate`, `dueDate`, `visibleDate`, `scoreVisibleDate`,
  `zeroScoresDate`
- `calendarItems[].beginDate`, `endDate` (in most payloads)

```javascript
// epoch seconds → ISO with offset
new Date(epochSeconds * 1000).toISOString()
```

Output ISO 8601 with the right Mountain Time offset:
- MST (`-07:00`) before the second Sunday of March and after the first
  Sunday of November
- MDT (`-06:00`) between those dates

Most BYU semesters cross at least one DST boundary. Don't hardcode a single
offset.

The bundled `scripts/epoch_to_iso_mt.py` does this correctly for any year.
`scripts/build_yaml.py` uses it. If you write your own emitter, use the
same helper.
