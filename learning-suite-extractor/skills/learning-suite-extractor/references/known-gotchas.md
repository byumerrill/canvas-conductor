# Known Gotchas

Things that will trip up the extractor if you don't know about them.

## 1. Async content load

Most Learning Suite routes render via Vue.js. The HTML shell loads first, then
the data and components hydrate. Always wait at least 1.5 to 2 seconds after
`navigate` before reading `<main>` or accessing `window.data`. If content is
still empty, retry once with a 4-second wait before treating it as a real
failure.

Pattern:

```javascript
new Promise(r => setTimeout(() => { /* read here */ }, 2000))
```

## 2. Chrome plugin content filter (blocking AND truncation)

The Claude in Chrome extension filters values that look like cookies, base64
blobs, or query strings. There are TWO failure modes, not one:

**Mode A: full replacement.** When the filter triggers on a whole string,
you get `[BLOCKED: Cookie/query string data]` or `[BLOCKED: Base64 encoded
data]` instead of the real value.

**Mode B: silent truncation.** When a long string contains URL-shaped
substrings, the transport truncates the value to roughly 1000 characters
and appends `[TRUNCATED]`. Splitting the string in half and reading each
half separately doesn't help, because the truncation reapplies per chunk.

**This means you cannot use `JSON.stringify(window.data)`.** It will return
mostly `[BLOCKED]` placeholders.

**Workaround pattern (in priority order):**

1. **Strip URLs preemptively** in the page-side JS before returning:
   ```javascript
   const stripUrls = (s) => (s || '').replace(/https?:\/\/\S+/g, '[link]');
   ```
   Apply to every text-shaped field before serializing the response. URLs
   are the most common trigger.

2. **Render HTML to plain text** with a throwaway DOM element, then strip
   URLs from the result:
   ```javascript
   const toText = (html) => {
     const t = document.createElement('div');
     t.innerHTML = html || '';
     return (t.innerText || '').replace(/https?:\/\/\S+/g, '[link]');
   };
   ```
   This avoids embedded `href="..."` attributes triggering the filter.

3. **Chunk at 800 chars or smaller.** If a description still gets
   `[TRUNCATED]` after URL strip, return it as an array of substring
   chunks. 800-char windows usually work. If a chunk is still blocked,
   drop to 150-char windows on that specific chunk only. (Yes, you may
   have to bisect a single problematic stretch of text. One Knowledge Check
   description in the Winter 2026 run needed 150-char windows over a
   ~150-character span; everything else was fine at 800.)

4. **Aggressive scrubbing as last resort:** strip long Base64-shaped runs
   and query-string fragments too:
   ```javascript
   const stripAll = (s) => (s || '')
     .replace(/https?:\/\/\S+/g, '[link]')
     .replace(/[A-Za-z0-9+\/]{30,}=*/g, '[long-token]')
     .replace(/[?&][A-Za-z0-9_]+=[^&\s"'<>]+/g, '');
   ```

The filter also affects:
- `data-*` attributes on elements (some are dropped)
- `Object.keys(...)` results (some keys appear as `[BLOCKED]`)
- `href` attributes on anchors that point to authenticated download endpoints

If a specific field returns `[BLOCKED]`, try reading just that field by name
in a fresh snippet. It often works on the second try.

## 3. Tool-result size ceiling

Claude in Chrome `javascript_tool` results larger than roughly 50KB get
written to a host-side persisted-output file instead of returned inline.
That file isn't accessible from the workspace shell, so you can't `cp` or
read it from a bash sandbox.

**Workaround:** never try to dump the full `window.data` payload in one
call. Split into at least four sub-extractions and keep each return under
50KB:

1. Categories + columns + classDays + period metadata
2. Events (54+ items on a typical course)
3. CalendarItems (54+ items, mostly duplicates of events)
4. Assignments (38+ items, this is the largest)

The snippets in `extraction-snippets.md` are already broken up this way.
Don't fold them back together.

## 4. URL path prefix varies per session

