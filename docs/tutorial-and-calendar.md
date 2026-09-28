# Tutorial, repeating tasks, and Google Calendar

The public Start tutorial entry and workspace menu open an isolated sample
account. The guide follows real navigation, allows exercises to be skipped, and
supports back/jump/exit. Existing users return to their original account after
exit; normal session expiry and credential-revocation checks still apply. Exiting
deletes the sample account and its data. Abandoned practice accounts use the
existing stale-demo cleanup. Core guide navigation also works without JavaScript.
The legacy `/demo` route remains for compatibility; public entry points use the
CSRF-protected tutorial route.

New task creation interprets the date as the inclusive repeat-through date when
a frequency is selected. The start defaults to today in the planner timezone;
the due time defaults to 23:59. Occurrences preserve local wall-clock time across
daylight-saving changes, are created atomically, and can be edited/completed
individually. A maximum of 366 occurrences prevents accidental enormous batches.
These finite schedules create no automatic prep tasks and do not spawn new work
after completion. No schema addition is required. Existing open-ended recurring
tasks retain their previous behavior rather than silently changing saved plans.

Google Calendar integration is one-way: the student reviews and saves a prefilled
one-minute deadline marker. Titles/times are shared with Google only when the
student follows that link. No OAuth tokens or Google account information are
collected. Bulk ICS export includes active deadlines, uses stable event IDs, escapes
text, folds UTF-8 lines, and marks events transparent. Both flows explain manual
updates and possible duplicate copies; neither claims automatic synchronization.

Implementation follows Google's [prefilled event-link documentation](https://developers.google.com/workspace/calendar/api/concepts/inviting-attendees-to-events#provide_a_link_for_users_to_add_the_event)
and [calendar import instructions](https://support.google.com/calendar/answer/37118).

Validation: `tests/test_tutorial.py`, `tests/test_task_creation_calendar.py`,
`scripts/check_tutorial.py`, and `scripts/check_task_creation_calendar.py` cover
isolation/restoration/deletion, revoked sessions, inclusive recurrence bounds,
end-date stopping, timezone/DST behavior, atomic validation failures, link
encoding, export permissions, UTF-8 folding, keyboard use, and mobile layouts.
