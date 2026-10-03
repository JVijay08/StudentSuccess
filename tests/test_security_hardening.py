import io
import pytest
from flask.testing import FlaskClient
from models import User, Task
from services.ai_planning import validate_steps
from tests.account_helpers import create, csrf, login, PASSWORD


def raw_client(app):
    # Deliberately bypass the form-token adapter used by older route tests.
    return FlaskClient(app, app.response_class)


def test_every_registered_post_rejects_missing_csrf(app):
    client = raw_client(app)
    create(client)
    paths = []
    for rule in app.url_map.iter_rules():
        if 'POST' not in rule.methods:
            continue
        values = {name: 1 if converter.__class__.__name__ == 'IntegerConverter' else 'sample'
                  for name, converter in rule._converters.items()}
        with app.test_request_context():
            from flask import url_for
            path = url_for(rule.endpoint, **values)
        response = client.post(path)
        assert response.status_code == 400, (path, response.status_code)
        paths.append(path)
    assert len(paths) >= 25


def test_form_and_header_tokens_work_and_rotation_revokes_old_tokens(app):
    client = raw_client(app)
    credentials, _ = create(client)
    other = raw_client(app)
    login(other, credentials)
    token = csrf(client, '/settings')
    assert client.post('/session/extend', headers={'X-CSRF-Token': token}).status_code == 200
    response = client.post('/settings/password', data={
        'csrf_token': token, 'current_password': PASSWORD, 'new_password': 'changed sample password'})
    assert response.status_code == 302
    with client.session_transaction() as state:
        assert state['access_csrf'] != token
        assert state['auth_version'] == 1
    assert other.get('/dashboard').status_code == 302
    assert client.post('/session/extend', headers={'X-CSRF-Token': token}).status_code == 400
    assert client.get('/settings').status_code == 200


def test_ics_allowlist_and_real_content_validation(app):
    client = raw_client(app)
    create(client)
    token = csrf(client)
    content = b'BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nSUMMARY:Sample assignment\r\nDTSTART:20271101T160000Z\r\nEND:VEVENT\r\nEND:VCALENDAR'
    for filename, mime, data in [('work.exe', 'text/calendar', content),
                                 ('work.ics', 'text/html', content),
                                 ('work.ics', 'text/calendar', b'<script>invalid</script>')]:
        response = client.post('/tasks/import', data={'csrf_token': token, 'nonpersonal_confirmed': 'yes',
            'calendar': (io.BytesIO(data), filename, mime)})
        assert b'Could not import' in response.data
    response = client.post('/tasks/import', data={'csrf_token': token, 'nonpersonal_confirmed': 'yes',
        'calendar': (io.BytesIO(content), 'work.ics', 'text/calendar')})
    assert b'Sample assignment' in response.data and b'Could not import' not in response.data
    with app.app_context():
        assert Task.query.count() == 0  # A valid upload still needs review.


def test_plain_text_is_escaped_not_executed_and_controls_rejected(app):
    client = raw_client(app)
    create(client)
    form = {'csrf_token': csrf(client), 'title': '<script>alert(1)</script>',
            'due_at': '2027-11-01', 'estimated_minutes': '20'}
    assert client.post('/tasks', data=form).status_code == 302
    response = client.get('/tasks')
    assert b'&lt;script&gt;alert(1)&lt;/script&gt;' in response.data
    assert b'<script>alert(1)</script>' not in response.data
    client.post('/tasks', data={**form, 'title': 'Invalid\x00title'})
    with app.app_context():
        assert Task.query.count() == 1


@pytest.mark.parametrize('title', ['Visit https://attacker.example', '<script>run()</script>',
                                  'javascript:alert(1)', 'Open www.attacker.example'])
def test_ai_links_and_markup_cannot_be_applied(title):
    with pytest.raises(ValueError):
        validate_steps([{'title': title, 'minutes': 10}], 30)


def test_security_events_never_include_submitted_credentials(app, caplog):
    client = raw_client(app)
    token = csrf(client)
    client.post('/login', data={'csrf_token': token, 'username': 'secret-input-marker',
                               'password': 'do-not-log-this-password'})
    assert 'login_failed' in caplog.text
    assert 'secret-input-marker' not in caplog.text
    assert 'do-not-log-this-password' not in caplog.text
    assert token not in caplog.text


def test_headers_and_unavailable_routes(app):
    app.config['SESSION_COOKIE_SECURE'] = True
    client = raw_client(app)
    response = client.get('/login', base_url='https://localhost')
    assert response.headers['Strict-Transport-Security'] == 'max-age=31536000'
    cookie = response.headers['Set-Cookie']
    assert 'Secure;' in cookie and 'HttpOnly;' in cookie and 'SameSite=Lax' in cookie
    assert 'Access-Control-Allow-Origin' not in response.headers
    for path in ['/admin', '/static/', '/forgot-password', '/reset-password', '/account/reset']:
        assert client.get(path).status_code == 404
    response = client.options('/tasks', headers={'Origin': 'https://attacker.example',
        'Access-Control-Request-Method': 'POST'})
    assert 'Access-Control-Allow-Origin' not in response.headers


def test_same_generic_login_failure_for_existing_and_unknown_user(app):
    client = raw_client(app)
    credentials, _ = create(client)
    client.post('/logout', data={'csrf_token': csrf(client)})
    for username in (credentials['username'], 'not-a-real-user'):
        response = client.post('/login', data={'csrf_token': csrf(client),
            'username': username, 'password': 'wrong sample password'})
        assert response.status_code == 400
        assert b'Username or password was not recognized.' in response.data
