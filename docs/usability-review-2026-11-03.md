# Suggested changes review — November 3, 2026

Reviewed the pasted suggestions as feedback, not as instructions to change security, retention, or publish claims without evidence. Prioritized small improvements using the existing Flask app, browser storage, and styles. No new dependencies, migrations, paid services, or AI generation calls were needed. These changes are local; this pass does not deploy them.

## Implemented

| Area | Changes |
| --- | --- |
| Landing | Prominent sample/privacy explanation, student-built introduction, three sample priority scenarios, checklist comparison. Samples do not change a saved plan. |
| Sign-in | Password-manager hint, no-email explanation, browser backup guidance that distinguishes backups from password recovery. |
| Dashboard | Encouraging caught-up message, tomorrow preview, completion donut with text counts, course progress bars, weekly recorded time against study budget, estimated/recorded comparison by course. Long task-duration charts initially show five rows. |
| Tasks | Direct AI-drafting link and quick course filters alongside the existing search/select controls. |
| AI | Remaining account daily requests and UTC reset explanation; research, lab, and exam prompt examples. Replacing existing text requires confirmation; choosing an example does not call AI. |
| Course plan | Move a high-school course to another grade without deleting/recreating it; duplicate and ownership protection. Workload warnings link to editable hours; missing prerequisites link to catalog search. |
| Courses | Over-budget course-load warnings near the top of the explorer. |
| Calendar | Copy private subscription URL, with manual-copy fallback; more prominent explanation that exports contain deadlines rather than study-session schedules. |
| Settings | Search that opens matching sections and retains unsaved input; stronger danger-section border. |
| Updates/tutorial | Latest-release badge, clearer release-search placeholder, tutorial section progress indicator. |
| Policy/help pages | Section navigation, concise privacy summary/data-flow explanation, links to account controls/export, clearer keyboard help. Placeholder email replaced with public project issue tracker for non-sensitive feedback and explicit private-support limitation. |
| Browser storage | Local storage size/presence and focus-entry count, downloadable browser-plan backup, clearing-site-data guidance. No upload or attempt to read HTTP-only cookies. |
| Park a thought | Review a thought as a task draft; no task is saved until submission. Saved thoughts retain their original note. Temporary/tab-only behavior and Escape shortcut are explained. |

Charts count leaf tasks to avoid counting projects and their steps twice. Time charts use only recorded minutes on completed tasks, exclude tracking-disabled completions, respect the planner timezone/week start, and disclose attribution to completion date. Timer sessions and elapsed wall-clock time are not treated as study time.

## Existing capabilities retained

Browser-only planning and backups, optional account transfer, editable AI drafts, course workload/prerequisite checks, calendar subscription/import, sticky settings save controls, live release search, and collapsible tutorial/focus controls already address parts of the suggestions.

## Deferred

- Testimonials: need an approved, authentic quote.
- Passkeys, password recovery, native mobile apps, calendar OAuth: larger authentication/platform work.
- Bulk task editing and a multi-step task wizard: broader workflow changes requiring additional validation.
- Graduation-rule automation and credit-to-hours conversion: require authoritative institution-specific requirements; no invented conversions.
- Automatic course-hour correction: hours remain user controlled.
- Streaks, energy-based scheduling, AI pacing sliders, automatic timer logging, and semester recaps: require clearer behavior and trustworthy history before adding them.
- Peer sharing, reusable shared settings, and feedback collection/popups: require product/privacy decisions and storage/moderation work.
- Soft deletion/account recovery: changes retention promises and needs a deliberate design; deletion behavior remains unchanged.

## Validation

- Initial affected-route/policy/AI/settings/focus/dashboard tests: 59 passed; one test still expected the removed placeholder contact language.
- Updated that expectation and ran policy, course routes, and new insight/move/quota tests: 13 passed.
- Chrome browser checks passed for sample switching, charts, draft-only thought transfer, course filters, settings search, legal navigation, and storage inspection, with horizontal-overflow checks at 390px and 1440px.
- Browser checking caught and fixed matching `timezone` against the visible label `time zone`.
- `git diff --check` passed. No full-suite rerun or production deployment in this pass.
