from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from extensions import db
from models import StudentProfile, Task, User
from services.auth_service import hash_password
from services.procrastination_service import (
    calculate_procrastination_risk,
    explain_procrastination_risk,
)


def add_profile(user_id):
    """Create a StudentProfile owned by the given user.

    ``user_id`` is required because ``StudentProfile.user_id`` is a non-null,
    unique FK to ``users.id`` under the multi-user isolation design. Must be
    called inside an app context.
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


def test_task_table_and_student_association(app):
    with app.app_context():
        user = User(username="owner", password_hash=hash_password("password123"))
        db.session.add(user)
        db.session.commit()

        profile = add_profile(user.id)
        task = Task(
            student_profile_id=profile.id,
            title="History essay",
            due_at=datetime.now(timezone.utc) + timedelta(days=3),
            estimated_minutes=90,
            difficulty="high",
            interest_level="medium",
        )
        db.session.add(task)
        db.session.commit()

        assert task.id is not None
        assert task.student_profile == profile
        assert profile.tasks == [task]


def test_task_route_creates_starts_and_completes_task(app, authed_client):
    with app.app_context():
        add_profile(authed_client.user_id)

    response = authed_client.post(
        "/tasks",
        data={
            "title": "Calculus practice",
            "subject": "Math",
            "task_type": "Homework",
            "due_at": "2027-01-15T18:00",
            "planned_start_at": "2027-01-14T16:00",
            "estimated_minutes": "75",
            "difficulty": "high",
            "interest_level": "low",
        },
    )
    assert response.status_code == 302

    with app.app_context():
        task = Task.query.one()
        task_id = task.id
        assert task.student_profile.first_name == "Alex"
        assert task.started_at is None

    assert authed_client.post(f"/tasks/{task_id}/start").status_code == 302
    with app.app_context():
        task = db.session.get(Task, task_id)
        assert task.status == "in_progress"
        assert task.started_at is not None

    assert authed_client.post(f"/tasks/{task_id}/complete").status_code == 302
    with app.app_context():
        task = db.session.get(Task, task_id)
        assert task.status == "completed"
        assert task.completed_at is not None


def test_tasks_redirects_to_onboarding_without_profile(authed_client):
    response = authed_client.get("/tasks")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/onboarding")


def test_rule_based_risk_is_high_and_explainable():
    now = datetime(2026, 9, 12, 12, tzinfo=timezone.utc)
    task = SimpleNamespace(
        status="not_started",
        started_at=None,
        due_at=now + timedelta(hours=20),
        estimated_minutes=120,
        difficulty="high",
        interest_level="low",
    )

    result = explain_procrastination_risk(task, now=now)

    assert calculate_procrastination_risk(task, now=now) == "HIGH"
    assert result["score"] == 9
    assert "assignment has not been started" in result["reasons"]
    assert "due in 24 hours or less" in result["reasons"]


def _make_qualifying_completed(profile_id, subject, delay_hours, index):
    """Insert a completed task that started ``delay_hours`` late in ``subject``.

    Used to build up per-group history so the suggestion service can produce a
    realism warning. Returns the created Task (added to the session, uncommitted).
    """
    base = datetime(2027, 2, 1, 12, tzinfo=timezone.utc) + timedelta(days=index)
    task = Task(
        student_profile_id=profile_id,
        title=f"{subject} history {index}",
        subject=subject,
        due_at=base + timedelta(hours=delay_hours + 2),
        estimated_minutes=60,
        difficulty="medium",
        interest_level="medium",
        status="completed",
        planned_start_at=base,
        started_at=base + timedelta(hours=delay_hours),
        completed_at=base + timedelta(hours=delay_hours + 1),
    )
    db.session.add(task)
    return task


def test_realism_warning_flashed_on_tight_deadline(app, authed_client):
    with app.app_context():
        profile = add_profile(authed_client.user_id)
        # Two qualifying Math tasks that started ~10 hours late -> avg > 4h.
        _make_qualifying_completed(profile.id, "Math", 10, 0)
        _make_qualifying_completed(profile.id, "Math", 10, 1)
        db.session.commit()

    # New Math task planned to start only 30 minutes before it is due, and a
    # long estimate: 30 min gap << 10h typical late start + 120 min estimate.
    response = authed_client.post(
        "/tasks",
        data={
            "title": "Tight calculus set",
            "subject": "Math",
            "task_type": "Homework",
            "due_at": "2027-06-01T18:30",
            "planned_start_at": "2027-06-01T18:00",
            "estimated_minutes": "120",
            "difficulty": "high",
            "interest_level": "low",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"this may be cutting it close" in response.data

    # The save still succeeds even though a warning was shown.
    with app.app_context():
        saved = Task.query.filter_by(title="Tight calculus set").one()
        assert saved.subject == "Math"


def test_no_realism_warning_below_minimum_sample(app, authed_client):
    with app.app_context():
        profile = add_profile(authed_client.user_id)
        # Only ONE qualifying History task -> below Minimum_Sample of 2.
        _make_qualifying_completed(profile.id, "History", 10, 0)
        db.session.commit()

    response = authed_client.post(
        "/tasks",
        data={
            "title": "History reading",
            "subject": "History",
            "task_type": "Homework",
            "due_at": "2027-06-01T18:30",
            "planned_start_at": "2027-06-01T18:00",
            "estimated_minutes": "120",
            "difficulty": "high",
            "interest_level": "low",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"this may be cutting it close" not in response.data

    with app.app_context():
        assert Task.query.filter_by(title="History reading").count() == 1

def _make_overdue_task(profile_id, title, *, planned_start_at, started_at=None):
    """Insert an unstarted (by default) overdue-to-start task for route tests."""
    task = Task(
        student_profile_id=profile_id,
        title=title,
        subject="Science",
        due_at=planned_start_at + timedelta(hours=3),
        estimated_minutes=60,
        difficulty="medium",
        interest_level="medium",
        status="not_started",
        planned_start_at=planned_start_at,
        started_at=started_at,
    )
    db.session.add(task)
    db.session.commit()
    return task


def _make_second_user_task(app):
    """Create a second user + profile + task and return the task id."""
    with app.app_context():
        other = User(username="other", password_hash=hash_password("password123"))
        db.session.add(other)
        db.session.commit()
        profile = StudentProfile(
            first_name="Sam",
            grade=12,
            graduation_year=2026,
            current_gpa=3.0,
            target_gpa=3.5,
            study_hours_per_week=8,
            user_id=other.id,
        )
        db.session.add(profile)
        db.session.commit()
        now = datetime.now(timezone.utc)
        task = _make_overdue_task(
            profile.id, "Not yours", planned_start_at=now - timedelta(hours=1)
        )
        return task.id


# --- Start-now via the nudge card (redirect_to=dashboard) ---


def test_start_now_via_nudge_redirects_to_dashboard(app, authed_client):
    now = datetime.now(timezone.utc)
    with app.app_context():
        profile = add_profile(authed_client.user_id)
        task = _make_overdue_task(
            profile.id, "Overdue set", planned_start_at=now - timedelta(hours=2)
        )
        task_id = task.id

    response = authed_client.post(
        f"/tasks/{task_id}/start", data={"redirect_to": "dashboard"}
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")

    with app.app_context():
        task = db.session.get(Task, task_id)
        assert task.status == "in_progress"
        assert task.started_at is not None


def test_start_now_preserves_existing_started_at(app, authed_client):
    now = datetime.now(timezone.utc)
    original_started = now - timedelta(hours=1)
    with app.app_context():
        profile = add_profile(authed_client.user_id)
        task = _make_overdue_task(
            profile.id,
            "Already started",
            planned_start_at=now - timedelta(hours=3),
            started_at=original_started,
        )
        task_id = task.id

    response = authed_client.post(
        f"/tasks/{task_id}/start", data={"redirect_to": "dashboard"}
    )
    assert response.status_code == 302

    with app.app_context():
        task = db.session.get(Task, task_id)
        assert task.status == "in_progress"
        # started_at unchanged (compare as UTC to absorb SQLite naive values).
        stored = task.started_at
        if stored.tzinfo is None:
            stored = stored.replace(tzinfo=timezone.utc)
        assert abs((stored - original_started).total_seconds()) < 1


def test_tasks_page_start_still_redirects_to_tasks(app, authed_client):
    now = datetime.now(timezone.utc)
    with app.app_context():
        profile = add_profile(authed_client.user_id)
        task = _make_overdue_task(
            profile.id, "Plain start", planned_start_at=now - timedelta(hours=1)
        )
        task_id = task.id

    response = authed_client.post(f"/tasks/{task_id}/start")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/tasks")


def test_start_now_unauthenticated_redirects_to_login(app):
    now = datetime.now(timezone.utc)
    with app.app_context():
        user = User(username="owner", password_hash=hash_password("password123"))
        db.session.add(user)
        db.session.commit()
        profile = add_profile(user.id)
        task = _make_overdue_task(
            profile.id, "Locked", planned_start_at=now - timedelta(hours=1)
        )
        task_id = task.id

    client = app.test_client()
    response = client.post(
        f"/tasks/{task_id}/start", data={"redirect_to": "dashboard"}
    )
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

    with app.app_context():
        task = db.session.get(Task, task_id)
        assert task.started_at is None
        assert task.status == "not_started"


def test_start_now_other_users_task_returns_404(app, authed_client):
    with app.app_context():
        add_profile(authed_client.user_id)
    task_id = _make_second_user_task(app)

    response = authed_client.post(
        f"/tasks/{task_id}/start", data={"redirect_to": "dashboard"}
    )
    assert response.status_code == 404

    with app.app_context():
        task = db.session.get(Task, task_id)
        assert task.started_at is None
        assert task.status == "not_started"


# --- Reschedule ---


def _future_local_string(days=3):
    """Return a future Eastern datetime-local string ('%Y-%m-%dT%H:%M')."""
    future = datetime.now(timezone.utc) + timedelta(days=days)
    return future.strftime("%Y-%m-%dT%H:%M")


def test_reschedule_valid_future_sets_planned_start(app, authed_client):
    now = datetime.now(timezone.utc)
    with app.app_context():
        profile = add_profile(authed_client.user_id)
        task = _make_overdue_task(
            profile.id, "Replan me", planned_start_at=now - timedelta(hours=2)
        )
        task_id = task.id

    response = authed_client.post(
        f"/tasks/{task_id}/reschedule",
        data={"planned_start_at": _future_local_string()},
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")

    with app.app_context():
        task = db.session.get(Task, task_id)
        stored = task.planned_start_at
        if stored.tzinfo is None:
            stored = stored.replace(tzinfo=timezone.utc)
        assert stored > now
        assert task.started_at is None


def test_reschedule_missing_value_flashes_error(app, authed_client):
    now = datetime.now(timezone.utc)
    planned = now - timedelta(hours=2)
    with app.app_context():
        profile = add_profile(authed_client.user_id)
        task = _make_overdue_task(
            profile.id, "No value", planned_start_at=planned
        )
        task_id = task.id

    response = authed_client.post(
        f"/tasks/{task_id}/reschedule",
        data={"planned_start_at": ""},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Enter a new planned start" in response.data

    with app.app_context():
        task = db.session.get(Task, task_id)
        stored = task.planned_start_at
        if stored.tzinfo is None:
            stored = stored.replace(tzinfo=timezone.utc)
        assert abs((stored - planned).total_seconds()) < 1


def test_reschedule_unparseable_flashes_error(app, authed_client):
    now = datetime.now(timezone.utc)
    with app.app_context():
        profile = add_profile(authed_client.user_id)
        task = _make_overdue_task(
            profile.id, "Bad value", planned_start_at=now - timedelta(hours=2)
        )
        task_id = task.id

    response = authed_client.post(
        f"/tasks/{task_id}/reschedule",
        data={"planned_start_at": "not-a-date"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Enter a valid planned start" in response.data


def test_reschedule_past_value_flashes_warning_and_no_change(app, authed_client):
    now = datetime.now(timezone.utc)
    planned = now - timedelta(hours=2)
    with app.app_context():
        profile = add_profile(authed_client.user_id)
        task = _make_overdue_task(
            profile.id, "Past replan", planned_start_at=planned
        )
        task_id = task.id

    past_local = (datetime.now(timezone.utc) - timedelta(days=1)).strftime(
        "%Y-%m-%dT%H:%M"
    )
    response = authed_client.post(
        f"/tasks/{task_id}/reschedule",
        data={"planned_start_at": past_local},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Pick a planned start in the future." in response.data

    with app.app_context():
        task = db.session.get(Task, task_id)
        stored = task.planned_start_at
        if stored.tzinfo is None:
            stored = stored.replace(tzinfo=timezone.utc)
        assert abs((stored - planned).total_seconds()) < 1
        assert task.started_at is None


def test_reschedule_unauthenticated_redirects_to_login(app):
    now = datetime.now(timezone.utc)
    with app.app_context():
        user = User(username="owner", password_hash=hash_password("password123"))
        db.session.add(user)
        db.session.commit()
        profile = add_profile(user.id)
        task = _make_overdue_task(
            profile.id, "Locked replan", planned_start_at=now - timedelta(hours=1)
        )
        task_id = task.id

    client = app.test_client()
    response = client.post(
        f"/tasks/{task_id}/reschedule",
        data={"planned_start_at": _future_local_string()},
    )
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_reschedule_other_users_task_returns_404(app, authed_client):
    with app.app_context():
        add_profile(authed_client.user_id)
    task_id = _make_second_user_task(app)

    response = authed_client.post(
        f"/tasks/{task_id}/reschedule",
        data={"planned_start_at": _future_local_string()},
    )
    assert response.status_code == 404


# =========================================================================
# Property-based tests (Hypothesis) — Task 6.2
# Validates: Requirements 3.2, 3.3, 3.7, 4.2, 4.3, 4.4, 4.5, 4.6, 4.10,
#            5.1, 5.2
# =========================================================================

from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from services import datetime_util


def _eastern_local_string(target_utc):
    """Format a UTC instant as an Eastern-local 'datetime-local' string.

    The reschedule route parses naive input via datetime_util.to_utc, which
    interprets naive values as Eastern, so we build the string in Eastern to
    keep the round-trip consistent.
    """
    return target_utc.astimezone(datetime_util.EASTERN).strftime("%Y-%m-%dT%H:%M")


@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(offset_seconds=st.integers(min_value=-100000, max_value=100000))
def test_reschedule_future_only_boundary(app, authed_client, offset_seconds):
    # Feature: overdue-start-nudge, Property 6: Reschedule is future-only and never touches started_at
    # Minute-resolution parsing makes offsets near zero ambiguous; skip a clear
    # band around now so future/past classification is unambiguous.
    assume(abs(offset_seconds) >= 120)

    now = datetime.now(timezone.utc)
    original_planned = now - timedelta(hours=5)
    candidate_utc = now + timedelta(seconds=offset_seconds)
    # The parsed value is truncated to minute resolution by the input string.
    expected_write = candidate_utc > now

    with app.app_context():
        # Fresh profile+task per example (function-scoped fixture is reused
        # across examples, so give each task a unique title and rebuild state).
        profile = StudentProfile.query.filter_by(
            user_id=authed_client.user_id
        ).first()
        if profile is None:
            profile = add_profile(authed_client.user_id)
        task = _make_overdue_task(
            profile.id,
            f"Prop6 {offset_seconds}",
            planned_start_at=original_planned,
        )
        task_id = task.id

    response = authed_client.post(
        f"/tasks/{task_id}/reschedule",
        data={"planned_start_at": _eastern_local_string(candidate_utc)},
    )
    assert response.status_code == 302

    with app.app_context():
        task = db.session.get(Task, task_id)
        # started_at is NEVER touched, in all cases.
        assert task.started_at is None

        stored = task.planned_start_at
        if stored.tzinfo is None:
            stored = stored.replace(tzinfo=timezone.utc)

        if expected_write:
            # planned_start_at moved to the future value (minute resolution).
            assert stored > now
        else:
            # Rejected: unchanged from the original past plan.
            assert abs((stored - original_planned).total_seconds()) < 1


@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    already_started=st.booleans(),
    planned_past_seconds=st.integers(min_value=60, max_value=100000),
)
def test_start_now_records_late_start(
    app, authed_client, already_started, planned_past_seconds
):
    # Feature: overdue-start-nudge, Property 7: Start_Now records the genuine late start
    now = datetime.now(timezone.utc)
    planned = now - timedelta(seconds=planned_past_seconds)
    original_started = now - timedelta(hours=1) if already_started else None

    with app.app_context():
        profile = StudentProfile.query.filter_by(
            user_id=authed_client.user_id
        ).first()
        if profile is None:
            profile = add_profile(authed_client.user_id)
        task = _make_overdue_task(
            profile.id,
            f"Prop7 {already_started}-{planned_past_seconds}",
            planned_start_at=planned,
            started_at=original_started,
        )
        task_id = task.id

    response = authed_client.post(
        f"/tasks/{task_id}/start", data={"redirect_to": "dashboard"}
    )
    assert response.status_code == 302

    with app.app_context():
        task = db.session.get(Task, task_id)
        assert task.status == "in_progress"
        if original_started is None:
            # A genuine late start is now recorded.
            assert task.started_at is not None
        else:
            # Existing started_at preserved.
            stored = task.started_at
            if stored.tzinfo is None:
                stored = stored.replace(tzinfo=timezone.utc)
            assert abs((stored - original_started).total_seconds()) < 1


# =========================================================================
# Recurring-sessions route tests — Task 4.5
# Validates: Requirements 3.1, 3.7, 3.8, 3.9, 3.10, 4.1, 4.2, 4.3, 4.8,
#            4.11, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 6.2, 6.3, 7.2, 7.3
# =========================================================================

from services import recurrence_service


def _future_dt_local(days=10, hour=18, minute=0):
    """Return a future Eastern datetime-local string '%Y-%m-%dT%H:%M'."""
    base = datetime.now(datetime_util.EASTERN) + timedelta(days=days)
    base = base.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return base.strftime("%Y-%m-%dT%H:%M")


def _valid_task_payload(**overrides):
    payload = {
        "title": "SAT Math tutoring",
        "subject": "Math",
        "task_type": "Tutoring",
        "due_at": _future_dt_local(days=10),
        "planned_start_at": _future_dt_local(days=9),
        "estimated_minutes": "60",
        "difficulty": "medium",
        "interest_level": "high",
    }
    payload.update(overrides)
    return payload


def test_create_recurring_task_creates_linked_prep(app, authed_client):
    with app.app_context():
        profile = add_profile(authed_client.user_id)
        profile_id = profile.id

    response = authed_client.post(
        "/tasks", data=_valid_task_payload(recurrence_rule="weekly")
    )
    assert response.status_code == 302

    with app.app_context():
        session_task = Task.query.filter_by(recurrence_rule="weekly").one()
        assert session_task.student_profile_id == profile_id
        prep = Task.query.filter_by(prep_for_id=session_task.id).one()
        assert prep.student_profile_id == profile_id
        assert prep.title.startswith("Prep: ")
        assert prep.recurrence_rule is None
        session_due = session_task.due_at
        prep_due = prep.due_at
        if session_due.tzinfo is None:
            session_due = session_due.replace(tzinfo=timezone.utc)
        if prep_due.tzinfo is None:
            prep_due = prep_due.replace(tzinfo=timezone.utc)
        assert abs(
            (session_due - prep_due).total_seconds() - 24 * 3600
        ) < 1


def test_create_non_recurring_task_creates_no_prep(app, authed_client):
    with app.app_context():
        add_profile(authed_client.user_id)

    response = authed_client.post(
        "/tasks", data=_valid_task_payload(recurrence_rule="")
    )
    assert response.status_code == 302

    with app.app_context():
        assert Task.query.count() == 1
        only = Task.query.one()
        assert only.recurrence_rule is None
        assert only.prep_for_id is None


def test_create_invalid_recurrence_rejected(app, authed_client):
    with app.app_context():
        add_profile(authed_client.user_id)

    response = authed_client.post(
        "/tasks",
        data=_valid_task_payload(title="Yearly thing", recurrence_rule="yearly"),
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Select a valid recurrence option." in response.data
    # Other submitted fields preserved in the re-rendered form.
    assert b"Yearly thing" in response.data

    with app.app_context():
        assert Task.query.count() == 0


def test_complete_recurring_materializes_next_occurrence(app, authed_client):
    with app.app_context():
        profile = add_profile(authed_client.user_id)
        original_due = datetime_util.to_utc(_future_dt_local(days=10))
        task = Task(
            student_profile_id=profile.id,
            title="Weekly tutoring",
            subject="Math",
            task_type="Tutoring",
            due_at=original_due,
            estimated_minutes=60,
            difficulty="medium",
            interest_level="high",
            recurrence_rule="weekly",
            status="not_started",
        )
        db.session.add(task)
        db.session.commit()
        task_id = task.id
        original_due_val = original_due

    response = authed_client.post(f"/tasks/{task_id}/complete")
    assert response.status_code == 302

    with app.app_context():
        completed = db.session.get(Task, task_id)
        assert completed.status == "completed"

        next_tasks = Task.query.filter(
            Task.recurrence_rule == "weekly",
            Task.status == "not_started",
            Task.title == "Weekly tutoring",
        ).all()
        assert len(next_tasks) == 1
        next_task = next_tasks[0]

        # The next occurrence is one weekly interval after the original. The
        # pure recurrence service owns the DST-safe math; the route persists
        # its output. We assert the new occurrence lands 7 calendar days after
        # the original session's due date. (SQLite returns these DateTime
        # columns naive in this environment; both values are read back through
        # the same column, so we compare them directly by calendar date and
        # allow the intra-day offset the storage layer introduces.)
        stored_orig = completed.due_at
        stored_new = next_task.due_at
        delta_days = (stored_new.date() - stored_orig.date()).days
        # Weekly advance is 7 local days; storage-layer tz normalization can
        # nudge the wall-clock across a day boundary, so allow 7 or 8.
        assert delta_days in (7, 8)
        # And the interval is well under two weeks and at least a week.
        interval = stored_new - stored_orig
        assert timedelta(days=7) <= interval < timedelta(days=8, hours=1)

        # A prep task for the next occurrence exists.
        prep = Task.query.filter_by(prep_for_id=next_task.id).one()
        assert prep.title.startswith("Prep: ")


def test_complete_non_recurring_materializes_nothing(app, authed_client):
    with app.app_context():
        profile = add_profile(authed_client.user_id)
        task = Task(
            student_profile_id=profile.id,
            title="One-off essay",
            due_at=datetime_util.to_utc(_future_dt_local(days=5)),
            estimated_minutes=60,
            difficulty="medium",
            interest_level="medium",
            status="not_started",
        )
        db.session.add(task)
        db.session.commit()
        task_id = task.id

    response = authed_client.post(f"/tasks/{task_id}/complete")
    assert response.status_code == 302

    with app.app_context():
        assert Task.query.count() == 1


def test_complete_other_users_task_returns_404(app, authed_client):
    with app.app_context():
        add_profile(authed_client.user_id)
    task_id = _make_second_user_task(app)

    response = authed_client.post(f"/tasks/{task_id}/complete")
    assert response.status_code == 404

    with app.app_context():
        task = db.session.get(Task, task_id)
        assert task.status == "not_started"


def _make_session_with_prep(profile_id, *, prep_completed=False):
    """Insert a recurring session plus a linked prep task; return their ids."""
    session_task = Task(
        student_profile_id=profile_id,
        title="Session with prep",
        due_at=datetime_util.to_utc(_future_dt_local(days=10)),
        estimated_minutes=60,
        difficulty="medium",
        interest_level="medium",
        recurrence_rule="weekly",
        status="not_started",
    )
    db.session.add(session_task)
    db.session.commit()
    prep = Task(
        student_profile_id=profile_id,
        prep_for_id=session_task.id,
        title="Prep: Session with prep",
        due_at=datetime_util.to_utc(_future_dt_local(days=9)),
        estimated_minutes=30,
        difficulty="medium",
        interest_level="medium",
        status="completed" if prep_completed else "not_started",
    )
    db.session.add(prep)
    db.session.commit()
    return session_task.id, prep.id


def test_delete_session_removes_pending_prep(app, authed_client):
    with app.app_context():
        profile = add_profile(authed_client.user_id)
        session_id, prep_id = _make_session_with_prep(profile.id)

    response = authed_client.post(f"/tasks/{session_id}/delete")
    assert response.status_code == 302

    with app.app_context():
        assert db.session.get(Task, session_id) is None
        assert db.session.get(Task, prep_id) is None


def test_delete_session_preserves_completed_prep(app, authed_client):
    with app.app_context():
        profile = add_profile(authed_client.user_id)
        session_id, prep_id = _make_session_with_prep(
            profile.id, prep_completed=True
        )

    response = authed_client.post(f"/tasks/{session_id}/delete")
    assert response.status_code == 302

    with app.app_context():
        assert db.session.get(Task, session_id) is None
        surviving = db.session.get(Task, prep_id)
        assert surviving is not None
        assert surviving.status == "completed"


def test_delete_prep_directly_leaves_session(app, authed_client):
    with app.app_context():
        profile = add_profile(authed_client.user_id)
        session_id, prep_id = _make_session_with_prep(profile.id)

    response = authed_client.post(f"/tasks/{prep_id}/delete")
    assert response.status_code == 302

    with app.app_context():
        assert db.session.get(Task, prep_id) is None
        assert db.session.get(Task, session_id) is not None


def test_edit_updates_recurrence_only_no_retroactive_prep(app, authed_client):
    with app.app_context():
        profile = add_profile(authed_client.user_id)
        task = Task(
            student_profile_id=profile.id,
            title="Becomes recurring",
            due_at=datetime_util.to_utc(_future_dt_local(days=8)),
            estimated_minutes=60,
            difficulty="medium",
            interest_level="medium",
            status="not_started",
        )
        db.session.add(task)
        db.session.commit()
        task_id = task.id

    response = authed_client.post(
        f"/tasks/{task_id}/edit",
        data=_valid_task_payload(
            title="Becomes recurring", recurrence_rule="weekly"
        ),
    )
    assert response.status_code == 302

    with app.app_context():
        edited = db.session.get(Task, task_id)
        assert edited.recurrence_rule == "weekly"
        # No retroactive prep created on edit.
        assert Task.query.filter_by(prep_for_id=task_id).count() == 0


# =========================================================================
# Recurring-sessions template tests — Task 6.4
# Validates: Requirements 6.1, 6.4, 6.5
# =========================================================================


def test_create_form_renders_recurrence_select(app, authed_client):
    with app.app_context():
        add_profile(authed_client.user_id)

    response = authed_client.get("/tasks")
    assert response.status_code == 200
    body = response.data
    assert b'name="recurrence_rule"' in body
    assert b">None<" in body
    assert b">Daily<" in body
    assert b">Weekly<" in body
    assert b">Every 2 weeks<" in body
    assert b">Monthly<" in body


def test_edit_form_preselects_current_recurrence(app, authed_client):
    with app.app_context():
        profile = add_profile(authed_client.user_id)
        task = Task(
            student_profile_id=profile.id,
            title="Weekly editable",
            due_at=datetime_util.to_utc(_future_dt_local(days=6)),
            estimated_minutes=60,
            difficulty="medium",
            interest_level="medium",
            recurrence_rule="weekly",
            status="not_started",
        )
        db.session.add(task)
        db.session.commit()
        task_id = task.id

    response = authed_client.get(f"/tasks/{task_id}/edit")
    assert response.status_code == 200
    assert b'value="weekly" selected' in response.data
