from datetime import datetime, timedelta, timezone
from io import BytesIO
from types import SimpleNamespace
import re

import pytest

from extensions import db
from models import Task, User, StudentProfile
from services.task_policy import MAX_TASK_MINUTES, split_minutes
from services.suggestion_service import get_suggested_tasks
from services.timing_service import timing_summary
from services.calendar_import import parse_calendar
from tests.test_course_routes import complete_profile


def create(client, **changes):
    values = dict(title="Research paper", subject="Science", due_at="2027-02-01",
                  estimated_minutes="1200", nonpersonal_confirmed="yes")
    values.update(changes)
    return client.post("/tasks", data=values)


def test_duration_date_defaults_and_explicit_time(app, authed_client):
    complete_profile(authed_client)
    for minutes in (1200, 1441, MAX_TASK_MINUTES):
        assert create(authed_client, estimated_minutes=str(minutes)).status_code == 302
    with app.app_context():
        assert Task.query.count() == 3
        # 23:59 Eastern in February is 04:59 UTC the next day.
        assert Task.query.first().due_at == datetime(2027, 2, 2, 4, 59)
    create(authed_client, due_time="09:15")
    with app.app_context():
        assert Task.query.order_by(Task.id.desc()).first().due_at == datetime(2027, 2, 1, 14, 15)
    for value in ("0", "-1", "10081", "abc"):
        assert create(authed_client, estimated_minutes=value).status_code == 200
    with app.app_context():
        assert Task.query.count() == 4


def test_subtask_split_progress_reopen_and_queue(app, authed_client):
    complete_profile(authed_client)
    create(authed_client, estimated_minutes="40")
    with app.app_context():
        parent_id = Task.query.first().id
    authed_client.post(f"/tasks/{parent_id}/split")
    with app.app_context():
        parent = db.session.get(Task, parent_id)
        assert [c.estimated_minutes for c in parent.children] == [25, 15]
        ids = [c.id for c in parent.children]
        rows = get_suggested_tasks(Task.query.all())
        assert parent not in [r["task"] for r in rows]
        assert len(rows) == 2
    authed_client.post(f"/tasks/{ids[0]}/complete", data={"actual_minutes": "25"})
    with app.app_context():
        assert db.session.get(Task, parent_id).progress == 50
    authed_client.post(f"/tasks/{ids[1]}/complete", data={"actual_minutes": "15"})
    with app.app_context():
        parent = db.session.get(Task, parent_id)
        assert parent.status == "completed"
        assert parent.actual_minutes == 40
    body = authed_client.get("/tasks").get_data(as_text=True)
    assert "Work block 1" not in body.split('id="completed-tasks"')[0]
    assert "Work block 1" in body.split('id="completed-tasks"')[1]
    authed_client.post(f"/tasks/{ids[0]}/undo-complete")
    with app.app_context():
        assert db.session.get(Task, parent_id).progress == 50
        assert db.session.get(Task, parent_id).completed_at is None
    # Cannot nest or complete a project with unfinished children.
    authed_client.post(f"/tasks/{ids[0]}/split")
    authed_client.post(f"/tasks/{parent_id}/complete")
    with app.app_context():
        assert Task.query.count() == 3
        assert db.session.get(Task, parent_id).status != "completed"


def test_subtask_ownership_and_inheritance(app, authed_client):
    complete_profile(authed_client)
    create(authed_client)
    with app.app_context():
        parent_id = Task.query.first().id
        other = User(username="other-feedback", password_hash="unused")
        db.session.add(other)
        db.session.flush()
        profile = StudentProfile(user_id=other.id, first_name="Example", grade=9, graduation_year=2030,
                                 current_gpa=3, target_gpa=3, study_hours_per_week=5)
        db.session.add(profile)
        db.session.flush()
        task = Task(student_profile_id=profile.id, title="Other", due_at=datetime.now(timezone.utc), estimated_minutes=60)
        db.session.add(task)
        db.session.commit()
        other_id = task.id
    values = dict(title="Outline", estimated_minutes="30", nonpersonal_confirmed="yes")
    assert authed_client.post(f"/tasks/{other_id}/subtasks", data=values).status_code == 404
    assert authed_client.post(f"/tasks/{other_id}/split").status_code == 404
    authed_client.post(f"/tasks/{parent_id}/subtasks", data=values)
    with app.app_context():
        child = Task.query.filter_by(parent_task_id=parent_id).one()
        assert child.subject == "Science"
        assert child.due_at == child.parent.due_at


