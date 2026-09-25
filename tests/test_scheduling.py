from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from extensions import db
from models import Task
from services.scheduling import planned_time
from services.task_policy import utc
from tests.test_access_codes import csrf
from tests.test_course_routes import complete_profile


def add_task(client):
    complete_profile(client)
    client.post('/tasks', data=dict(title='Schedule me',due_at='2027-12-10',estimated_minutes='30',nonpersonal_confirmed='yes'))


def test_quick_times_follow_planner_timezone_and_dst():
    now = datetime(2026, 3, 7, 18, tzinfo=timezone.utc)
    tomorrow = planned_time({'schedule_choice':'tomorrow'},'America/New_York',now)
    assert tomorrow.astimezone(ZoneInfo('America/New_York')).hour == 9
    assert tomorrow == datetime(2026, 3, 8, 13, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        planned_time({'planned_start_at':'2026-03-08T02:30'},'America/New_York',now)
    assert planned_time({'schedule_choice':'clear'},'America/New_York',now) is None


def test_reschedule_undo_keeps_deadline_and_start_history(app,authed_client):
    add_task(authed_client)
    with app.app_context():
        task=Task.query.one()
        identifier,due=task.id,task.due_at
    assert authed_client.post(f'/tasks/{identifier}/reschedule',data={'schedule_choice':'hour'}).status_code==400
    data={'csrf_token':csrf(authed_client),'schedule_choice':'hour'}
    assert authed_client.post(f'/tasks/{identifier}/reschedule',data=data).status_code==302
    with app.app_context():
        task=db.session.get(Task,identifier)
        assert task.due_at==due and task.started_at is None
        assert utc(task.planned_start_at)>datetime.now(timezone.utc)
    authed_client.post('/tasks/undo-schedule',data={'csrf_token':csrf(authed_client)})
    with app.app_context():
        task=db.session.get(Task,identifier)
        assert task.planned_start_at is None and task.due_at==due


def test_undo_does_not_overwrite_later_changes(app,authed_client):
    add_task(authed_client)
    with app.app_context(): identifier=Task.query.one().id
    authed_client.post(f'/tasks/{identifier}/reschedule',data={'csrf_token':csrf(authed_client),'schedule_choice':'tomorrow'})
    authed_client.post(f'/tasks/{identifier}/start')
    response=authed_client.post('/tasks/undo-schedule',data={'csrf_token':csrf(authed_client)},follow_redirects=True)
    assert b'latest changes have been kept' in response.data
    with app.app_context():
        task=db.session.get(Task,identifier)
        assert task.status=='in_progress' and task.planned_start_at is not None


def test_completed_tasks_cannot_be_rescheduled(app,authed_client):
    add_task(authed_client)
    with app.app_context(): identifier=Task.query.one().id
    authed_client.post(f'/tasks/{identifier}/complete')
    authed_client.post(f'/tasks/{identifier}/reschedule',data={'csrf_token':csrf(authed_client),'schedule_choice':'tomorrow'})
    with app.app_context(): assert db.session.get(Task,identifier).planned_start_at is None
