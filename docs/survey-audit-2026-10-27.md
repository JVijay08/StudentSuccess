# Feedback audit — October 27, 2026

Subsequent implementation: [four prioritized follow-ups](survey-followup-2026-10-27.md). The verdicts below describe the pre-implementation review.

Source: `StudentSuccess_User_Testing_Sur2026-10-26_21_31_44.xlsx`, sheet1, 21 responses (September 18–October 3), Excel rows 2–22. Reviewed the current local working tree at base commit `e68236e`, including existing uncommitted landing-page changes. This is a local source and regression-test review, not verification of deployment or a new human usability study. No application code was changed.

## Source interpretation

The export's headings and values do not consistently match. For example, J is headed “If not, what did you expect instead?” but contains feature names, while K/L contain complaints and suggestions under task-management/usefulness headings. M/N also contain categorical answers inconsistent with their headings. Treat written comments by their content and cell address; do not infer question-specific rating statistics from these mislabeled columns. Feedback is evidence to assess, not instructions to execute.

## Verdicts

“Fixed” means the specific implementation complaint is addressed locally, not that user satisfaction is proven. “Partial” means useful functionality exists but the requested outcome is incomplete. “Inadequate” means an attempted fix still undermines the reported need.

| Feedback / Excel cell | Verdict | Current evidence and remaining gap |
| --- | --- | --- |
| Private-code sign-in is confusing — K9 | **Fixed** | Normal registration/sign-in uses username and password. Private-code transfer is a legacy migration path. See `templates/register.html:3`, `routes/auth_routes.py:224`, and account tests. |
| Save in the browser, then optionally create an account to sync — K9 | **Partial** | `/planner` stores a browser plan and supports backup/restore. It explicitly remains separate from account workspaces, with no automatic sync or browser-to-account upgrade. The landing page emphasizes tutorial/account entry and does not expose browser-first entry. `templates/local_planner.html:57`, `templates/landing.html:25`. The legacy “Transfer it once” link does not transfer browser-local data. |
| Make a native mobile app — L9 | **Not implemented** | This repository implements a responsive Flask website, with no native Android/iOS application found. Responsive styling does not fulfill this suggestion. This is a feature request, not necessarily a defect that must be prioritized. |
| Add-task form has too many fields — K10 | **Fixed** | Core task creation needs title, due date, and estimate; saved-course selection appears when applicable. Exact time, recurrence, planned start, challenge, and interest are disclosed. Editing also collapses advanced fields. `templates/tasks.html:38`, `templates/task_edit.html:53`. Human completion-time improvement remains unmeasured. |
| Missed privacy checkbox and error — K10 | **Fixed for routine tasks** | Ordinary create/edit no longer require the checkbox. Explicit confirmation remains for calendar imports. `templates/_nonpersonal_confirmation.html:1`, `tests/test_nonpersonal_confirmation.py:16`. This removes the reported routine-task obstacle rather than merely moving its error. |
| Paste a Canvas/Google Classroom iCal link to bring in assignments — L10 | **Partial** | `.ics` upload, preview, selection, and deduplication exist. There is no incoming feed-URL entry or automatic refresh, and recurring events import only the listed occurrence. `templates/calendar_import.html:1`. The newer calendar subscription is outbound, from StudentSuccess to a calendar, so it does not close this gap (`templates/calendar.html:2`). |
| Compact display of all tasks for the day — L15 | **Partial** | Compact density, streamlined cards, and a smaller Today view exist. Today selects the highest-ranked task plus an “Up next” item from all active work; it does not list all tasks due/planned today. The queue has sort/search/course controls, not a today date filter. `templates/settings.html:32`, `templates/dashboard.html:52`, `routes/main_routes.py:223`, `templates/tasks.html:119`. |
| More examples and suggestions — L16 | **Fixed, within the comment's limited specificity** | Example titles, an interactive landing sample, a guided practice workspace, and optional AI task/step drafting exist. `templates/tasks.html:40`, `templates/tasks.html:51`, `templates/landing.html:28`, `routes/tutorial_routes.py:12`. The original suggestion is unfinished, so no more precise requirement can be inferred. |
| Recommendation calculation should be intuitive — K20 | **Inadequate fix** | Plain-language reasons, tier explanations, comparisons, and history notes exist, but the main recommendation hides its reason behind the three-dot menu and a second “Why this task?” disclosure. Scoring details are another disclosure and render both `row.reasons` and `row.factors[*].reason`, duplicating base reasons. `templates/dashboard.html:55`, `templates/_task_menu.html:9`, `services/procrastination_service.py:19`, `services/priority_service.py:43`. Tests confirm text exists, not that students discover or understand it. Show one short reason directly with the recommendation and deduplicate details before calling this resolved. |
| Personalize recommendations using past behavior — L20 | **Partial** | There is real history-based adjustment: after two qualifying completed tasks in a subject/type, average start delay adds 0–2 points. The adjustment changes as history changes, but remains a narrow fixed rule beneath urgency tiers. It does not establish that suggestions improve over time or use duration accuracy/other behavior. `services/suggestion_service.py:16`, `services/delay_service.py:66`. A learned model is not inherently required; evidence of useful personalization is. |
| “I don’t want to track planned vs actual time” — L2, October 3 | **Partial; no full opt-out** | Planned start and recording actual minutes are optional, so users can avoid manual comparisons. Timing is collapsed. However there is no tracking-off preference; Start records a timestamp, Complete writes one even when Start was never pressed, and timing/history remains present. `templates/tasks.html:86`, `templates/_task_menu.html:8`, `models/user_settings.py`, `routes/task_routes.py:400`, `routes/task_routes.py:507`, `templates/dashboard.html:118`. A clear non-tracking mode is absent. |