The course URL templates in `url-templates.md` show `/.8NDL/cid-<ID>/...`
but the actual prefix in the session may be `/.68kj/`, `/.X9aB/`, or
something else. Learning Suite redirects from `.8NDL` to the active
session's prefix on first navigate.

**Always read `location.pathname` after the first navigate** and template
your subsequent URLs from the prefix you actually landed on. The `cid-<ID>`
segment is stable; the prefix is not.

```javascript
const prefix = (location.pathname.match(/^\/\.[A-Za-z0-9]+/) || [])[0];
const cid = (location.pathname.match(/\/cid-[A-Za-z0-9_-]+/) || [])[0];
const calendarUrl = `https://learningsuite.byu.edu${prefix}${cid}/calendar`;
```

## 5. URL redirects

These routes redirect silently and you'll lose track of where you are if you
don't verify `location.pathname` after navigating:

| You navigate to                       | You actually end up at                 |
|---------------------------------------|----------------------------------------|
| `/syllabus/instructor_ta` (instructor) | `/syllabus/syllabus`                  |
| `/syllabus/course` (instructor)        | `/syllabus/syllabus`                  |
| `/syllabus/policies` (instructor)      | `/syllabus/syllabus`                  |
| `/syllabus/assignments` (instructor)   | `/syllabus/syllabus`                  |
| `/student/syllabus`                    | `/student/syllabus/instructor_ta`     |
| `/pages`                               | `/pages/id-<FIRST_PAGE_ID>`           |
| `/student/assignments`                 | (often blank, no redirect)            |

For syllabus content, always use `/student/syllabus/<section>`. The
instructor view is an editor that doesn't render content.

## 6. Sidebar IDs are masked

Page IDs in the Content sidebar are stored in `data-*` attributes on each
`.dynamicNavLink` item. The Chrome plugin filter strips these. You cannot
build the full page list from a single DOM read.

**Workaround:** click each sidebar item, wait for navigation, read
`location.pathname` (which now contains `/pages/id-XXXX`). The clicked item's
text gives you the title; the URL gives you the ID.

**Parent/child relationships** come from the `pl-N` Tailwind padding class on
each `.dynamicNavLink`. Top-level pages typically have `pl-4`, first-level
children have `pl-8`, grandchildren `pl-12`. Capture the `pl-N` value when
you read the sidebar and use it to build the tree afterward. Don't assume
the depth values; read them.

If a top-level page has children, they appear in the sidebar only when the
parent is expanded. Most courses leave them expanded, but if you read 0
children from a parent that obviously should have them, click the expand
caret first.

**Pathname page-ID regex.** The course URL also contains an `id-...` segment
(the `cid-` portion), so a naive `/id-[A-Za-z0-9_-]+/` regex picks up the
wrong one. Anchor on the prefix:

```javascript
const pageId = (location.pathname.match(/\/pages\/(id-[A-Za-z0-9_-]+)/) || [])[1];
```

## 7. Date formats: epoch seconds AND pre-formatted strings

`window.data` mixes two date formats and the docs are unhelpful about which
field is which. Trust this list, not the field name:

**Epoch seconds (`new Date(value * 1000)`):**
- `periodFirstDay`, `periodLastDay`
- `classDays[].date`
- `events[].date`
- `calendarItems[].beginDate` and `endDate` in some payloads (varies)

**Pre-formatted `"YYYY-MM-DD HH:MM:SS"` strings (Mountain Time, no offset):**
- `assignments[].beginDate`, `dueDate`, `visibleDate`, `scoreVisibleDate`,
  `zeroScoresDate`
- `calendarItems[].beginDate` and `endDate` in most payloads

**Output ISO 8601 with the right Mountain Time offset.** Winter is `-07:00`
(MST); after DST starts (second Sunday of March) it's `-06:00` (MDT); back
to `-07:00` on the first Sunday of November. Most BYU semesters cross at
least one DST boundary, so don't hardcode a single offset.

The `scripts/epoch_to_iso_mt.py` helper bundled with this plugin does this
correctly for any year. Use it from your YAML-emitter script.

## 8. Empty syllabus sections and empty Office Hours

If an instructor has never filled out a syllabus section (e.g. Course
Information), the student-view page renders an empty `<main>`. Don't treat
this as an extraction failure. Record `empty: true` in the section's
front-matter and write an empty body. Note it in the Phase 5 summary so the
user knows to either fill it in or leave it intentionally blank.

The Instructor/TA section sometimes renders just a name and contact info
with a bare `Hours:` line and no value. That's a 130 to 200 char total, not
empty. Don't flag it as a failure; record it as-is.

## 9. Content pages may contain student rosters (PII)

Some content pages (commonly titled "Group Assignments," "Class Roster,"
"Project Teams," etc.) contain full student names paired with group IDs or
section numbers. The skill explicitly excludes student-identifying data
from extraction.

**Before capturing a content page body**, scan for roster patterns:

- Repeated `Lastname\tFirstname\tgroup_NN` rows
- Repeated `Last, First` patterns with N > 10
- Headers like "Last Name | First Name | Group" or "Roster" or "Students"

If detected, capture metadata only (id, title, sidebar position, attachment
count) and write `excerpt: "[Student roster — body intentionally not captured per privacy scope]"`
into the page entry. Flag it in the Phase 5 open-issues section so the user
knows you saw it and skipped intentionally.

## 10. Content page attachment markup

Learning Suite renders attachment lists as alternating text-and-anchor
sequences:

```html
<p>2026-01-13 Lecture 2.pdf <a href="plugins/Upload/...">Download</a></p>
```

The filename is in a text node or surrounding `<p>`, NOT a label or
`alt` attribute on the anchor. So `previousSibling.textContent` and
similar DOM-walk approaches are unreliable.

**Use regex on `main.innerText` instead:**

```javascript
const text = m.innerText;
const filenameRegex = /([^\n]+?\.(?:pdf|pptx?|xlsx?|docx?|zip|R|csv|md|html|txt|json))\s+Download/gi;
const filenames = [...text.matchAll(filenameRegex)].map(x => x[1].trim());
const hrefs = Array.from(m.querySelectorAll('a[href*="fileDownload"]')).map(a => a.getAttribute('href'));
const attachments = filenames.map((name, i) => ({ filename: name, href: hrefs[i] }));
```

This pairs N filenames with N hrefs positionally. Sanity-check that the
counts match before writing to disk.

## 11. Past semesters

The course selector menu lists every prior course the instructor has taught.
Each has its own `cid-XXXX`. Re-run the extractor per course; do not try to
extract multiple semesters in one pass. Course slugs and output folders
should reflect the period (e.g. `is-566-w26`, `is-566-w25`) so you can diff
across semesters later.

## 12. The `Print` and `Link` icons on the syllabus

These are Vue click handlers, not regular anchors. The Print icon opens a
print preview dialog (which the agent cannot read from). Don't try to use
either icon for content extraction. The student-view subroutes already
render full content.

## 13. Plagiarism check, rubrics, and attachments

Some assignment fields are objects, not scalars: `rubric`, `attachment`,
`exceptions`. These may be `null` for most assignments and populated for a
few. The pick function in `extraction-snippets.md` handles both cases by
preserving the value as-is. If the value is a complex object, it'll be
dumped to YAML as-is and may contain `[BLOCKED]` placeholders for nested
sensitive fields. That's expected.

## 14. `iCalAvailable` and the iCal export

The schedule has a public iCal feed (visible as `iCalAvailable: true` in
`window.data`). The URL is shown by the "Get iCalendar Feed" button on the
schedule page. The extractor does NOT capture this URL because it's
session-scoped and not useful for archiving. If the user asks, the URL is
findable on the page but treat it as ephemeral.

## 15. Lecture / assignment numbering gaps are normal

Faculty often delete or skip-number content (e.g. "Lecture 14" then
"Lecture 17", or "Knowledge Check Week 5" then "Knowledge Check Week 7" with
no Week 6). Don't try to fill in gaps or flag them as missing. Just record
what's there.
