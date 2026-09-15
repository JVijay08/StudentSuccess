from datetime import datetime, timedelta, timezone

from extensions import db
from models import PlannedCourse, StudentProfile, Task


def add_profile(user_id):
    """Create a StudentProfile owned by the given user.

    Must be called inside an app context. ``user_id`` scopes the profile to the
    authenticated fixture user under the multi-user isolation design.
    """
    profile = StudentProfile(
        first_name="Alex",
        grade=11,
        graduation_year=2027,
        current_gpa=3.7,
        target_gpa=3.9,
        study_hours_per_week=12,
        user_id=user_id,
    )
    db.session.add(profile)
    db.session.commit()
    return profile


def make_completed_task(
    profile_id,
    title,
    completed_at,
    *,
    subject=None,
    task_type=None,
    planned_start_at=None,
    started_at=None,
    due_at=None,
):
    """Insert a completed Task row directly for dashboard history tests."""
    if due_at is None:
        due_at = completed_at
    task = Task(
        student_profile_id=profile_id,
        title=title,
        subject=subject,
        task_type=task_type,
        due_at=due_at,
        estimated_minutes=60,
        difficulty="medium",
        interest_level="medium",
        status="completed",
        planned_start_at=planned_start_at,
        started_at=started_at,
        completed_at=completed_at,
    )
    db.session.add(task)
    return task


def test_start_history_limited_to_ten_newest_first(app, authed_client):
    base = datetime(2027, 1, 1, 12, tzinfo=timezone.utc)
    with app.app_context():
        profile = add_profile(authed_client.user_id)
        # 12 completed tasks with strictly increasing completed_at.
        for index in range(12):
            completed_at = base + timedelta(days=index)
            make_completed_task(
                profile.id,
                f"Task {index}",
                completed_at,
                subject="Math",
                planned_start_at=completed_at - timedelta(hours=2),
                started_at=completed_at - timedelta(hours=1),
            )
        db.session.commit()

    response = authed_client.get("/dashboard")
    assert response.status_code == 200
    body = response.data.decode()

    # At most 10 rows: the two oldest tasks (0 and 1) must be excluded.
    assert "Task 11" in body
    assert "Task 2 <" in body
    assert "Task 0 <" not in body
    assert "Task 1 <" not in body  # trailing " <" avoids matching "Task 11 <"

    # Newest first: Task 11 appears before Task 2 in the rendered page.
    assert body.index("Task 11") < body.index("Task 2 <")


def test_start_history_group_label_and_delay_display(app, authed_client):
    base = datetime(2027, 3, 1, 12, tzinfo=timezone.utc)
    with app.app_context():
        profile = add_profile(authed_client.user_id)

        # Subject wins as the group label; started 2 hours late.
        make_completed_task(
            profile.id,
            "Late math essay",
            base + timedelta(days=2),
            subject="Math",
            planned_start_at=base,
            started_at=base + timedelta(hours=2),
        )
        # No subject -> falls back to task_type; missing start data.
        make_completed_task(
            profile.id,
            "Typed reading",
            base + timedelta(days=1),
            task_type="Reading",
            planned_start_at=None,
            started_at=None,
        )
        db.session.commit()

    response = authed_client.get("/dashboard")
    body = response.data.decode()

    assert "Late math essay" in body
    assert "(Math)" in body
    assert "2.0 hr late" in body

    assert "Typed reading" in body
    assert "(Reading)" in body
    assert "no start data" in body


def test_start_history_empty_state(app, authed_client):
    with app.app_context():
        add_profile(authed_client.user_id)

    response = authed_client.get("/dashboard")
    assert response.status_code == 200
    assert b"RECENT START HISTORY" not in response.data

from models import User
from services.auth_service import hash_password


def make_overdue_task(
    profile_id,
    title,
    *,
    planned_start_at,
    due_at=None,
    subject=None,
    task_type=None,
):
    """Insert an unstarted, not-completed Task planned in the past.

    Used to exercise the OVERDUE TO START dashboard card. ``planned_start_at``
    should be a timezone-aware UTC datetime in the past.
    """
    if due_at is None:
        due_at = planned_start_at + timedelta(hours=3)
    task = Task(
        student_profile_id=profile_id,
        title=title,
        subject=subject,
        task_type=task_type,
        due_at=due_at,
        estimated_minutes=60,
        difficulty="medium",
        interest_level="medium",
        status="not_started",
        planned_start_at=planned_start_at,
        started_at=None,
    )
    db.session.add(task)
    return task


