import pytest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from extensions import db
from models import Task
from services import ai_planning as ai
from services.ai_schedule import spread
from tests.test_ai_planning import ready, token, generate, apply


def test_rough_note_missing_date_requires_review(app, ready, monkeypatch):
    client, _ = ready
    monkeypatch.setattr(ai, 'generate_assignment', lambda *args: dict(title='Study chemistry',
        subject='Chemistry', due_at=None, estimated_minutes=60,
        steps=[dict(title='Review concepts', minutes=20), dict(title='Practice and self-check', minutes=40)]))
    response = client.post('/tasks/ai/new', data=dict(csrf_token=token(client),
        description='study chemistry', autofill='yes', consent='yes'))
    assert response.status_code == 302
    url = response.location
    assert b'Confirm the deadline' in client.get(url).data
    assert b'valid due date' in apply(client, url).data
    with app.app_context(): assert Task.query.count() == 1
    response = apply(client, url, parent_title='Chemistry practice', parent_due='2027-06-01T18:30', parent_minutes='90')
    assert response.status_code == 302
    with app.app_context():
        task = Task.query.filter_by(title='Chemistry practice').one()
        assert task.estimated_minutes == 90 and task.subject == 'Chemistry'
        assert len(task.children) == 2


def test_generated_metadata_validation(monkeypatch):
    good = dict(title='Review calculus chapters 6 to 8', subject='Calculus', due_at='2027-01-08T23:59',
        estimated_minutes=90, steps=[dict(title='Solve practice problems and check mistakes',minutes=90)])
    monkeypatch.setattr(ai, '_request', lambda *a:good)
    assert ai.generate_assignment('calc next Friday', '2027-01-01')['estimated_minutes'] == 90
    for bad in [dict(good, estimated_minutes=True), dict(good, due_at='not a date'),
                dict(good, title='<script>'), dict(good, estimated_minutes=5)]:
        monkeypatch.setattr(ai, '_request', lambda *a:bad)
        with pytest.raises(ai.AIUnavailable): ai.generate_assignment('note','2027-01-01')


def test_spread_preserves_minutes_avoids_conflicts_and_deadline():
    first = datetime.now(timezone.utc).replace(second=0,microsecond=0) + timedelta(days=2)
    busy = SimpleNamespace(status='not_started', planned_start_at=first, estimated_minutes=30, children=[])
    steps = [dict(title='Research and write', minutes=120)]
    result = spread(steps, first, 60, first+timedelta(days=3), [busy], 'America/New_York')
    assert len(result)==2 and sum(s['minutes'] for s in result)==120
    assert datetime.fromisoformat(result[0]['planned_start_at']) == first+timedelta(minutes=30)
    assert datetime.fromisoformat(result[1]['planned_start_at']) == first+timedelta(days=1)
    with pytest.raises(ValueError): spread(steps, first,60,first+timedelta(minutes=20), [],'UTC')
    with pytest.raises(ValueError): spread(steps, first,10,first+timedelta(days=30), [],'UTC')


def test_schedule_preview_does_not_write_tasks_then_applies(app, ready):
    client, tid = ready
    with app.app_context():
        task=db.session.get(Task,tid)
        task.due_at=datetime.now(timezone.utc)+timedelta(days=10)
        db.session.commit()
    url=generate(client,tid).location
    first=(datetime.now(timezone.utc)+timedelta(days=2)).isoformat()
    response=apply(client,url,action='schedule',first_start=first,daily_minutes='30')
    assert response.status_code==302
    with app.app_context(): assert Task.query.count()==1
    page=client.get(url)
    assert b'session 1' in page.data
    response=apply(client,url,selected=['0','1','2'], title_0='Research',minutes_0='20',
        title_1='Draft',minutes_1='30',title_2='Self-check',minutes_2='10')
    assert response.status_code==302
    with app.app_context():
        children=Task.query.filter_by(parent_task_id=tid).all()
        assert len(children)==3 and all(t.planned_start_at for t in children)
    apply(client,url)
    with app.app_context(): assert Task.query.count()==4


def test_conflicting_reviewed_session_cannot_be_saved(app, ready):
    client, tid=ready
    with app.app_context():
        task=db.session.get(Task,tid)
        task.due_at=datetime.now(timezone.utc)+timedelta(days=10)
        db.session.commit()
    url=generate(client,tid).location
    first=(datetime.now(timezone.utc)+timedelta(days=2)).isoformat()
    response=apply(client,url,start_0=first,start_1=first)
    assert b'overlaps planned work' in response.data
    with app.app_context(): assert Task.query.count()==1


def test_autofill_requires_consent(app, ready, monkeypatch):
    client,_=ready
    monkeypatch.setattr(ai, 'generate_assignment', lambda *args:pytest.fail('No consent'))
    response=client.post('/tasks/ai/new',data=dict(csrf_token=token(client),
        description='study chemistry',autofill='yes'))
    assert b'Confirm the sharing' in response.data


def test_spread_keeps_local_hour_across_dst():
    from zoneinfo import ZoneInfo
    first=datetime(2027,3,13,17,tzinfo=ZoneInfo('America/New_York')).astimezone(timezone.utc)
    sessions=spread([dict(title='Study',minutes=120)],first,60,first+timedelta(days=3), [], 'America/New_York')
    second=datetime.fromisoformat(sessions[1]['planned_start_at'])
    assert second.astimezone(ZoneInfo('America/New_York')).hour==17
    assert second-first==timedelta(hours=23)
