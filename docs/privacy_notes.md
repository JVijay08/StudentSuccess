# Privacy Notes

StudentSuccess is an academic-planning prototype with a hosted demo and an optional browser-only workspace. Its guiding rule is simple:

> Collect only information required by a visible, working feature.

## Current data handling

### Username/password accounts

Create a server-stored planner with a nickname-style username and a password of
15?128 characters. No email address, full name, or student ID is requested.
Werkzeug hashes passwords; plaintext passwords are not stored in the database,
session, or browser storage by the app. Save credentials in a password manager.
There is no email-based recovery or security-question fallback.

New accounts must complete planning preferences: education context, study budget,
timezone, task defaults, and display choices. College program/term and credit target
are optional. The server enforces completion across all workspace routes and new
sessions. Compatibility profile fields use "Planner", a placeholder graduation year,
and zero GPA values. Previously saved profile values are preserved, not newly collected.

Old code and email login routes are removed. A separate one-time transfer requires
an existing private code plus new credentials; it preserves the user ID and planner,
deletes the old code digest, and invalidates other sessions. No new codes are issued.
Retired email request tables remain for migration/deletion safety, with no active mail flow.

The privacy dialog remains available on demand. Dismissing it is not a substitute
for onboarding or a formal consent mechanism. Hosting still receives ordinary
request metadata; nickname accounts do not promise anonymity or encrypted storage.

### Entry confirmation

Task creation/editing, planning preference editing, and free-text catalog searches
require an acknowledgment that personal identifiers and sensitive details are excluded
on every submission. Actual course names, institution selections, assignments, deadlines,
and everyday tasks are allowed.
The acknowledgment starts unchecked and resets when relevant entries change.
The server rejects unconfirmed task/preference saves and does not apply unconfirmed
search text. Catalog searches use POST so new searches do not put text in URLs.
The guidance identifies full names, student IDs, contact details, home addresses,
passwords, and private records as information to remove. Public institution and course
names are allowed. This is a user confirmation, not automatic detection or redaction.
Authentication fields and structured catalog selections are not subject to the
free-text acknowledgment.

The college directory searches public institution names and cities using GET filters,
so those public search terms can appear in browser history and ordinary hosting logs.
Do not enter personal information in directory search. Optional institution selections
are stored as public IPEDS IDs for planning, not as a verified attendance claim.
College-course forms allow public catalog details and URLs while requiring acknowledgment
that personal identifiers and sensitive details are excluded. These student-entered details are
included in account export/deletion and are separate from the public institution dataset.

### Optional browser-only workspace

The separate browser-only planner remains at `/planner`. It keeps the existing `studentsuccess.local-plan.v1`
storage key and reads old backups. Tasks, task ratings, four-year course plans,
and weekly availability stay in browser storage; export/import and erase remain
available. Anyone using the same browser profile can access the plan.

The browser workspace uses the dashboard visual design with local task history,
completion and start-delay summaries, catalog browsing, comparisons, and a
four-year plan. A single unauthenticated public catalog-bundle request downloads
reference data. Searches and course selections then run locally; none are sent
back to the server. Server accounts retain their existing advanced features
including recurring tasks, reminders, calendar export, and account preferences.
Browser plans are separate and do not automatically sync to server accounts.

The same entry confirmation is required in browser task/custom-course
forms and searches. Backup restoration also asks the user to confirm the file
excludes personal identifiers and sensitive details. This is acknowledgment, not automated detection.

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
or delete their account and associated records from Settings. Actual course/task
planning is supported; sensitive records and personal identifiers are outside the
intended use. This wording change does not alter storage, authentication, or access
controls. Retention documentation and ongoing privacy/security reviews remain
operational work. Do not reuse student plans for model training without separate,
explicit consent.

## Security basics

Keep secrets out of source control, validate input on the server, minimize logs containing student-entered content, and back up or export local data only with the student's knowledge.

## Deployment persistence

Local development uses SQLite in `instance/studentsuccess.db`. Render
deployments must provide a persistent `DATABASE_URL`, preferably a managed
PostgreSQL database. The Render blueprint disables `DEMO_RESET_ON_DEPLOY`; the
reset remains available only when explicitly enabled for a disposable demo.