def test_dashboard_shows_overdue_to_start_task(app, authed_client):
    now = datetime.now(timezone.utc)
    with app.app_context():
        profile = add_profile(authed_client.user_id)
        make_overdue_task(
            profile.id,
            "Overdue lab report",
            planned_start_at=now - timedelta(hours=3),
            subject="Chemistry",
        )
        db.session.commit()

    response = authed_client.get("/dashboard")
    assert response.status_code == 200
    body = response.data.decode()

    assert "OVERDUE TO START" in body
    assert "Overdue lab report" in body
    assert "(Chemistry)" in body
    assert "planned" in body and "ago" in body
    assert "Start now" in body
    assert "New planned start" in body


def test_dashboard_overdue_empty_state(app, authed_client):
    with app.app_context():
        add_profile(authed_client.user_id)

    response = authed_client.get("/dashboard")
    assert response.status_code == 200
    assert b"Nothing overdue to start." in response.data


def test_dashboard_connects_current_course_load_to_task_planning(
    app, authed_client
):
    with app.app_context():
        profile = add_profile(authed_client.user_id)
        for course_id in (
            "NATIONAL_AP_ENGLISH_LANGUAGE",
            "MATH_AP_CALC_AB",
            "MATH_AP_STATISTICS",
        ):
            db.session.add(
                PlannedCourse(
                    student_profile_id=profile.id,
                    catalog_id="national",
                    course_id=course_id,
                    school_year=11,
                    term="Full year",
                    status="planned",
                )
            )
        db.session.commit()

    response = authed_client.get("/dashboard")
    body = response.data.decode()

    assert response.status_code == 200
    assert "CURRENT COURSE LOAD" in body
    assert "Moderate estimate" in body
    assert "3 planned courses" in body
    assert "3 high-workload courses" in body
    assert "consistent weekly task planning" in body


def test_dashboard_overdue_scoped_to_current_user(app, authed_client):
    now = datetime.now(timezone.utc)
    with app.app_context():
        profile = add_profile(authed_client.user_id)
        make_overdue_task(
            profile.id,
            "Mine overdue",
            planned_start_at=now - timedelta(hours=2),
            subject="Math",
        )

        # A second user with their own overdue task must NOT appear.
        other_user = User(
            username="other", password_hash=hash_password("password123")
        )
        db.session.add(other_user)
        db.session.commit()
        other_profile = StudentProfile(
            first_name="Sam",
            grade=12,
            graduation_year=2026,
            current_gpa=3.0,
            target_gpa=3.5,
            study_hours_per_week=8,
            user_id=other_user.id,
        )
        db.session.add(other_profile)
        db.session.commit()
        make_overdue_task(
            other_profile.id,
            "Theirs overdue",
            planned_start_at=now - timedelta(hours=5),
            subject="History",
        )
        db.session.commit()

    response = authed_client.get("/dashboard")
    body = response.data.decode()

    assert "Mine overdue" in body
    assert "Theirs overdue" not in body


def test_dashboard_unauthenticated_redirects_to_login(app):
    client = app.test_client()
    response = client.get("/dashboard")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    assert b"OVERDUE TO START" not in response.data


def make_measurable_task(
    profile_id,
    title,
    *,
    subject=None,
    task_type=None,
    estimated_minutes,
    actual_minutes,
    completed_at,
):
    """Insert a completed Task with a deterministic actual duration.

    ``actual_minutes`` is the elapsed time between ``started_at`` and
    ``completed_at``; combined with ``estimated_minutes`` this fixes the
    per-task burn rate (actual / estimated). Timestamps are timezone-aware UTC.
    """
    started_at = completed_at - timedelta(minutes=actual_minutes)
    task = Task(
        student_profile_id=profile_id,
        title=title,
        subject=subject,
        task_type=task_type,
        due_at=completed_at,
        estimated_minutes=estimated_minutes,
        difficulty="medium",
        interest_level="medium",
        status="completed",
        planned_start_at=None,
        started_at=started_at,
        completed_at=completed_at,
    )
    db.session.add(task)
    return task