def test_tiers_stability_and_urgent_deadline():
    now = datetime(2027, 1, 1, tzinfo=timezone.utc)
    def task(id, hours, **kw):
        values = dict(id=id, title=str(id), due_at=now+timedelta(hours=hours), status="not_started",
                      planned_start_at=None, started_at=None, estimated_minutes=30,
                      difficulty="low", interest_level="high", subject="Science", task_type=None)
        values.update(kw)
        return SimpleNamespace(**values)
    tasks = [task(5, 48, estimated_minutes=500, difficulty="high", interest_level="low"), task(4, 8),
             task(3, 48, planned_start_at=now-timedelta(hours=1)), task(2, -1), task(1, 80, status="in_progress"), task(6, 8)]
    assert [r["task"].id for r in get_suggested_tasks(tasks, now)] == [1, 2, 3, 4, 6, 5]
    assert [r["task"].id for r in get_suggested_tasks(reversed(tasks), now)] == [1, 2, 3, 4, 6, 5]


def test_timing_normalizes_subjects_and_keeps_negative_delays():
    now = datetime(2027, 1, 1, tzinfo=timezone.utc)
    tasks = [SimpleNamespace(id=i, title=str(i), subject=subject, status="completed", planned_start_at=now,
                            started_at=now+timedelta(minutes=delay), completed_at=now+timedelta(hours=2),
                            due_at=now, estimated_minutes=60, actual_minutes=90)
             for i, (subject, delay) in enumerate([("Science", -30), ("science", 0), (" SCIENCE ", 60)])]
    result = timing_summary(tasks)
    assert result["count"] == 3
    assert result["median"] == "On time"
    assert result["on_time"] == 67
    assert len(result["subjects"]) == 1
    assert result["subjects"][0]["value"] == 10
    assert result["delays"][0]["value"] == -30
    assert len(result["durations"]) == 3
    assert timing_summary([])["count"] == 0


@pytest.mark.parametrize("total,block", [(40,25), (10080,25), (1,60), (1200,60)])
def test_exact_work_blocks(total, block):
    blocks = split_minutes(total, block)
    assert sum(blocks) == total
    assert all(0 < value <= block for value in blocks)


def test_college_settings_and_manual_terms(app, authed_client):
    complete_profile(authed_client)
    authed_client.post("/settings", data={"academic_context": "college"})
    body = authed_client.get("/dashboard").get_data(as_text=True)
    assert "College planning" in body
    assert "th grade" not in body
    assert 'href="/terms' in body
    response = authed_client.post("/terms", data=dict(title="BIO 101", term="Fall 2027", weekly_hours="4", nonpersonal_confirmed="yes"), follow_redirects=True)
    assert b"BIO 101" in response.data
    assert b"4.0</strong> estimated study hours" in response.data
    assert authed_client.get("/settings/export").json["term_courses"][0]["term"] == "Fall 2027"


ICS = b"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nBEGIN:VEVENT\r\nUID:demo-assignment\r\nDTSTART;VALUE=DATE:20270201\r\nSUMMARY:Fictional paper\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n"


def test_calendar_preview_dedup_and_export(app, authed_client):
    complete_profile(authed_client)
    events = parse_calendar(ICS, "America/New_York")
    assert events[0]["due_at"] == "2027-02-02T04:59:00+00:00"
    response = authed_client.post("/tasks/import", data={"calendar": (BytesIO(ICS), "demo.ics"), "nonpersonal_confirmed": "yes"})
    token = re.search(r'name="preview" value="([^"]+)"', response.get_data(as_text=True))[1]
    values = dict(preview=token, confirm="yes", selected="0", estimated_minutes="1800", nonpersonal_confirmed="yes")
    authed_client.post("/tasks/import", data=values)
    authed_client.post("/tasks/import", data=values)
    with app.app_context():
        assert Task.query.count() == 1
        assert Task.query.one().estimated_minutes == 1800
    export = authed_client.get("/settings/calendar.ics")
    assert b"Fictional paper" in export.data
    assert b"BEGIN:VEVENT" in export.data


