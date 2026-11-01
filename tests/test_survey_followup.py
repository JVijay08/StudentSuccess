from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from extensions import db
from models import Task, User
from services.daily_tasks import daily_task_rows
from services.delay_service import start_delay
from services.burn_rate_service import is_measurable
from services.suggestion_service import get_suggested_tasks
from tests.test_course_routes import complete_profile
from tests.test_feedback_overhaul import create


def test_direct_completion_never_invents_start_but_accepts_duration(app, authed_client):
    complete_profile(authed_client)
    create(authed_client, planned_start_at='2026-10-01T12:00')
    with app.app_context():
        identifier = Task.query.one().id
    authed_client.post(f'/tasks/{identifier}/complete', data={'actual_minutes': '45'})
    with app.app_context():
        task = db.session.get(Task, identifier)
        assert task.status == 'completed' and task.completed_at is not None
        assert task.started_at is None and start_delay(task) is None
        assert task.actual_minutes == 45 and is_measurable(task)


def test_tracking_off_is_enforced_and_excluded_after_reenable(app, authed_client):
    complete_profile(authed_client)
    create(authed_client, planned_start_at='2026-10-01T12:00')
    authed_client.post('/settings', data={'time_tracking_enabled': 'no'})
    with app.app_context():
        assert not db.session.get(User, authed_client.user_id).settings.time_tracking_enabled
        identifier = Task.query.one().id
    authed_client.post(f'/tasks/{identifier}/start')
    with app.app_context():
        task = db.session.get(Task, identifier)
        assert task.status == 'in_progress' and task.started_at is None
    html = authed_client.get('/dashboard').get_data(as_text=True)
    assert 'Timing and work history' not in html
    assert 'Record time &amp; complete' not in html
    assert 'History adds 1 point' not in html
    assert 'Record focused time' not in authed_client.get(f'/tasks/{identifier}').get_data(as_text=True)
    authed_client.post(f'/tasks/{identifier}/complete', data={'actual_minutes': '99'})
    authed_client.post('/settings', data={'time_tracking_enabled': 'yes'})
    with app.app_context():
        task = db.session.get(Task, identifier)
        assert task.status == 'completed' and task.completed_at is not None
        assert task.actual_minutes is None and task.started_at is None
        assert task.timing_excluded and not is_measurable(task)
        assert start_delay(task) is None


def test_start_before_optout_is_preserved_but_not_measured(app, authed_client):
    complete_profile(authed_client)
    create(authed_client)
    with app.app_context():
        identifier = Task.query.one().id
    authed_client.post(f'/tasks/{identifier}/start')
    authed_client.post('/settings', data={'time_tracking_enabled': 'no'})
    authed_client.post(f'/tasks/{identifier}/complete')
    with app.app_context():
        task = db.session.get(Task, identifier)
        assert task.started_at is not None
        assert not is_measurable(task)


def test_history_can_be_disabled_without_changing_status_priority():
    now = datetime(2026, 10, 27, tzinfo=timezone.utc)
    def task(identifier, status, **extra):
        values = dict(id=identifier, title=str(identifier), status=status, subject='Math', task_type='',
                      due_at=now + timedelta(days=3), planned_start_at=now - timedelta(hours=8),
                      started_at=None, estimated_minutes=30, difficulty='medium', interest_level='medium', children=[])
        values.update(extra)
        return SimpleNamespace(**values)
    history = [task(i, 'completed', started_at=now) for i in (1, 2)]
    active = task(3, 'in_progress')
    assert get_suggested_tasks(history + [active], now)[0]['bonus'] == 2
    row = get_suggested_tasks(history + [active], now, use_history=False)[0]
    assert row['bonus'] == 0 and row['tier'] == 0
    assert not any(f['key'] == 'start' for f in row['factors'])


def test_daily_partition_timezone_duplicates_and_overdue():
    # UTC is already October 28; New York is still October 27.
    now = datetime(2026, 10, 28, 1, tzinfo=timezone.utc)
    def row(identifier, due, planned=None, status='not_started', children=None):
        return {'task': SimpleNamespace(id=identifier, due_at=due, planned_start_at=planned,
                                        status=status, children=children or [])}
    later = now + timedelta(hours=2)
    tomorrow = now + timedelta(days=1)
    rows = [row(1, later, later), row(2, tomorrow, later), row(3, now - timedelta(hours=1), later),
            row(4, tomorrow), row(5, later, status='completed'), row(6, later, children=[1]),
            row(7, later.replace(tzinfo=None))]
    today, overdue = daily_task_rows(rows, 'America/New_York', now)
    assert [r['task'].id for r in today] == [1, 2, 7]
    assert [r['task'].id for r in overdue] == [3]


def test_dashboard_reason_is_visible_and_details_do_not_repeat(app, authed_client):
    complete_profile(authed_client)
    create(authed_client)
    html = authed_client.get('/dashboard?view=today').get_data(as_text=True)
    assert '<p class="recommendation-reason">' in html
    assert html.count('<li>assignment has not been started</li>') == 1
    assert "Today's tasks" in html
    assert 'No tasks due or planned today.' in html


def test_project_progress_does_not_depend_on_tracking(app, authed_client):
    complete_profile(authed_client)
    create(authed_client)
    with app.app_context():
        parent = Task.query.one()
        parent_id = parent.id
        children = [Task(student_profile_id=parent.student_profile_id, parent=parent,
                         title=f'Step {i}', due_at=parent.due_at, estimated_minutes=15) for i in range(2)]
        db.session.add_all(children)
        db.session.commit()
        child_id = children[0].id
    authed_client.post('/settings', data={'time_tracking_enabled': 'no'})
    authed_client.post(f'/tasks/{child_id}/start')
    with app.app_context():
        parent = db.session.get(Task, parent_id)
        assert parent.status == 'in_progress' and parent.started_at is None
    authed_client.post(f'/tasks/{child_id}/complete')
    with app.app_context():
        parent = db.session.get(Task, parent_id)
        assert parent.status == 'in_progress' and parent.progress == 50
