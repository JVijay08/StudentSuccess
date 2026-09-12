# Data Dictionary

StudentSuccess stores only data required by working planning features. Local student data lives in SQLite; the curated course catalog lives in JSON.

## StudentProfile (implemented)

Database table: `student_profiles`

| Field | Type | Required | Purpose |
|---|---|---:|---|
| id | Integer | Yes | Primary key |
| first_name | String(100) | Yes | Dashboard greeting and profile identification |
| grade | Integer | Yes | Current grade, validated from 9 through 12 |
| graduation_year | Integer | Yes | Planning context, validated from 2026 through 2035 |
| current_gpa | Float | Yes | Current academic context, from 0 through 5 |
| target_gpa | Float | Yes | Student goal, from 0 through 5 |
| study_hours_per_week | Float | Yes | Available weekly study context, from 0 through 80 |
| career_goals | String(120) | No | Optional career interest |
| course_rigor | String(60) | No | Optional rigor preference |
| created_at | DateTime | Yes | UTC creation time |
| updated_at | DateTime | Yes | UTC last-update time |

The onboarding form uses `career_interest` as its request key and maps it to the model's `career_goals` field.

## Course catalog (implemented)

File: `data/courses.json`

Each course record contains:

- `course_id`: unique stable identifier
- `course_name`: display name
- `subject`: subject used for filtering
- `course_type`: Standard, AP, or IB
- `grade_levels`: planning-appropriate grade numbers
- `rigor_level`: catalog planning label
- `workload_level`: project-created planning estimate
- `prerequisites`: prerequisite course names or eligibility notes
- `graduation_category`: graduation-area label
- `career_clusters`: optional related career categories

The current catalog has 59 records. It is curated reference data, not student behavior data.

## Task behavior (planned next)

The next model should record a task's title, subject, type, deadline, estimated minutes, difficulty, interest level, status, planned start, actual start, completion time, and timestamps. It should reference `student_profiles.id`.

These fields are planned until a working task route and tests are added. No prediction output, health data, or opaque scoring should be stored.

## Future behavioral history

Planned-versus-actual start times can later support personal summaries such as typical delay windows by subject or task type. Collection should begin only through a visible task feature, remain minimal, and use transparent calculations before any machine-learning work is considered.
