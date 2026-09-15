from datetime import datetime, timedelta, timezone
import json

from extensions import db
from models import StudentProfile, Task, User, UserSettings


def add_profile(user_id):
    profile = StudentProfile(
        first_name="Alex",
        grade=11,
        graduation_year=2027,
        current_gpa=3.5,
        target_gpa=3.8,
        study_hours_per_week=10,
        user_id=user_id,
    )
    db.session.add(profile)
    db.session.commit()
    return profile


def test_settings_page_and_preferences_persist(app, authed_client):
    response = authed_client.get("/settings")
    assert response.status_code == 200
    assert b"Make the workspace work for you" in response.data

    response = authed_client.post(
        "/settings",
        data={
            "theme": "high-contrast",
            "text_scale": "150",
            "comfortable_spacing": "on",
            "reduce_motion": "on",
            "font_choice": "sans",
            "dashboard_mode": "focus",
            "hidden_cards": ["history", "profile"],
            "card_density": "compact",
            "default_task_minutes": "45",
            "work_session_minutes": "25",
            "start_buffer_days": "3",
            "suggest_breakdown": "on",
            "recommendation_count": "1",
            "recommendation_tone": "encouraging",
            "reminders_enabled": "on",
            "reminder_lead_hours": "48",
            "quiet_start": "22:00",
            "quiet_end": "06:00",
            "snooze_minutes": "60",
            "calendar_export_enabled": "on",
            "timezone_name": "America/Chicago",
            "time_format": "24-hour",
            "week_start": "Monday",
            "date_format": "day-first",
            "relative_dates": "on",
            "session_timeout_minutes": "120",
        },
    )
    assert response.status_code == 302

    with app.app_context():
        saved = UserSettings.query.one()
        assert saved.theme == "high-contrast"
        assert saved.text_scale == 150
        assert saved.dashboard_mode == "focus"
        assert saved.hidden_cards == {"history", "profile"}
        assert saved.timezone_name == "America/Chicago"
        assert saved.session_timeout_minutes == 120


def test_focus_mode_hides_dashboard_detail_grid(app, authed_client):
    with app.app_context():
        add_profile(authed_client.user_id)
    authed_client.post("/settings", data={"dashboard_mode": "focus"})

    response = authed_client.get("/dashboard")

    assert response.status_code == 200
    assert b"WHAT TO WORK ON NOW" in response.data
    assert b"COMPLETION RATE" not in response.data


def test_data_and_calendar_exports_are_scoped_to_user(app, authed_client):
    with app.app_context():
        profile = add_profile(authed_client.user_id)
        db.session.add(
            Task(
                student_profile_id=profile.id,
                title="Export me",
                due_at=datetime.now(timezone.utc) + timedelta(days=1),
                estimated_minutes=30,
                difficulty="low",
                interest_level="high",
                status="not_started",
            )
        )
        db.session.commit()

    data_response = authed_client.get("/settings/export")
    calendar_response = authed_client.get("/settings/calendar.ics")

    assert data_response.status_code == 200
    assert json.loads(data_response.data)["tasks"][0]["title"] == "Export me"
    assert calendar_response.status_code == 200
    assert b"BEGIN:VCALENDAR" in calendar_response.data
    assert b"SUMMARY:Export me due" in calendar_response.data


def test_clear_history_keeps_active_tasks(app, authed_client):
    with app.app_context():
        profile = add_profile(authed_client.user_id)
        for status in ("completed", "not_started"):
            db.session.add(
                Task(
                    student_profile_id=profile.id,
                    title=status,
                    due_at=datetime.now(timezone.utc),
                    estimated_minutes=30,
                    difficulty="low",
                    interest_level="low",
                    status=status,
                )
            )
        db.session.commit()

    response = authed_client.post("/settings/clear-history")
    assert response.status_code == 302
    with app.app_context():
        assert [task.status for task in Task.query.all()] == ["not_started"]


def test_delete_account_removes_owned_data(app, authed_client):
    with app.app_context():
        add_profile(authed_client.user_id)
    authed_client.get("/settings")

    response = authed_client.post(
        "/settings/delete-account", data={"password": "password123"}
    )

    assert response.status_code == 302
    with app.app_context():
        assert User.query.count() == 0
        assert StudentProfile.query.count() == 0
        assert UserSettings.query.count() == 0


def test_reminder_can_be_shown_and_snoozed(app, authed_client):
    with app.app_context():
        profile = add_profile(authed_client.user_id)
        task = Task(
            student_profile_id=profile.id,
            title="Reminder task",
            due_at=datetime.now(timezone.utc) + timedelta(hours=1),
            estimated_minutes=20,
            difficulty="medium",
            interest_level="medium",
            status="not_started",
        )
        db.session.add(task)
        db.session.commit()
        task_id = task.id
    authed_client.post(
        "/settings",
        data={
            "reminders_enabled": "on",
            "reminder_lead_hours": "24",
            "quiet_start": "00:00",
            "quiet_end": "00:01",
            "snooze_minutes": "30",
        },
    )

    assert b"Reminder task" in authed_client.get("/dashboard").data
    authed_client.post(f"/tasks/{task_id}/snooze-reminder")
    response = authed_client.get("/dashboard")
    assert b"REMINDERS YOU REQUESTED" not in response.data


def test_custom_session_timeout_allows_more_time(app, authed_client):
    authed_client.post("/settings", data={"session_timeout_minutes": "120"})
    with authed_client.session_transaction() as current_session:
        current_session["_last_active"] = (
            datetime.now(timezone.utc) - timedelta(minutes=60)
        ).isoformat()

    response = authed_client.get("/settings")

    assert response.status_code == 200
