from datetime import datetime, timezone, timedelta
from tests.conftest import TEST_USERNAME, TEST_PASSWORD
from models import User
from extensions import db


def age_session(client, days):
    with client.session_transaction() as state:
        state['_last_active'] = (datetime.now(timezone.utc)-timedelta(days=days)).isoformat()


def remember_login(client):
    client.post('/logout')
    from tests.account_helpers import csrf
    response = client.post('/login', data={'username':TEST_USERNAME,'password':TEST_PASSWORD,'remember_device':'yes','csrf_token':csrf(client)})
    assert response.status_code == 302
    with client.session_transaction() as state:
        assert state.get('remember_device') is True
    return response


def test_remember_survives_inactivity_and_expires(authed_client):
    response=remember_login(authed_client)
    assert 'Expires=' in response.headers.get('Set-Cookie','')
    age_session(authed_client, 7)
    assert authed_client.get('/settings').status_code == 200
    age_session(authed_client, 31)
    assert '/login' in authed_client.get('/settings').location


def test_normal_session_still_expires(authed_client):
    age_session(authed_client, 1)
    assert '/login' in authed_client.get('/settings').location


def test_setting_supports_thirty_days_and_shorter_override(authed_client):
    remember_login(authed_client)
    authed_client.post('/settings',data={'session_timeout_minutes':'43200'})
    age_session(authed_client, 14)
    assert authed_client.get('/settings').status_code == 200
    authed_client.post('/settings',data={'session_timeout_minutes':'30'})
    age_session(authed_client, 1)
    assert '/login' in authed_client.get('/settings').location


def test_remember_does_not_bypass_password_revocation(app,authed_client):
    remember_login(authed_client)
    with app.app_context():
        user=db.session.get(User, authed_client.user_id)
        user.auth_version += 1
        db.session.commit()
    assert '/login' in authed_client.get('/settings').location


def test_logout_clears_remember_device(authed_client):
    remember_login(authed_client)
    authed_client.post('/logout')
    with authed_client.session_transaction() as state:
        assert not state.get('remember_device')
        assert not state.get('user_id')
