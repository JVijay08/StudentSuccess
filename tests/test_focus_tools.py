from extensions import db
from models import Task
from tests.test_ai_planning import ready, token


def test_micro_start_records_start_once_and_consumes_open_request(app,ready):
    client,tid=ready
    response=client.post(f'/tasks/{tid}/start',data={'csrf_token':token(client),'focus_minutes':'5'})
    assert response.status_code==302 and response.location.endswith('/dashboard')
    with client.session_transaction() as state:
        assert state['focus_starter']['task_id']==tid and state['focus_starter']['minutes']==5
    with app.app_context():
        task=db.session.get(Task,tid)
        assert task.status=='in_progress' and task.actual_minutes is None
        started=task.started_at
    assert b'focus-dialog' in client.get('/dashboard').data
    with client.session_transaction() as state: assert 'focus_starter' not in state
    client.post(f'/tasks/{tid}/start',data={'csrf_token':token(client),'focus_minutes':'5'})
    with app.app_context(): assert db.session.get(Task,tid).started_at==started


def test_micro_start_cannot_start_someone_elses_task(app,ready):
    client,tid=ready
    other=app.test_client();other.post('/demo')
    response=other.post(f'/tasks/{tid}/start',data={'csrf_token':token(other),'focus_minutes':'5'})
    assert response.status_code==404
    with other.session_transaction() as state:assert 'focus_starter' not in state
    with app.app_context():assert db.session.get(Task,tid).status=='not_started'
