# Feedback overhaul implementation — September 22, 2026

This implements the web-app changes from `StudentSuccess_Feedback_Implementation_Spec_Latest.md`. Existing Flask blueprints, SQLAlchemy models, rule-based scoring, private-code access, course catalogs, accessibility preferences, reminders, and calendar export are retained. No production deployment was performed.

| Spec | Implemented behavior | Main files | Verification |
| --- | --- | --- | --- |
| A — Queue | Stable work-status/urgency tiers; score, deadline, planned start, and ID tie-breakers. Recommended/due/planned/subject/status sorting. Compact rows and disclosed secondary actions. | `services/task_policy.py`, `services/priority_service.py`, `services/suggestion_service.py`, `routes/task_routes.py`, `templates/tasks.html` | Tier-order and reversed-input stability tests; existing priority property tests updated for tiers; Chrome task flow |
| B — Completed | Completed tasks separated into collapsed history, newest first; start timestamps and estimated/actual durations retained. | `routes/task_routes.py`, `templates/tasks.html` | Subtask completion/history separation tests; existing history and undo tests |
| C — Timing | One timing area with mean, median, on-time percentage, sample size, signed start-delay charts, normalized subject charts, and paired duration bars. Charts have adjacent text values; insufficient history has explicit empty states. Detailed history remains disclosed. Projects do not double-count subtask measurements. | `services/timing_service.py`, `templates/_timing.html`, `routes/main_routes.py`, `services/delay_service.py`, `services/burn_rate_service.py` | Early/on-time/late/empty data and subject-normalization tests; existing delay/duration tests |
| D — Durations | Shared 10,080-minute limit for estimates and recorded actuals, creation/editing/completion, and browser validation. | `services/task_policy.py`, `app.py`, `routes/task_routes.py`, task templates, `static/js/local_planner.js` | 1,200/1,441/10,080 accepted; zero/negative/over-limit rejected; 10,080 actual minutes saved |
| E — Subtasks | One level of subtasks; inherited task metadata and optional date overrides; editable child tasks; project progress; automatic parent completion/reopening; actionable children recommended. Exact work-block splitting (40 becomes 25 + 15). Project estimates must cover manually added child estimates. | `models/task.py`, `routes/task_routes.py`, `templates/task_edit.html`, `services/task_policy.py` | Split totals, inheritance, access controls, completion/reopening, project recommendation exclusion; Chrome long-project splitting |
| F — College | Persistent high-school/college preference. College navigation uses a manual term plan, with named terms and weekly workload totals. High-school catalog/plans remain saved. | `models/user_settings.py`, `models/term_course.py`, `routes/term_routes.py`, `templates/term_plan.html`, settings/profile/course routes, `services/navigation.py` | College rendering, manual course creation, export tests; Chrome browser college persistence |
| G — Task entry | Essential fields first; planned start, ratings, recurrence, and reminders under More options. Privacy confirmation remains beside submission, with inline server errors. | `templates/tasks.html`, `templates/_nonpersonal_confirmation.html`, `routes/task_routes.py` | Four-field/default creation tests; existing privacy tests; Chrome creation without opening More options |
| H — Subjects | Case/spacing normalization in analytics and history suggestions; planner-specific and common subject suggestions; custom labels preserved in stored tasks. | `services/delay_service.py`, `services/timing_service.py`, task routes/templates, browser planner | Science/science/whitespace aggregate together; existing grouping tests |
| I — Deadlines | Date-only deadlines become 23:59 in the planner timezone. Explicit times survive. Due-within-24-hours is a separate urgency tier above ordinary future work. | `routes/task_routes.py`, `services/task_policy.py`, task forms | Eastern date-only conversion, explicit override, urgent-vs-hard task tests |
| J — Private codes | Literal explanation of the code, server storage, browser-only alternative, loss/recovery limits, and prominent existing-code link. | `templates/register.html`, `templates/_welcome.html`, `templates/landing.html` | Existing access-code tests; public entry-link test |
| K/O — Visual/product clarity | Literal hero, functional fictional planner preview, conventional CTAs, navy/blue palette, restrained utility cards, fewer repeated numbers, standard links, no pointer-follow animation. | `templates/landing.html`, `static/css/overhaul.css`, `static/js/depth.js`, shared head | Chrome mobile/desktop screenshots, overflow and JavaScript checks |
| L — Helpers | Task/subtask examples, deadline default helper, timing empty states, term-plan example and empty state. Existing course-comparison examples retained. | task/term/timing templates | Route rendering tests and browser review |
| M — Import | `.ics` file upload, preview, event selection, user-bound expiring preview token, duration selection, and external-UID deduplication. | `services/calendar_import.py`, `routes/task_routes.py`, `templates/calendar_import.html` | Preview/import/dedup/export and malformed-token tests |
| N — Today | Direct Today/full-dashboard links; Today shows one actionable recommendation. Existing persistent focus preference retained. Ranking details and runner-up comparison remain disclosed. | `templates/dashboard.html`, `routes/main_routes.py`, `services/recommendation_explanations.py` | Existing focus/explanation tests and Chrome rendering |
| First-run/mobile | Short dismissible/reopenable orientation. Larger tap targets, single-column mobile entry, no horizontal overflow in tested views. | `templates/_orientation.html`, `static/js/orientation.js`, `static/css/overhaul.css` | Chrome dismissal/reload/reopen and viewport checks |
| Browser planner | Stable ordering/sorting, separate completed section, subtasks/work blocks/progress, actual minutes, timing charts, college terms, date-only defaults, and backward-compatible backup fields. | `static/js/local_planner.js`, `templates/local_planner.html` | Chrome create/start/complete/reopen, old-shape storage loading, college save/reload |
| Preserve useful features | Reminders/snooze, `.ics` export, private-code isolation, high-school plans/comparisons, start/duration calculations, accessibility settings. JSON export now includes task IDs/parents/timestamps/actual minutes and college courses. | existing services/routes plus `routes/settings_routes.py` | Full regression suite; explicit reminder and calendar regression tests |

