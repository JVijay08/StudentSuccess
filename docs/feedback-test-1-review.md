# Test 1 feedback review

This is the original audit. See [implementation status](feedback-test-1-implementation.md) for the fixes made after this review and the remaining source-verification limitation.

Reviewed September 26, 2026 against commit `4b6bfc4` and all three pages, including embedded screenshots, of StudentSuccess Test #1 Feedback.pdf. The PDF is feedback evidence; proposed new features below are not represented as implemented. No private planner data was inspected.

## Already released

- Removed duplicate Add task actions from the empty dashboard.
- Redesigned the current-task card with primary actions and a three-dot menu. Rescheduling is available for unstarted tasks; started tasks retain their original planned start for accurate history and can still have their deadline edited.
- Moved ranking explanations and optional recorded minutes out of the main task card. The long-description screenshot in the PDF shows the previous recommendation layout.
- Completing a task no longer requires entering minutes or accepts an estimate prefilled as actual time.
- Fixed large-text task-menu rendering and the empty state after finishing the queue.

Release validation: 346 tests passed, 213 responsive views without detected layout issues or JavaScript errors, and live start/complete/empty-state checks passed. These checks do not establish that the remaining feedback below is resolved.

## Remaining checklist

| Priority | Feedback | Finding and next action |
| --- | --- | --- |
| P1 | Session expires or host wakes; Extend time appears frozen | Confirmed client-side recovery gap: `static/js/accessibility.js` does not check HTTP status, redirects, or response content and has no network-error handling. A redirected login response can be treated as a successful extension. Add bounded loading, retry, and explicit sign-in recovery. Test expired sessions and slow/offline requests separately. A hosting restart as the cause of logout is not established. |
| P1 | Broken/mixed course filters | `routes/course_routes.py` gives an AP/IB catalog precedence over a selected state. That behavior is tested but confusing when both controls look active. Clarify the scope and active filters; reset incompatible filters and test successive state/program changes. Georgia's sparse data is an additional issue, not solely a filter bug. |
| P1 | Corrupted course names and duplicate AP offerings | A local data scan found 21 titles containing "prerequisite" in `courses_ap.json`, 168 in Arkansas, and one in Indiana. Multiple state catalogs also contain exact-name duplicate groups. Audit against source records; separate titles from descriptions and prerequisites. Preserve course IDs and saved plans. Do not merge genuine variants solely because names match. The AP file has no exact case-insensitive name duplicates in this scan; cross-source equivalence still needs review. |
| P1 | Missing Georgia ELA, Health and Personal Fitness | Georgia uses `data/courses.json`, explicitly a partial local reference. Its English/literature matches are AP/IB; the reported Health and Personal Fitness names are absent. Restore verified local coverage from source material and make coverage limits prominent. Do not invent district offerings. |
| P1 | Saved dual courses missing when creating a task | Backend already includes every saved `TermCourse` plus resolvable planned high-school courses in suggestions. That does not prove the reported browser selection works. Reproduce with several synthetic high-school and dual courses; inspect the native suggestion list, filtering, unresolved catalog IDs, and 80-character truncation. Prefer a clearly browsable saved-course picker. |
| P2 | Adding a course returns to page top | Course cards have no stable return anchors, unlike task cards. Return to the added card, preserve filters, and announce confirmation without losing context. |
| P2 | Apply filters requires excessive scrolling | Only one submit button appears after all filter controls. Provide an accessible, readily reachable apply/reset area and simplify secondary filters on mobile. |
| P2 | Course browsing feels cramped and janky | Rework the explorer as a coherent flow, with more useful result width, concise cards, explicit scope, and accessible mobile filters. Verify long titles and keyboard navigation. |
| P2 | Two links to four-year plan | Header always includes both contextual Back and My Four-Year Plan; they can share a destination. Render one when destinations match. |
| P2 | State/source labels; canonical AP/IB | Cards currently show course type without per-card provenance. Add source/coverage labels and canonical relationships for verified equivalent offerings, preserving documented state variants and saved references. |
| P2 | College selector only says Not selected / not listed | The screenshot confirms an empty selector. Search exists in a separate disclosure, so this is not an absent college database feature. Integrate search with the selector, provide a clear empty state, and explain manual entry. Retain multiple-college support per course. |
| P2 | Add In progress to course status | Screenshot refers to college-course planning status. Current options are Considering, Planned, Completed. Add In progress consistently across validation, forms, display, filtering, and editing. |
| P2 | Subtasks hard to discover | Subtasks exist on the task edit page and course grouping, but there is no dedicated progression page. Make the entry point explicit. A task-detail page with individually completable steps is a new design proposal; provide an accessible list alongside any trail visualization. |
| P2 | Mobile deadlines blend into metadata | Partially addressed: the redesigned recommendation card separates/emphasizes the due date. Queue rows still combine subject, effort, and deadline in one paragraph. Give deadlines consistent, distinct treatment in all task views. |
| P3 | Long task descriptions | The specific screenshot shows ranking explanations, now hidden in the task menu. Check the expanded explanation for concise wording; retain useful transparency. Corrupted course-title text is a separate unresolved data issue above. |
| P3 | Flexibility for long breaks | Optional manual actual minutes now avoid equating elapsed time with effort. There is no explicit break allowance or pause/resume feature. Design flexibility separately from focused effort and due dates; explain what each duration means before adding more controls. |

## Suggested delivery order

1. Session recovery and a reproducible saved-course-picker check.
2. Catalog quality, scope/filter behavior, and source verification together.
3. Course explorer interaction fixes, integrated college selection, and In progress status.
4. Consistent mobile deadlines and discoverable task/subtask detail flow.
5. Evaluate break flexibility after testing the simpler task flow.

This is a review and backlog, not a claim that these remaining items have shipped.
