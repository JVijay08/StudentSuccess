# Privacy Notes

StudentSuccess is a local academic-planning project. Its guiding rule is simple:

> Collect only information required by a visible, working feature.

## Current local data

### Private-code accounts (default public entry point)

New visitors create a server-stored planner without a name, email, or chosen
password. A private access code contains 32 cryptographically random bytes;
only its SHA-256 digest is stored in the new `access_credentials` table. Codes
are sent in POST bodies, never URLs, and are shown once in a no-store response.
They are not retained in the session cookie or browser storage by the app.
The user can copy or download the code and must keep that copy private.

Possession of the code grants full account access. A lost code cannot be
recovered. Replacement requires the current code and invalidates the previous
code and other sessions. Deletion also requires the code. The code is an access
credential, not encryption or a promise of anonymity. Hosting still receives
ordinary request metadata. Use fictional information only.

Code accounts skip personal-profile onboarding. Existing planner services use
explicit sample defaults (year 9, 10 weekly study hours, Balanced rigor).
Compatibility profile fields use "Planner", a placeholder graduation year, and
zero GPA values; these are not collected or inferred personal details. Only
planning year and weekly study budget are exposed in the preferences form.

The first-visit welcome dialog explains the prototype, code handling, server
storage, and fictional demo. Dismissal is remembered in localStorage under
`studentsuccess.welcome.v1`; the explanation can be reopened. It is not a formal
consent mechanism. Existing username/password accounts remain usable.

### Non-personal entry confirmation

Task creation/editing, legacy profile editing, and free-text catalog searches
require an explicit non-personal-information acknowledgment on every submission.
The acknowledgment starts unchecked and resets when relevant entries change.
The server rejects unconfirmed task/profile saves and does not apply unconfirmed
search text. Catalog searches use POST so new searches do not put text in URLs.
The warning identifies real names, school names, contact details, student IDs,
and other identifying details as information to remove. This is a user
confirmation, not automatic detection or a guarantee that text is non-personal.
Authentication fields and structured catalog selections are not subject to the
free-text acknowledgment.

### Optional browser-only workspace

The browser-only planner is offered beneath private-code creation, not in the
private-code dashboard. It keeps the existing `studentsuccess.local-plan.v1`
storage key and reads old backups. Tasks, task ratings, four-year course plans,
and weekly availability stay in browser storage; export/import and erase remain
available. Anyone using the same browser profile can access the plan.

The browser workspace uses the dashboard visual design with local task history,
completion and start-delay summaries, catalog browsing, comparisons, and a
four-year plan. A single unauthenticated public catalog-bundle request downloads
reference data. Searches and course selections then run locally; none are sent
back to the server. Server accounts retain their existing advanced features
including recurring tasks, reminders, calendar export, and account preferences.
Browser plans are separate and do not automatically sync to private-code accounts.

The same non-personal text confirmation is required in browser task/custom-course
forms and searches. Backup restoration also asks the user to confirm the file
contains no personal information. This is acknowledgment, not automated detection.

### Account and demo workspaces

The SQLite database may contain a student's first name, grade, graduation year, GPA goals, weekly study-time estimate, career interest, and course-rigor preference. The task planner also stores assignment details and planned-versus-actual start times.

The development database is stored locally in `instance/studentsuccess.db` and is ignored by Git. It should not be shared or committed.

## Data minimization

Task behavior can reveal habits and routines. Store only what is needed to help the student plan:

- Avoid detailed location, device, browsing, or surveillance data.
- Do not collect medical, diagnostic, therapy, financial, government-ID, or unrelated school-record data.
- Do not collect information about other students.
- Do not retain speculative prediction fields.
- Explain every score using understandable rules and the student's own task data.

StudentSuccess is not a medical service, admissions predictor, or monitoring tool.

## Public prototype users

Authentication and per-user access controls isolate student workspaces. Users
can export their profile, tasks, and course plan; clear completed-task history;
or delete their account and associated records from Settings. A documented
retention policy and formal consent language are still required before the
prototype should accept real student information. Do not reuse prototype data
for model training without separate, explicit consent.

## Security basics

Keep secrets out of source control, validate input on the server, minimize logs containing student-entered content, and back up or export local data only with the student's knowledge.

## Deployment persistence

Local development uses SQLite in `instance/studentsuccess.db`. Render
deployments must provide a persistent `DATABASE_URL`, preferably a managed
PostgreSQL database. The Render blueprint disables `DEMO_RESET_ON_DEPLOY`; the
reset remains available only when explicitly enabled for a disposable demo.