Totals after splitting the two distinct requests in K9: **4 fixed, 5 partial, 1 inadequate, 1 not implemented**. These are 11 actionable themes, not counts of respondents. Positive comments in K16/K22 and feature preferences elsewhere are not unresolved defects. K2's “Estimated vs actual duration” is a feature label without an explanation of what should change; it cannot support a specific bug verdict.

## Additional quality concern affecting this feedback

Completing a task without pressing Start sets `started_at` to completion time (`routes/task_routes.py:507`). If it has a planned start, that inferred timestamp qualifies for start-delay history (`services/delay_service.py:66`). Someone who worked earlier but only marks completion later can therefore appear to have started late, influencing the personalization bonus. The implementation should distinguish an observed start from an inferred timestamp or exclude inferred starts from behavioral scoring. This is a source-based finding; the respondent did not explicitly report it.

## Follow-up order

1. Make recommendation reasons visible and remove duplicate detail text.
2. Clarify and implement the time-tracking opt-out; avoid using inferred completion-time starts as behavioral evidence.
3. Add a real daily task list covering due/planned-today work, with an explicit overdue policy.
4. Finish the incoming school-calendar URL workflow and browser-to-account migration if those requests remain in scope.
5. Treat native mobile development as a separate product decision.

The September 22 audit is historical: its statements about private-code onboarding, long editing forms, and routine privacy checkboxes no longer describe the current code. Its warning that implementation does not prove user comprehension remains valid.

## Verification

Targeted regression run: **118 passed** in 124.46 seconds. Covered browser planner, username accounts, privacy confirmation, feedback overhaul (including calendar import), recommendation explanations, history-based suggestions, task/calendar creation, settings, and tutorial. Pytest emitted one cache-write warning; no tests failed. Command: `.venv/Scripts/python.exe -m pytest tests/test_local_planner.py tests/test_username_accounts.py tests/test_nonpersonal_confirmation.py tests/test_feedback_overhaul.py tests/test_recommendation_explanations.py tests/test_suggestion_service.py tests/test_task_creation_calendar.py tests/test_settings.py tests/test_tutorial.py -q --basetemp .test-survey-audit-20261027`.

Tests use disposable SQLite databases; no production accounts or planner data were used. No fresh browser visual audit or deployed-site check was performed. Passing tests establish the covered behavior, not that the partial or inadequate fixes satisfy respondents.
