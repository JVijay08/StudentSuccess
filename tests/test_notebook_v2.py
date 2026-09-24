from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from extensions import db
from models import Task
from models.term_course import TermCourse
from services.timing_service import timing_summary
from tests.test_course_routes import complete_profile
from tests.test_feedback_overhaul import create


def test_early_starts_do_not_cancel_lateness():
    now = datetime(2026, 9, 23, tzinfo=timezone.utc)
    tasks = [SimpleNamespace(id=index, title='Example', subject='Science', task_type='',
        status='completed', children=[], completed_at=now, due_at=now,
        planned_start_at=now, started_at=now+timedelta(minutes=minutes),
        estimated_minutes=60, actual_minutes=30)
        for index, minutes in enumerate([-60, 60, 0], 1)]
    summary = timing_summary(tasks)
    assert summary['on_time'] == 67
    assert summary['on_time_count'] == 2
    assert summary['average_lateness'] == '20 min late'
    assert summary['median_lateness'] == 'On time'
    assert summary['average'] == 'On time'  # Raw signed data remains available.


def test_course_tree_preserves_parent_and_hides_completed_children(app, authed_client):
    complete_profile(authed_client)
    create(authed_client, title='Lab report', subject='Biology', estimated_minutes='40')
    with app.app_context():
        parent = Task.query.one()
        parent_id = parent.id
    authed_client.post(f'/tasks/{parent_id}/split')
    with app.app_context():
        first = Task.query.filter_by(parent_task_id=parent_id).order_by(Task.id).first().id
    authed_client.post(f'/tasks/{first}/complete', data={'actual_minutes':'25'})
    body = authed_client.get('/tasks?view=courses').get_data(as_text=True)
    active = body.split('id="completed-tasks"')[0]
    assert 'Lab report' in active and '50% complete' in active
    assert 'Work block 2' in active
    assert 'Work block 1' not in active
    assert 'Work block 1' in body.split('id="completed-tasks"')[1]
    assert 'subtask-branch' in active


def test_course_grouping_normalizes_names_and_excludes_other_accounts(app, authed_client):
    complete_profile(authed_client)
    create(authed_client, title='One', subject='Biology')
    create(authed_client, title='Two', subject=' biology ')
    with app.app_context():
        db.session.add(TermCourse(user_id=authed_client.user_id, title='Biology', term='Fall', weekly_hours=4))
        db.session.commit()
    body = authed_client.get('/tasks?view=courses&course=BIOLOGY').get_data(as_text=True)
    assert body.count('class="course-task-group"') == 1
    assert '2 active steps' in body
    assert 'One' in body and 'Two' in body
    anonymous = app.test_client().get('/tasks?view=courses')
    assert anonymous.status_code == 302


def test_empty_college_course_links_to_prefilled_assignment(app, authed_client):
    complete_profile(authed_client)
    authed_client.post('/terms', data={'title':'BIO 101', 'term':'Fall 2026', 'weekly_hours':'4', 'nonpersonal_confirmed':'yes'})
    plan = authed_client.get('/terms').get_data(as_text=True)
    assert 'Assignments &amp; subtasks' in plan
    body = authed_client.get('/tasks?view=courses&course=BIO+101').get_data(as_text=True)
    assert 'No assignments yet' in body
    assert 'value="BIO 101"' in body


def test_timing_headline_does_not_label_early_as_a_problem(app, authed_client):
    complete_profile(authed_client)
    body = authed_client.get('/dashboard?view=full').get_data(as_text=True)
    assert 'On-time starts' in body and 'Average lateness' in body
    assert 'Average start delay</dt>' not in body