## Schema and data preservation

- `tasks.parent_task_id`: nullable self-reference; existing tasks remain top-level.
- `tasks.external_uid`: nullable hash of imported UID/occurrence, scoped to the planner during duplicate detection.
- `user_settings.academic_context`: defaults to `high_school` for existing users.
- New `term_courses` table: user, title, term, weekly study hours; removed with its owning account.
- `app._migrate_feedback_columns` follows the existing additive startup-migration pattern. It does not rewrite task titles, subjects, dates, or history. The migration test checks retained legacy content and repeat execution.
- Browser backups retain version 1 and accept older records without the new optional fields. Failed validation leaves existing storage untouched.
- Parent deletion is guarded while children remain; subtasks can be managed individually. Clearing history remains a separate explicit Settings action.

## Validation

- Baseline: 267 tests passed before changes.
- New coverage: `tests/test_feedback_overhaul.py` (15 cases including parametrized work-block tests).
- Final full suite: **282 passed**. Browser run: **zero JavaScript errors and zero horizontal-overflow failures** across the tested viewports/themes/scales.
- Existing assertions were revised only where requested behavior changed: urgency tiers, new duration maximum, chart/disclosure markup, and broader audience copy.
- Full-suite command: `.venv/Scripts/python.exe -m pytest -q --basetemp=.test-overhaul-release -p no:cacheprovider` (set a local `SECRET_KEY`).
- Browser command: `.venv/Scripts/python.exe scripts/check_feedback_overhaul.py`.
- Browser checks use isolated in-memory data and Chrome at 320, 390, 768, and 1440 pixels; also 200% text in dark/high-contrast modes, reduced motion, and keyboard focus. Screenshots/logs are local ignored artifacts under `.test-overhaul-browser/`.

## Intentional boundaries

- Import is file-based and available in the server-saved planner. No private calendar URL fetching, live sync, LMS API adapter, or browser-only `.ics` import is claimed.
- The bounded importer accepts UTF-8 VEVENT records with SUMMARY and DTSTART/DUE, UTC or IANA timezones, date-only events, and folded lines. It imports the listed occurrence of a recurring event; it does not expand RRULEs or custom VTIMEZONE definitions. Descriptions are omitted. Limits: 1 MB, 200 events; previews expire after 30 minutes.
- Subtasks are one level and cannot recur independently. Recurring tasks retain their existing separate behavior.
- College courses are manual, not an official institutional catalog or degree audit. Switching academic context preserves high-school plans.
- Native apps, ML ranking, hosting changes, live synchronization, and full Canvas/Google Classroom adapters remain the specification's longer-term work.
- Browser automation verifies flows/layout, not actual tester comprehension. Repeating the human mobile survey is still needed to measure first-open understanding and satisfaction.
