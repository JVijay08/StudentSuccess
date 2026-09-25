import re
from datetime import datetime, timedelta, timezone

import pytest
from extensions import db
from models import User, Task
from models.account_request import AccountRequest
from services.auth_service import check_password
from tests.test_access_codes import create, csrf, login as code_login

PASSWORD = 'three quiet study notebooks'


@pytest.fixture
def delivery(app):
    messages = []
    app.config.update(EMAIL_TEST_DELIVERY=messages.append, PUBLIC_BASE_URL='https://planner.example')
    return messages


def email_form(client, **changes):
    values = dict(csrf_token=csrf(client), email='student@example.org', password=PASSWORD,
                  confirm_password=PASSWORD, understood='yes')
    values.update(changes)
    return values


def link(messages):
    return re.search(r'/account/confirm/[^\s]+', messages[-1]['text'])[0]


def signup(client, messages):
    assert client.post('/account/signup', data=email_form(client)).status_code == 200
    path = link(messages)
    assert client.get(path).status_code == 200
    assert client.post(path, data={'csrf_token':csrf(client)}).status_code == 302
    return path


def test_email_setup_is_gated_and_existing_access_still_works(app):
    client = app.test_client()
    assert client.post('/account/signup', data=email_form(client)).status_code == 503
    with app.app_context():
        assert AccountRequest.query.count() == 0
    code, _ = create(client)
    assert code_login(app.test_client(), code).status_code == 302


def test_signup_verify_login_and_single_use(app, delivery):
    client = app.test_client()
    response = client.post('/account/signup', data=email_form(client))
    assert response.status_code == 200
    path = link(delivery)
    with app.app_context():
        assert User.query.count() == 0
        assert PASSWORD not in AccountRequest.query.one().password_hash
        assert path.split('/')[-1] != AccountRequest.query.one().digest
    assert client.get(path).status_code == 200  # scanners cannot consume links
    assert client.get(path).status_code == 200
    assert client.post(path, data={'csrf_token':csrf(client)}).status_code == 302
    assert client.post(path, data={'csrf_token':csrf(client)}).status_code == 400
    assert client.get('/onboarding').status_code == 200
    assert b'First Name' not in client.get('/onboarding').data
    other = app.test_client()
    assert other.post('/account/login', data=email_form(other, email='STUDENT@example.org')).status_code == 302
    with app.app_context():
        user = User.query.one()
        assert user.email == 'student@example.org' and check_password(PASSWORD, user.password_hash)
    assert other.get('/dashboard').status_code == 200


def test_upgrade_keeps_data_revokes_code_and_other_sessions(app, delivery):
    # Make a legacy planner before enabling email signup.
    app.config['EMAIL_TEST_DELIVERY'] = None
    client = app.test_client()
    code, _ = create(client)
    other = app.test_client()
    code_login(other, code)
    client.post('/tasks', data=dict(title='Keep this work', due_at='2027-12-01', estimated_minutes='30', nonpersonal_confirmed='yes'))
    with client.session_transaction() as session:
        original = session['user_id']
    app.config['EMAIL_TEST_DELIVERY'] = delivery.append
    assert client.post('/account/upgrade', data=email_form(client, current_access=code)).status_code == 200
    assert other.get('/tasks').status_code == 200
    path = link(delivery)
    assert client.post(path, data={'csrf_token':csrf(client)}).status_code == 302
    with app.app_context():
        assert User.query.one().id == original
        assert Task.query.one().title == 'Keep this work'
        assert User.query.one().access_credential is None
    assert other.get('/tasks').status_code == 302
    assert code_login(app.test_client(), code).status_code == 400


def test_reset_expires_tokens_and_revokes_sessions(app, delivery):
    client = app.test_client()
    signup(client, delivery)
    other = app.test_client()
    other.post('/account/login', data=email_form(other))
    response = client.post('/account/forgot-password', data=email_form(client))
    assert response.status_code == 200
    path = link(delivery)
    new = 'four different study notebooks'
    assert client.post(path, data=email_form(client, password=new, confirm_password=new)).status_code == 200
    assert other.get('/tasks').status_code == 302
    assert other.post('/account/login', data=email_form(other)).status_code == 400
    assert other.post('/account/login', data=email_form(other, password=new)).status_code == 302
    assert client.post(path, data=email_form(client, password=new, confirm_password=new)).status_code == 400


def test_expiry_csrf_failure_and_delivery_failure(app, delivery):
    client = app.test_client()
    assert client.post('/account/signup', data={'email':'a@example.org'}).status_code == 400
    client.post('/account/signup', data=email_form(client))
    path = link(delivery)
    with app.app_context():
        AccountRequest.query.one().expires_at = datetime.now(timezone.utc)-timedelta(seconds=1)
        db.session.commit()
    assert client.get(path).status_code == 400
    def fail(_message):
        raise RuntimeError('provider detail must not leak')
    app.config['EMAIL_TEST_DELIVERY'] = fail
    response = client.post('/account/signup', data=email_form(client, email='another@example.org'))
    assert response.status_code == 503 and b'provider detail' not in response.data
    with app.app_context():
        assert AccountRequest.query.count() == 0


def test_requests_are_limited_and_unknown_recovery_is_generic(app, delivery):
    client = app.test_client()
    for _ in range(5):
        assert client.post('/account/forgot-password', data=email_form(client)).status_code == 200
    assert delivery == []
    assert client.post('/account/forgot-password', data=email_form(client)).status_code == 429


def test_password_change_revokes_pending_reset_and_email_survives_delivery_outage(app, delivery):
    client = app.test_client()
    signup(client, delivery)
    client.post('/account/forgot-password', data=email_form(client))
    reset_link = link(delivery)
    new = 'another long notebook password'
    assert client.post('/settings/password', data=dict(csrf_token=csrf(client),
        current_password=PASSWORD, new_password=new)).status_code == 302
    assert client.get(reset_link).status_code == 400
    assert client.get('/settings/export').json['email'] == 'student@example.org'
    app.config['EMAIL_TEST_DELIVERY'] = None
    other = app.test_client()
    assert other.get('/account/login').status_code == 200
    assert other.post('/account/login', data=email_form(other, password=new)).status_code == 302


def test_account_deletion_removes_pending_email_requests(app, delivery):
    client = app.test_client()
    signup(client, delivery)
    client.post('/account/forgot-password', data=email_form(client))
    client.post('/settings/delete-account', data={'password':PASSWORD})
    with app.app_context():
        assert User.query.count() == 0
        assert AccountRequest.query.count() == 0
