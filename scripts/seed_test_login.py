"""
scripts/seed_test_login.py
---------------------------
Create (or reset) a TEST LOGIN account with realistic seed data so the
dashboard's features can be explored with populated cards:

  - Estimate accuracy (burn rate): completed tasks with actual-vs-estimated time
  - Start-delay summary + recent start history: planned-vs-actual start times
  - Overdue-to-start nudge: an active task whose planned start is in the past
  - Recurring session + linked prep task: a weekly commitment
  - Priority list: a spread of active tasks with varied deadlines/difficulty

Login after running:
    username: testuser
    password: testpass123

Safety
~~~~~~
- Idempotent: if a user named "testuser" already exists, it is deleted first
  (cascade removes its profile and tasks) and recreated fresh. No OTHER user's
  data is touched.
- Operates on whatever database the app is configured to use (instance/
  studentsuccess.db by default). It only adds/removes the single test account.

Usage
~~~~~
    python scripts/seed_test_login.py
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from extensions import db
from models import StudentProfile, Task, User
from services.auth_service import hash_password

TEST_USERNAME = "testuser"
TEST_PASSWORD = "testpass123"


def _add_task(profile_id, **kwargs):
    task = Task(student_profile_id=profile_id, **kwargs)
    db.session.add(task)
    return task


def run_seed():
    app = create_app()
    with app.app_context():
        db.create_all()

        # Idempotent: remove any prior test user (cascades to profile + tasks).
        existing = User.query.filter_by(username=TEST_USERNAME).first()
        if existing is not None:
            db.session.delete(existing)
            db.session.commit()
            print(f"[seed] Removed existing '{TEST_USERNAME}' and its data.")

        user = User(
            username=TEST_USERNAME,
            password_hash=hash_password(TEST_PASSWORD),
        )
        db.session.add(user)
        db.session.commit()

        profile = StudentProfile(
            user_id=user.id,
            first_name="Jayesh",
            grade=11,
            graduation_year=2027,
            current_gpa=4.1,
            target_gpa=4.5,
            study_hours_per_week=15,
            career_goals="Engineering",
            course_rigor="Challenging",
        )
        db.session.add(profile)
        db.session.commit()
        pid = profile.id

        now = datetime.now(timezone.utc)

        # --- Completed tasks: estimate accuracy + start-delay + history ------
        # Math tutoring/homework: consistently runs OVER estimate, starts late.
        for i, (est, actual, delay_h) in enumerate(
            [(60, 90, 3), (60, 84, 2), (45, 63, 4)]
        ):
            done = now - timedelta(days=10 + i)
            planned = done - timedelta(hours=actual / 60 + delay_h)
            started = planned + timedelta(hours=delay_h)
            _add_task(
                pid,
                title=f"SAT Math problem set {i + 1}",
                subject="Math",
                task_type="Tutoring prep",
                due_at=done + timedelta(hours=2),
                estimated_minutes=est,
                difficulty="high",
                interest_level="high",
                status="completed",
                planned_start_at=planned,
                started_at=started,
                completed_at=started + timedelta(minutes=actual),
            )

        # Tamil TA lesson prep: finishes EARLY, starts roughly on time.
        for i, (est, actual) in enumerate([(60, 42), (60, 45)]):
            done = now - timedelta(days=7 + i)
            planned = done - timedelta(hours=actual / 60 + 0.2)
            started = planned + timedelta(minutes=10)
            _add_task(
                pid,
                title=f"Tamil school lesson plan {i + 1}",
                subject="Tamil",
                task_type="Lesson prep",
                due_at=done + timedelta(hours=1),
                estimated_minutes=est,
                difficulty="low",
                interest_level="high",
                status="completed",
                planned_start_at=planned,
                started_at=started,
                completed_at=started + timedelta(minutes=actual),
            )

        # English essay: about on time / accurate estimate.
        done = now - timedelta(days=5)
        planned = done - timedelta(hours=2)
        _add_task(
            pid,
            title="English essay draft",
            subject="English",
            task_type="Homework",
            due_at=done + timedelta(hours=3),
            estimated_minutes=90,
            difficulty="medium",
            interest_level="medium",
            status="completed",
            planned_start_at=planned,
            started_at=planned + timedelta(minutes=20),
            completed_at=planned + timedelta(minutes=20 + 92),
        )

        # --- Overdue to start: planned start in the past, not started -------
        _add_task(
            pid,
            title="Physics lab write-up",
            subject="Physics",
            task_type="Homework",
            due_at=now + timedelta(days=1, hours=6),
            estimated_minutes=75,
            difficulty="high",
            interest_level="low",
            status="not_started",
            planned_start_at=now - timedelta(hours=4),
        )

        # --- Active tasks for the priority list -----------------------------
        _add_task(
            pid,
            title="Calculus homework ch. 5",
            subject="Math",
            task_type="Homework",
            due_at=now + timedelta(hours=20),
            estimated_minutes=120,
            difficulty="high",
            interest_level="medium",
            status="not_started",
            planned_start_at=now + timedelta(hours=2),
        )
        _add_task(
            pid,
            title="Read history chapter",
            subject="History",
            task_type="Reading",
            due_at=now + timedelta(days=4),
            estimated_minutes=40,
            difficulty="low",
            interest_level="low",
            status="in_progress",
            planned_start_at=now - timedelta(hours=1),
            started_at=now - timedelta(minutes=30),
        )

        # --- Recurring weekly session + linked prep task --------------------
        session = _add_task(
            pid,
            title="SAT Math tutoring session (Schoolhouse)",
            subject="Math",
            task_type="Tutoring session",
            due_at=now + timedelta(days=3, hours=18),
            estimated_minutes=60,
            difficulty="medium",
            interest_level="high",
            status="not_started",
            planned_start_at=now + timedelta(days=3, hours=17),
            recurrence_rule="weekly",
        )
        db.session.commit()  # get session.id
        _add_task(
            pid,
            title="Prep: SAT Math tutoring session (Schoolhouse)",
            subject="Math",
            task_type="Lesson prep",
            due_at=session.due_at - timedelta(hours=24),
            estimated_minutes=30,
            difficulty="medium",
            interest_level="high",
            status="not_started",
            prep_for_id=session.id,
        )

        db.session.commit()

        total = Task.query.filter_by(student_profile_id=pid).count()
        print(
            f"[seed] Created '{TEST_USERNAME}' (password '{TEST_PASSWORD}') "
            f"with profile '{profile.first_name}' and {total} tasks."
        )
        print("[seed] Log in at /login to explore the populated dashboard.")


if __name__ == "__main__":
    run_seed()
