# Survey audit: September 22, 2026

Source: `StudentSuccess_User_Testing_Sur2026-09-22_21_05_33.xlsx`, sheet1, 18 responses and 14 columns. Compared with the current local working tree and the previous overhaul's captured screens/test logs. This is not verification of the deployed site or a new usability study.

The workbook has no written "vibe-coded" comment, no links to design resources, and no expanded visual-design/mobile questionnaire columns. That concern comes from the owner's message and earlier specification. Its absence here does not invalidate the concern. Row numbers below refer to Excel rows, including the header.

## Written feedback coverage

| Feedback | Evidence | Current status | Remaining work |
| --- | --- | --- | --- |
| Private codes are confusing; save in the browser and optionally sync | K6 | Partial. Browser-only storage already exists; create/open pages explain private codes and server storage. | Browser-only and server-saved planners are separate. There is no seamless browser-to-account upgrade/sync. The homepage still emphasizes codes and the browser option sits on the creation page. |
| Prefer a native app | L6 | Deferred, as specified in the earlier web-overhaul scope. | A responsive website is not a native app. |
| Add-task form is too long | K7 | Substantially addressed in task creation: advanced metadata is collapsed and defaults exist. | Date and optional exact time remain separate visible controls; editing is still a long form. Creation appears before the queue. Finish the short-entry layout and assess completion time with users. |
| Privacy checkbox/error was missed | K7 | Implemented: confirmation beside submit, native validation, and inline server error. | Needs user retest for discoverability. |
| Paste an iCal feed from Canvas/Google Classroom | L7 | Partial. Server planner supports file upload, preview, selection, and deduplication. | No feed URL import, recurring-series expansion, automatic refresh, or LMS API connection. File import is not the exact requested flow. |
| Compact display of today's tasks | L12 | Partial. Stable order, compact cards, separate completion history, and a Today recommendation view exist. | Today is not a dedicated date-filtered task list. The queue remains below the creation form. Completion is hidden behind an action disclosure. |
| More examples and suggestions | L13 | Implemented in task titles, subtasks, term planning, timing empty states, and existing course comparison. | Validate that examples are encountered at the point of hesitation. |
| Recommendation calculation is difficult to understand | K17 | Implemented changes: natural-language leading reason, explicit urgency tiers, optional factor breakdown. | Understanding has not been demonstrated by a new user test. Avoid equating rendered explanation text with comprehension. |
| Suggestions should improve from past behavior | L17 | Partial. A per-subject start-delay bonus already exists and remains explainable. | It uses fixed thresholds, not a learned/adaptive model, and does not personalize from every behavior. |
| Positive comments and useful core features | K13, K19; feature selections throughout | Preserved in local code. | Continue testing course comparison, reminders/export, planned-vs-actual starts, and estimated-vs-actual duration. |

The September 20 row with first-open understanding 2/5 and explanation clarity 1/5 (Excel row 5) is a reason to retest onboarding and recommendations. Its expanded mobile answers are not present in this export. The September 22 response gives 5/5 for the five product ratings and has no written complaint; there is no evidence in the file identifying which build that respondent tested.

## Earlier owner requirements

Stable ordering, separate completion history, the 10,080-minute limit, exact work-block splitting, one-level subtasks, parent progress/reopening, college terms, subject grouping, date-only deadline defaults, and consolidated timing charts are implemented locally. See `feedback-overhaul-implementation.md` for implementation/test mappings.

The visual-design requirement remains **partially addressed**. The previous implementation report's visual section should be read as a list of changes, not a conclusion that the design criticism is resolved. The prior 282 passing tests and zero-overflow browser result establish functional/layout checks, not visual coherence, accessibility certification, or user comprehension.

## Why the site can still feel assembled rather than designed

These are audit judgments grounded in current markup, styles, and previously captured screens, not quotations from respondents.

1. **Competing emphasis.** `templates/landing.html:36` gives Explore Demo and Create Private Planner the same primary visual treatment. Several lower sections repeat calls to enter the product. Choose a clear first-use path and subordinate the alternatives.
2. **Repeated orientation.** `templates/dashboard.html:39` includes the new orientation and line 53 also includes the demo checklist. A new demo visitor can encounter two introductions before the task recommendation. Use one compact orientation.
3. **Daily work is not first.** `templates/tasks.html:38` starts a large creation panel; the queue starts at line 101. For returning users, show the queue first with a compact Add task entry.
4. **Useful actions became harder to find.** Task completion is inside `Task actions` / `Complete / edit` at `templates/tasks.html:123`. Keep the current primary action visible: Start for an unstarted task, Complete for active work. Disclose editing/deletion and calculation details.
5. **Today is only partly focused.** `_timing.html` is included at `templates/dashboard.html:109` before the focus-view condition. Today still displays a timing panel and its four metrics. Put optional analytics behind an explicit destination or disclosure in this view.
6. **The product preview is a separate approximation.** `templates/landing.html:42` combines recommendation, progress, and course comparison into a hand-authored preview. Reuse the real product components with fictional data, or use current screenshots, so the preview matches what users enter.
7. **Editorial decoration remains.** The landing still contains slogan dividers, margin notes, numbered feature rows, repeated serif headings, and a graph-paper background across the whole page. Retain a small recognizable notebook accent while reducing decoration around the actual workflow.
8. **Styles are layered rather than consolidated.** `_accessibility_head.html` loads studio, accessibility, mobile, fieldnotes, depth, workspace tools, and overhaul CSS on top of page-specific CSS. Multiple files redefine the same fonts, palettes, cards, and buttons. This is a maintenance risk and a source of uneven styling; it is not proof by itself that users perceive a problem. Consolidate the visual rules while preserving accessibility behavior.

## Concrete next design pass

1. Establish shared colors, spacing, typography, borders, and primary/secondary/destructive actions. Remove superseded visual rules instead of adding another override layer.
2. Design the returning-user task screen first: compact navigation, one recommended task, a scannable queue, visible contextual action, and a small Add task entry.
3. Make Today a genuinely focused view and move optional analytics out of its initial reading path.
4. Unify onboarding and clarify the choice among demo, browser storage, and server storage.
5. Use actual planner components in the landing preview, then remove redundant decorative sections.
6. Retest with new mobile users: choose an entry path, create a task, explain the recommendation, start/complete work, and find history. Record hesitation and assistance as well as opinions about appearance.

## Useful design resources

- [Refactoring UI](https://refactoringui.com/): practical developer-oriented guidance on hierarchy, spacing, typography, and component refinement. Two free chapters are offered; the full package is paid. Start with the free material.
- [Free Refactoring UI preview: Labels are a last resort](https://refactoringui.com/previews/labels-are-a-last-resort): useful for reducing repetitive metadata labels in task rows. This is not a reason to remove accessible form labels.
- [NN/g: Five Principles of Visual Design](https://www.nngroup.com/articles/principles-visual-design/): scale, hierarchy, balance, contrast, and grouping. Apply these to the task screen so importance is obvious.
- [GOV.UK Design System: Details](https://design-system.service.gov.uk/components/details/): disclosure is for information only some users need; essential actions/information should stay discoverable. Relevant to the current hidden Complete action.
- [Mobbin](https://mobbin.com/): real application screens and flows. Study task lists, onboarding, and form patterns; compare several examples rather than copying a full brand or landing-page template.

Useful search terms: **dashboard visual hierarchy**, **task list interaction design**, **UI spacing and typography**, **progressive disclosure usability**, and **product design consistency**. The phrase "anti-vibe-coded" is less precise than the design problems being fixed.

Audit only: this review adds documentation and makes no further application changes.
