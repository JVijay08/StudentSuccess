# StudentSuccess AI Data Dictionary

## Purpose

StudentSuccess AI collects information exclusively for supporting academic planning, task organization, workload and burnout check-ins, course recommendations, and portfolio recommendations.

The project works with two kinds of data:

- **Student-entered local data** saved to SQLite for individual use
- **Synthetic data** generated later for demonstrating machine-learning models

**Important:** This project does not predict real college admissions decisions or provide medical or mental-health advice.

## Student Profile Data

| Field | Example | Source | Used For | Validation |
|-------|---------|--------|----------|------------|
| first_name | "Alex" | User entry | Personalization | Required, text only |
| grade_level | 11 | User entry | Course recommendations, milestone tracking | Integer 9–12 |
| graduation_year | 2027 | Derived from grade_level | Course pathway planning | Integer 2026–2035 |
| current_gpa | 3.75 | User entry | Success prediction, course matching | Float 0.0–5.0 |
| target_gpa | 3.9 | User entry | Goal tracking, workload planning | Float 0.0–5.0 |
| study_hours_per_week | 15 | User entry | Workload estimation, burnout assessment | Integer 0–80 |
| career_interest | "Computer Science" | User entry | Career-aligned course recommendations | Text, optional |
| course_rigor_preference | "Challenging" | User entry | Course difficulty matching | Enum: Balanced, Challenging, or Relaxed |

## Task and Deadline Data

| Field | Example | Source | Used For | Validation |
|-------|---------|--------|----------|------------|
| title | "Complete calculus homework" | User entry | Task organization, deadline tracking | Required, text |
| category | "Homework" | User entry | Task filtering and reporting | Text (e.g., Homework, Project, Exam, Other) |
| priority | "High" | User entry | Task sorting, workload assessment | Enum: High, Medium, Low |
| due_date | "2026-12-15" | User entry | Deadline reminders, burnout estimation | Valid ISO date format |
| estimated_minutes | 120 | User entry | Workload calculation | Integer 0–600 |
| completed | true | User tracking | Progress tracking, burnout metrics | Boolean |
| notes | "Includes limit problems" | User entry | Task context and reference | Text, optional |

## Burnout Check-In Data

| Field | Example | Source | Used For | Validation |
|-------|---------|--------|----------|------------|
| sleep_hours | 7.5 | User entry | Workload-balance estimate | Float 0–24 |
| homework_hours | 3.5 | User entry | Workload-balance estimate | Float 0–24 |
| extracurricular_hours | 5 | User entry | Workload-balance estimate | Float 0–24 |
| stress_rating | 7 | User entry | Workload-balance estimate | Integer 1–10 |
| free_time_rating | 5 | User entry | Workload-balance estimate | Integer 1–10 |
| created_at | "2026-12-01 14:30" | System timestamp | Tracking trends over time | ISO datetime format |

**Important:** Burnout check-in results are educational workload and balance estimates only. They are not medical or mental-health diagnoses and should not be used as a substitute for professional mental-health support.

## Course Catalog Data

| Field | Example | Source | Used For | Validation |
|-------|---------|--------|----------|------------|
| course_name | "AP Calculus BC" | Curated | Course recommendations, pathway planning | Required, text |
| subject | "Mathematics" | Curated | Subject filtering | Text (e.g., Mathematics, Science, English, History, Computer Science) |
| grade_levels | "10, 11, 12" | Curated | Grade-level filtering and prerequisite checking | Comma-separated integers 9–12 |
| prerequisite | "Algebra 2" | Curated | Prerequisite validation and recommendations | Text, optional |
| workload_level | "High" | Curated | Workload planning and student matching | Enum: Low, Medium, High |
| graduation_category | "Math" | Curated | Graduation requirement tracking | Text (e.g., Math, Science, English, Social Studies, Elective) |

This data supports course pathway recommendations and prerequisite validation.

## Portfolio Builder Data

| Field | Example | Source | Used For | Validation |
|-------|---------|--------|----------|------------|
| activity_name | "Science Fair Project" | Curated | Portfolio recommendations | Required, text |
| category | "Research & Exploration" | Curated | Activity categorization and filtering | Text (e.g., Personal Projects, Leadership, Community Service, Competitions, Certifications, Research & Exploration, Skill-Building) |
| time_commitment | "20 hours" | Curated | Student planning and workload estimation | Text (e.g., "5 hours", "10 hours", "20+ hours") |
| related_interests | "STEM, Biology, Public Speaking" | Curated | Interest-based recommendations | Comma-separated tags |
| difficulty | "Intermediate" | Curated | Student capability matching | Enum: Beginner, Intermediate, Advanced |
| description | "Design and present an independent biological research project." | Curated | Activity overview and guidance | Text |

Portfolio Builder recommendations may include personal projects, leadership roles, community service, academic competitions, industry certifications, research and exploration opportunities, and skill-building goals.

**Important:** Portfolio Builder recommendations do not guarantee admission results and do not claim to increase admission probability. They are designed to support thoughtful, interest-aligned activity exploration.

## Synthetic Machine-Learning Training Data

The project will generate synthetic student records later for demonstration-only machine-learning models. These synthetic records will include typical fields for academic performance and burnout prediction, such as:

- current_gpa
- attendance_rate
- study_hours_per_week
- course_rigor
- homework_completion_rate
- extracurricular_hours
- sleep_hours
- stress_rating
- success_outcome
- burnout_risk_level

**Important:** All synthetic data will be documented, reproducible, and created for demonstration purposes only. It is not based on real student records and should not be used to make decisions about real individuals.

## Privacy Rules

The project **does not collect** the following information:

- Passwords outside the authentication system
- Government identification numbers (SSN, state ID, passport number, etc.)
- Home addresses
- Precise location data or GPS coordinates
- Financial account information or payment details
- Medical records or physical health information
- Therapy or diagnosis information
- Real college admissions decisions or outcomes
- Other students' private records without explicit permission

**Guiding principle:**

> Only collect information needed for a visible StudentSuccess feature.