def test_dashboard_estimate_accuracy_card_qualifying_history(app, authed_client):
    base = datetime(2027, 5, 1, 12, tzinfo=timezone.utc)
    with app.app_context():
        profile = add_profile(authed_client.user_id)

        # Chemistry: rates 2.0 (120/60) and 1.5 (90/60) -> mean 1.75 (over).
        make_measurable_task(
            profile.id,
            "Chem lab A",
            subject="Chemistry",
            estimated_minutes=60,
            actual_minutes=120,
            completed_at=base + timedelta(days=1),
        )
        make_measurable_task(
            profile.id,
            "Chem lab B",
            subject="Chemistry",
            estimated_minutes=60,
            actual_minutes=90,
            completed_at=base + timedelta(days=2),
        )
        # Reading: rates 0.5 (30/60) and 0.5 (30/60) -> mean 0.5 (early).
        make_measurable_task(
            profile.id,
            "Reading A",
            subject="Reading",
            estimated_minutes=60,
            actual_minutes=30,
            completed_at=base + timedelta(days=3),
        )
        make_measurable_task(
            profile.id,
            "Reading B",
            subject="Reading",
            estimated_minutes=60,
            actual_minutes=30,
            completed_at=base + timedelta(days=4),
        )
        db.session.commit()

    response = authed_client.get("/dashboard")
    assert response.status_code == 200
    body = response.data.decode()

    assert "ESTIMATE ACCURACY" in body
    # Overall line present with a plain-language label.
    assert "Overall:" in body
    assert "runs ~" in body

    # Both qualifying groups appear.
    assert "Chemistry" in body
    assert "Reading" in body

    # Ordered rate DESC: the over-estimate group (Chemistry) precedes the
    # lower-rate group (Reading).
    assert body.index("Chemistry") < body.index("Reading")


def test_dashboard_estimate_accuracy_scoped_to_current_user(app, authed_client):
    base = datetime(2027, 6, 1, 12, tzinfo=timezone.utc)
    with app.app_context():
        profile = add_profile(authed_client.user_id)
        make_measurable_task(
            profile.id,
            "Mine chem A",
            subject="Chemistry",
            estimated_minutes=60,
            actual_minutes=120,
            completed_at=base + timedelta(days=1),
        )
        make_measurable_task(
            profile.id,
            "Mine chem B",
            subject="Chemistry",
            estimated_minutes=60,
            actual_minutes=90,
            completed_at=base + timedelta(days=2),
        )

        # A second user whose group must NOT appear on this user's dashboard.
        other_user = User(
            username="other2", password_hash=hash_password("password123")
        )
        db.session.add(other_user)
        db.session.commit()
        other_profile = StudentProfile(
            first_name="Sam",
            grade=12,
            graduation_year=2026,
            current_gpa=3.0,
            target_gpa=3.5,
            study_hours_per_week=8,
            user_id=other_user.id,
        )
        db.session.add(other_profile)
        db.session.commit()
        make_measurable_task(
            other_profile.id,
            "Theirs bio A",
            subject="Biology",
            estimated_minutes=60,
            actual_minutes=120,
            completed_at=base + timedelta(days=1),
        )
        make_measurable_task(
            other_profile.id,
            "Theirs bio B",
            subject="Biology",
            estimated_minutes=60,
            actual_minutes=90,
            completed_at=base + timedelta(days=2),
        )
        db.session.commit()

    response = authed_client.get("/dashboard")
    body = response.data.decode()

    assert "Chemistry" in body
    assert "Biology" not in body


def test_dashboard_estimate_accuracy_insufficient_history(app, authed_client):
    base = datetime(2027, 7, 1, 12, tzinfo=timezone.utc)
    with app.app_context():
        profile = add_profile(authed_client.user_id)
        # Only one measurable task -> below MINIMUM_SAMPLE, empty state.
        make_measurable_task(
            profile.id,
            "Lone task",
            subject="Chemistry",
            estimated_minutes=60,
            actual_minutes=120,
            completed_at=base + timedelta(days=1),
        )
        db.session.commit()

    response = authed_client.get("/dashboard")
    assert response.status_code == 200
    body = response.data.decode()

    assert "ESTIMATE ACCURACY" not in body


def test_dashboard_estimate_accuracy_unauthenticated_redirects(app):
    client = app.test_client()
    response = client.get("/dashboard")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    assert b"ESTIMATE ACCURACY" not in response.data
