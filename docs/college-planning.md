# College directory and dual enrollment

## Shipped scope

Both academic presets share a state/name/city-searchable institution directory at `/colleges`.
Choosing an institution saves an optional default in settings; it does not assert attendance.
Each course saves its own institution ID, so a term may contain more than one college.
Clearing/changing the default does not rewrite old courses. Switching presets preserves plans.

The term planner supports course name/code, credits, weekly study hours, term, planning
status, optional description and public catalog URL. Dual-enrollment courses also require
a grade (9â€“12) and appear in the corresponding year of the high-school plan. College
study hours are shown separately from the high-school reference workload rating.
Only planned courses contribute to the term's planned weekly-hours total; considering
and completed courses remain visible. Credits are user-entered college credits, not
verified high-school equivalencies or transfer guarantees.

Edits/removals are scoped to the signed-in account. All course fields and the selected
college ID are included in account export and removed with the account through the
existing relationship cascade. Existing term courses migrate as college/planned, with
no institution attached; no rows are deleted. The browser-only planner does not sync
these server-stored selections.

## Directory provenance and maintenance

- Source: [NCES IPEDS HD2024](https://nces.ed.gov/ipeds/datacenter/data/HD2024.zip).
- `data/colleges.json` contains 5,994 institutions marked active in that release,
  covering all 50 states, DC, and other listed territories/jurisdictions.
- Stable identifier: IPEDS UNITID, stored as a string. Institutions include name,
  aliases, city, state, website, sector, and degree-granting flag.
- The file records source URL, release year, retrieval timestamp, SHA-256 of the source
  ZIP, and a coverage statement. It excludes officials' names, contact details, and
  street addresses. No API key or per-user external request is needed.
- This is a **2024 directory snapshot**, not a guarantee of every college operating
  today, dual-enrollment participation, or a current course catalog. The 2025 ZIP URL
  was unavailable when checked; do not silently relabel the 2024 release as current.

To refresh, obtain an official HD ZIP and run:

```powershell
.venv\Scripts\python.exe scripts/import_colleges.py path/to/HD2024.zip --year 2024
```

Review counts, schema, coverage, removed/renamed IDs and source changes before committing
an updated snapshot. Preserve an archive/mapping for IDs referenced by existing plans
before removing retired institutions. The importer validates IDs/counts before replacing
the output; unknown institutions can be left unselected in a student course plan.

## Course catalog and future AI roadmap

Directory records and student-entered course notes are deliberately separate.
IPEDS and College Scorecard provide institution/program information, not a complete
nationwide catalog of individual courses and transfer agreements. A large trustworthy
catalog requires institution/state sources, update processes and explicit coverage.

Next catalog ingestion should begin with a bounded set of official partner catalogs
and store institution ID, catalog year, course code, title, description, credits/unit
system, prerequisites, source URL, retrieval date, license/permission and verification
status. Version records rather than overwriting historical requirements. Keep published
offerings separate from semester sections, local high-school approvals, transfer rules,
and a student's selected course. Do not fill missing records with invented descriptions.

Before AI recommendations, add source-backed retrieval with citations and catalog-year
checks; never treat user-entered notes as verified public catalog records. Keep private
student plans separate from the shared catalog and do not repurpose them for training.
Course-to-task links currently use normalized subject names (80 characters), so equal
names across institutions/terms share a task group; explicit course enrollment IDs are
the next step before institution-specific AI or transfer recommendations.

## Verification

Tests cover source coverage/search, selection, dual-course placement, editing/status,
preset preservation, task links, exports, invalid numbers/IDs/URLs, ownership and
legacy migrations. Browser checks exercise directory selection, dual-course creation,
editing, mobile/desktop reflow and the no-JavaScript directory fallback.

Release checks: 303 Python tests passed. Both the college workflow browser audit and
the existing notebook browser regression audit reported no JavaScript errors or visual
issues at their tested viewports (320, 390, 768, 1440 pixels; dark/high-contrast at 200%).

## Integrated preset update

High-school students add and edit college courses directly inside `/courses`, alongside
high-school choices. The existing `/terms` URL redirects there in high-school mode.
Inline state/name lookup keeps an unfinished course draft intact; GET search also works
without JavaScript. Saved courses retain institutions, grade placement and task links.

College mode retains term planning and adds an optional program, explicitly selected
current term, personal credit target and course categories (major, general education,
elective or prerequisite). Only planned courses in the selected term count toward its
summary; missing credits are identified. With no selected term, a single existing term
is used; multiple terms require choosing one. Preset switches preserve both plans.
The new settings and category columns migrate additively and appear in account exports.
