# Survey follow-up implementation — October 27, 2026

The next two items are now covered by [browser transfer and incoming calendars](import-followup-2026-10-27.md).

Implements the four prioritized changes from the survey audit for the account workspace. Browser-to-account transfer, incoming school calendar feeds, and native apps remain outside this change. The separate browser-local `/planner` workspace is unchanged.

- Recommendations show their short reason directly on the dashboard card. Scoring details render each factor once.
- Completing a task without starting it leaves its actual start unknown. Explicitly recorded work minutes still contribute to duration statistics without requiring a fabricated start.
- Settings → Task planning → Start and duration tracking can be turned off. Task status and completion dates still work; planned starts remain scheduling inputs. While off, start timestamps and submitted work minutes are not collected, timing views and time-entry controls are hidden, and history bonuses and delay-based warnings are disabled. Existing history is preserved. Tasks started or completed while off are excluded from future timing calculations, even after re-enabling tracking.
- Today's tasks lists unfinished leaf tasks due or planned on the account's local date. Passed deadlines appear once in Overdue, including deadlines earlier today; future-only tasks and completed work are excluded. The recommended next task remains independent of this date filter. Start and Complete actions return to the dashboard.

Additive startup migrations introduce `user_settings.time_tracking_enabled` (default true) and `tasks.timing_excluded` (default false). The export includes both. Existing inferred historical start times are not rewritten: older records do not reliably identify whether a start was observed or inferred.

Validation covers direct completion, explicit minutes without a start, preference persistence and server enforcement, re-enabling tracking, history-free ranking, timezone boundaries, daily-list deduplication, project progress, and additive migration preservation. Browser checks exercise desktop/mobile layout, visible reasons, daily selection, and starting/completing with tracking off using disposable data. See `tests/test_survey_followup.py` and `scripts/check_survey_followup.py`.
