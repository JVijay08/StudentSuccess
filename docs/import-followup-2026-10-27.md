# Browser transfer and incoming school calendars — October 27, 2026

## Browser plan transfer

The browser planner's Storage section and account Settings link to `/planner/transfer`. Sign-in preserves this destination; new accounts return to it after onboarding. Practice accounts cannot receive a transfer.

Users can select the locally saved plan or upload a version-1 JSON backup, up to 1 MB, 2,000 tasks, and 200 courses. Selecting the local plan only prepares a file in the browser. Preview explicitly uploads it; saving requires a second confirmation. Account-bound signed previews expire after 30 minutes. No browser data is erased or replaced, and nothing continuously syncs.

The preview lists additions and duplicate skips. Task identity uses stable browser IDs, preserving subtasks and account edits during repeated transfers. Course duplicates are matched by source identity or course/year (high school) and title/term (college). High-school catalog matches keep their catalog references. Custom or unavailable catalog courses become private custom entries in the four-year plan and saved-course picker. College courses enter the term plan. Imported course metadata remains in account exports. College titles must fit the existing 120-character account field; invalid backups fail before writing.

Academic context and study budget changes are separately optional. Account budgets remain limited to 80 hours/week. Historical browser timing is excluded from analytics because older browser data may infer starts at completion. Tracking-off accounts do not receive historical start timestamps or actual minutes. Completion dates, planned schedules, estimates, and task status are retained.

Additive migrations add `planned_courses.imported_details`, `term_courses.imported_details`, and `term_courses.browser_source_key`. Existing rows remain intact.

## Calendar URL import and manual refresh

Tasks → Import or refresh school calendar assignments accepts a direct HTTPS download link or `.ics` file. Users preview up to 200 events / 1 MB, then select changes. New assignments are checked; updates require explicit selection. Updates change only titles and deadlines, preserving estimates and progress. Event UIDs identify repeat imports; duplicate occurrences are skipped. Completed tasks, events missing from the new feed, and account changes made after preview are preserved. Cancelled events are not added. Recurring series still import only explicitly listed occurrences.

To refresh, paste the same link again. URLs are not saved to the account or placed in preview tokens. This is manual import, not an LMS API connection or background subscription. School login pages and redirecting links require the final direct calendar-download URL; file upload remains available.

Network retrieval requires public HTTPS addresses on port 443, rejects credentials, internal/loopback/link-local and transition addresses, and connects to a checked IP while verifying TLS against the original hostname. Redirects and compressed responses are rejected. Reads are bounded by size and timeouts; downloads are rate-limited per account. No network request occurs merely by opening the import page.

## Validation

125 targeted regression tests passed. A final run of 30 tests passed after the validation edge-case additions, including additive migration preservation. These runs overlap. `scripts/check_import_followup.py` passed the real Chrome sign-up/return, local selection, preview/save, unchanged local copy, custom-course visibility, and calendar import/update flows. Tests use disposable accounts/databases and mocked school feeds. No live school calendar or production deployment was accessed.
