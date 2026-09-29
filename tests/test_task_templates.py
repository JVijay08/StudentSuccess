from extensions import db
from models import Task
from tests.test_course_routes import complete_profile
from tests.test_feedback_overhaul import create


def test_template_prefills_without_copying_schedule_or_mutating(app,authed_client):
    complete_profile(authed_client)
    create(authed_client,title='Reusable assignment',estimated_minutes='45',subject='Math',due_time='15:30')
    with app.app_context(): identifier=Task.query.one().id
    authed_client.post(f'/tasks/{identifier}/complete')
    response=authed_client.get(f'/tasks?template={identifier}')
    assert response.status_code==200
    assert b'Template ready.' in response.data and b'value="Reusable assignment"' in response.data
    assert b'name="due_at" value=""' in response.data
    assert b'name="due_time" value=""' in response.data
    with app.app_context():
        assert Task.query.count()==1 and Task.query.one().status=='completed'


def test_template_requires_ownership(app,authed_client):
    complete_profile(authed_client);create(authed_client)
    with app.app_context():identifier=Task.query.one().id
    other=app.test_client();other.post('/demo')
    assert other.get(f'/tasks?template={identifier}').status_code==404
    assert authed_client.get('/tasks?template=9999999').status_code==404
