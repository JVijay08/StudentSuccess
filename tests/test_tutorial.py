import re
from models import User, Task
from extensions import db
from routes.tutorial_routes import STEPS


def token(client, path='/'):
    html=client.get(path).get_data(as_text=True)
    return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)


def test_tutorial_isolated_navigation_and_cleanup(app):
    client=app.test_client()
    assert client.post('/tutorial/start').status_code == 400
    response=client.post('/tutorial/start',data={'csrf_token':token(client)},follow_redirects=True)
    assert response.status_code==200 and b'Welcome to your practice planner' in response.data
    with client.session_transaction() as state:
        practice_id=state['user_id']
        practice_task=state['tutorial_task']
    for index in range(len(STEPS)):
        response=client.post('/tutorial/step',data={'csrf_token':token(client,'/dashboard'),'step':index},follow_redirects=True)
        assert response.status_code==200, (index,response.status_code)
        assert STEPS[index][0].encode() in response.data
    response=client.post('/tutorial/step',data={'csrf_token':token(client,'/dashboard'),'step':999})
    assert response.status_code==400
    response=client.post('/tutorial/finish',data={'csrf_token':token(client,'/dashboard')},follow_redirects=True)
    assert response.status_code==200 and b'Create an account' in response.data
    with app.app_context():
        assert db.session.get(User,practice_id) is None
        assert db.session.get(Task,practice_task) is None


def test_tutorial_restores_original_account(app,authed_client):
    client=authed_client
    original=client.user_id
    client.post('/tutorial/start',data={'csrf_token':token(client,'/settings')})
    with client.session_transaction() as state:
        assert state['user_id'] != original
        sample=state['user_id']
    client.post('/tutorial/step',data={'csrf_token':token(client,'/dashboard'),'step':10})
    with app.app_context():
        real=db.session.get(User,original)
        assert real.settings is None or real.settings.academic_context != 'college'
    client.post('/tutorial/finish',data={'csrf_token':token(client,'/dashboard')})
    with client.session_transaction() as state:
        assert state['user_id']==original
        assert 'tutorial_mode' not in state
    with app.app_context():
        assert db.session.get(User,sample) is None
        assert db.session.get(User,original) is not None


def test_regular_account_cannot_advance_or_delete_as_tutorial(authed_client):
    csrf=token(authed_client,'/settings')
    assert authed_client.post('/tutorial/step',data={'csrf_token':csrf,'step':1}).status_code==403
    assert authed_client.post('/tutorial/finish',data={'csrf_token':csrf}).status_code==403


def test_revoked_account_is_not_restored(app,authed_client):
    client=authed_client
    client.post('/tutorial/start',data={'csrf_token':token(client,'/settings')})
    with app.app_context():
        db.session.get(User,client.user_id).auth_version += 1
        db.session.commit()
    response=client.post('/tutorial/finish',data={'csrf_token':token(client,'/dashboard')})
    assert response.location.endswith('/tutorial/finished')
    with client.session_transaction() as state:
        assert 'user_id' not in state


def test_restart_and_practice_account_delete_preserve_return(app,authed_client):
    client=authed_client
    client.post('/tutorial/start',data={'csrf_token':token(client,'/settings')})
    with client.session_transaction() as state:
        first=state['user_id']
    client.post('/tutorial/start',data={'csrf_token':token(client,'/dashboard')})
    with app.app_context():
        # SQLite may reuse the deleted highest ID; there is still only one practice account.
        assert User.query.filter(User.username.startswith('demo-')).count()==1
    client.post('/settings/delete-account',data={'csrf_token':token(client,'/settings')})
    with client.session_transaction() as state:
        assert state['user_id']==client.user_id
    with app.app_context():
        assert User.query.filter(User.username.startswith('demo-')).count()==0
