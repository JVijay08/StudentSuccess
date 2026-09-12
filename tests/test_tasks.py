from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app import create_app
from extensions import db
from models import StudentProfile, Task
from services.procrastination_service import (
    calculate_procrastination_risk,
    explain_procrastination_risk,
)


@pytest.fixture()
def app(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": (
                f"sqlite:///{tmp_path / 'tasks-test.db'}"
            ),
        }
    )

    with app.app_context():
        db.create_all()

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()


def add_profile():
    profile = StudentProfile(
        first_name="Alex",
        grade=11,
        graduation_year=2027,
        current_gpa=3.7,
        target_gpa=3.9,
        study_hours_per_week=12,
    )
    db.session.add(profile)
    db.session.commit()
    return profile


def test_task_table_and_student_association(app):
    with app.app_context():
        profile = add_profile()
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


def test_task_route_creates_starts_and_completes_task(app):
    client = app.test_client()
    with app.app_context():
        add_profile()

    response = client.post(
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

    assert client.post(f"/tasks/{task_id}/start").status_code == 302
    with app.app_context():
        task = db.session.get(Task, task_id)
        assert task.status == "in_progress"
        assert task.started_at is not None

    assert client.post(f"/tasks/{task_id}/complete").status_code == 302
    with app.app_context():
        task = db.session.get(Task, task_id)
        assert task.status == "completed"
        assert task.completed_at is not None


def test_tasks_redirects_to_onboarding_without_profile(app):
    response = app.test_client().get("/tasks")

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
