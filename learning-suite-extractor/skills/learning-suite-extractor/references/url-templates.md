# Learning Suite URL Templates

Replace `<ID>` with the course's `cid-XXXX` segment.

> **Important about the path prefix.** The templates below show `/.8NDL/`
> but the prefix in your session may be different (`/.68kj/`, `/.X9aB/`,
> etc.). Learning Suite silently redirects from `.8NDL` to the active
> session prefix on first navigate. Read `location.pathname` after the
> first navigate and template from the prefix you actually landed on. The
> `cid-<ID>` segment is stable; the prefix is not. See `known-gotchas.md`
> §4 for the regex.

## Top-level routes

| Purpose                  | URL                                                       |
|--------------------------|------------------------------------------------------------|
| Course home              | `/.8NDL/cid-<ID>/home`                                     |
| Schedule (canonical)     | `/.8NDL/cid-<ID>/calendar`                                 |
| Syllabus instructor view | `/.8NDL/cid-<ID>/syllabus/syllabus`                        |
| Assignments (instructor) | `/.8NDL/cid-<ID>/home/assignments`                         |
| Content (pages)          | `/.8NDL/cid-<ID>/pages`                                    |
| Individual page          | `/.8NDL/cid-<ID>/pages/id-<PAGE_ID>`                       |

## Syllabus subroutes (use student view for content)

| Section             | URL template                                                  |
|---------------------|----------------------------------------------------------------|
| Instructor/TA       | `/.8NDL/cid-<ID>/student/syllabus/instructor_ta`               |
| Course Info         | `/.8NDL/cid-<ID>/student/syllabus/course`                      |
| University Policies | `/.8NDL/cid-<ID>/student/syllabus/policies`                    |

The instructor-view URLs (`/syllabus/<section>`) silently redirect to the
editor index `/syllabus/syllabus` and do NOT render content. Always use the
`/student/syllabus/<section>` form.

## URL behavior notes

- The course selector menu lists every prior course the instructor has
  taught. Each has its own `cid-XXXX`. Re-run the extractor per course; do
  not try to extract multiple semesters in one pass.
- After every navigate, verify `location.pathname` matches what you expected
  before extracting. Several routes redirect.
- The `/pages` route always redirects to `/pages/id-<FIRST_PAGE_ID>`. That's
  expected, not an error.
- When extracting the page ID from `location.pathname`, anchor your regex
  on `/pages/` so you don't accidentally match the `cid-<ID>` segment.