def test_onboarding_and_mobile_entry(authed_client):
    complete_profile(authed_client)
    body = authed_client.get("/dashboard").get_data(as_text=True)
    assert 'id="orientation-dismiss"' in body and 'id="orientation-reopen"' in body
    public = authed_client.application.test_client().get("/").get_data(as_text=True)
    for label in ("Explore Demo", "Create Private Planner", "I already have a code"):
        assert label in public


def test_additive_migration_preserves_legacy_rows(app):
    from app import _migrate_feedback_columns
    from sqlalchemy import text, inspect
    with app.app_context():
        db.drop_all()
        db.session.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, username VARCHAR(80))"))
        db.session.execute(text("INSERT INTO users (id,username) VALUES (1,'existing-account')"))
        db.session.execute(text("CREATE TABLE tasks (id INTEGER PRIMARY KEY, title VARCHAR(160))"))
        db.session.execute(text("CREATE TABLE user_settings (id INTEGER PRIMARY KEY)"))
        db.session.execute(text("CREATE TABLE term_courses (id INTEGER PRIMARY KEY, title VARCHAR(120), weekly_hours FLOAT)"))
        db.session.execute(text("INSERT INTO term_courses (id,title,weekly_hours) VALUES (1,'Existing college course',4)"))
        db.session.execute(text("INSERT INTO tasks (id,title) VALUES (1,'Existing history')"))
        db.session.execute(text("INSERT INTO user_settings (id) VALUES (1)"))
        db.session.commit()
        _migrate_feedback_columns()
        _migrate_feedback_columns()
        assert db.session.execute(text("SELECT username,email,auth_version FROM users WHERE id=1")).one() == ('existing-account', None, 0)
        assert db.session.execute(text("SELECT title FROM tasks WHERE id=1")).scalar() == "Existing history"
        assert db.session.execute(text("SELECT academic_context FROM user_settings WHERE id=1")).scalar() == "high_school"
        assert db.session.execute(text("SELECT title, weekly_hours, enrollment_type, status, institution_id FROM term_courses WHERE id=1")).one() == ('Existing college course', 4, 'college', 'planned', None)
        assert db.session.execute(text("SELECT college_program, college_term, term_credit_goal FROM user_settings WHERE id=1")).one() == ('', '', None)
        assert db.session.execute(text("SELECT requirement_area FROM term_courses WHERE id=1")).scalar() == 'unspecified'
        assert {"parent_task_id", "external_uid"} <= {c["name"] for c in inspect(db.engine).get_columns("tasks")}


def test_import_token_and_term_ownership(app, authed_client):
    complete_profile(authed_client)
    response = authed_client.post("/tasks/import", data={"preview":"tampered", "confirm":"yes", "nonpersonal_confirmed":"yes"})
    assert b"Could not import" in response.data
    with app.app_context():
        assert Task.query.count() == 0
    # Privacy is required on editable free-text content, not queue sorting.
    assert b"confirm" in authed_client.post("/terms", data={"title":"Example", "term":"Fall", "weekly_hours":"3"}).data.lower()
    assert authed_client.get("/tasks?sort=subject").status_code == 200


def test_completion_large_actual_and_reminders(app, authed_client):
    complete_profile(authed_client)
    create(authed_client, due_at=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat(), reminder_enabled="on")
    with app.app_context():
        task = Task.query.one()
        task_id = task.id
        settings = task.student_profile.user.settings
        settings.reminders_enabled = True
        local_hour = datetime.now(timezone.utc).astimezone(__import__('zoneinfo').ZoneInfo(settings.timezone_name)).hour
        settings.quiet_start = f"{(local_hour+2)%24:02d}:00"
        settings.quiet_end = f"{(local_hour+3)%24:02d}:00"
        db.session.commit()
    assert b"REMINDERS YOU REQUESTED" in authed_client.get("/dashboard").data
    authed_client.post(f"/tasks/{task_id}/snooze-reminder")
    assert b"REMINDERS YOU REQUESTED" not in authed_client.get("/dashboard").data
    authed_client.post(f"/tasks/{task_id}/complete", data={"actual_minutes":"10080"})
    with app.app_context():
        assert db.session.get(Task, task_id).actual_minutes == MAX_TASK_MINUTES
