# Privacy Notes

StudentSuccess is a local academic-planning project. Its guiding rule is simple:

> Collect only information required by a visible, working feature.

## Current local data

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

## Future beta users

Before accepting beta users, add authentication, access controls, a deletion/export path, clear consent language, and a retention policy. Use separate records per user and ensure one student cannot access another student's data. Do not reuse beta data for model training without separate, explicit consent.

## Security basics

Keep secrets out of source control, validate input on the server, minimize logs containing student-entered content, and back up or export local data only with the student's knowledge.

## Deployment persistence

Local development uses SQLite in `instance/studentsuccess.db`. Render
deployments must provide a persistent `DATABASE_URL`, preferably a managed
PostgreSQL database. The Render blueprint disables `DEMO_RESET_ON_DEPLOY`; the
reset remains available only when explicitly enabled for a disposable demo.
