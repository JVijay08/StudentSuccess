import secrets

import pytest
from extensions import db
from models import AccessCredential, StudentProfile, User, UserSettings
from services.access_service import code_digest
from services.auth_service import hash_password, check_password
from tests.account_helpers import PASSWORD, csrf, register, setup, create, login


def test_registration_stores_hash_and_no_identity(app):
    client = app.test_client()
    credentials, response = register(client, 'Study-owl')
    assert response.location == '/onboarding'
    assert response.headers['Cache-Control'] == 'no-store'
    with app.app_context():
        user = User.query.one()
        assert user.username == 'study-owl'
        assert user.email is None and user.access_credential is None
        assert not user.onboarding_completed
        assert user.password_hash != PASSWORD and check_password(PASSWORD, user.password_hash)
        assert StudentProfile.query.one().first_name == 'Planner'
    with client.session_transaction() as session:
        assert PASSWORD not in str(dict(session))
    html = client.get('/onboarding').data
    assert b'first_name' not in html and b'name="email"' not in html
    assert b'Cancel' not in html and b'Finish setup' in html


@pytest.mark.parametrize('extra', [dict(username='ab'), dict(username='person@example.com'),
    dict(username='demo-student'), dict(password='too short', confirm_password='too short'),
    dict(password='x'*129, confirm_password='x'*129), dict(confirm_password='different'), dict(understood='')])
def test_registration_rejects_invalid_credentials(app, extra):
    client = app.test_client()
    _, response = register(client, **extra)
    assert response.status_code == 400
    with app.app_context():
        assert User.query.count() == 0


def test_csrf_and_duplicate_username(app):
    client = app.test_client()
    assert client.post('/register', data={'username':'learner'}).status_code == 400
    assert client.post('/login', data={'username':'learner'}).status_code == 400
    register(client, 'unique-user')
    other = app.test_client()
    _, response = register(other, 'UNIQUE-USER')
    assert response.status_code == 400 and b'unavailable' in response.data
    assert PASSWORD.encode() not in response.data


@pytest.mark.parametrize('path', ['/dashboard','/tasks','/courses','/courses/plan','/college-courses',
    '/settings','/settings/export','/profile','/updates','/'])
def test_unfinished_accounts_cannot_open_workspace(app, path):
    client = app.test_client()
    register(client)
    assert client.get(path).location == '/onboarding'
    with client.session_transaction() as session:
        session['onboarding_completed'] = True
    assert client.post(path).location == '/onboarding'


def test_gate_survives_logout_and_other_devices(app):
    first = app.test_client()
    credentials, _ = register(first)
    first.post('/logout')
    assert login(first, credentials).location == '/onboarding'
    other = app.test_client()
    assert login(other, credentials).location == '/onboarding'
    assert setup(first).location == '/dashboard'
    assert other.get('/dashboard').status_code == 200
    first.post('/logout')
    assert login(first, credentials).location == '/dashboard'


@pytest.mark.parametrize('extra', [dict(nonpersonal_confirmed=''), dict(study_hours='nan'),
    dict(study_hours='81'), dict(grade='13'), dict(timezone_name='fake/zone'),
    dict(academic_context='unknown'), dict(theme='purple'), dict(default_task_minutes='999'),
    dict(academic_context='college',term_credit_goal='inf')])
def test_invalid_setup_never_unlocks_account(app, extra):
    client = app.test_client()
    register(client)
    assert setup(client, **extra).status_code == 200
    with app.app_context():
        assert not User.query.one().onboarding_completed
    assert client.get('/tasks').location == '/onboarding'


def test_setup_persists_choices_and_preserves_college_details(app):
    client = app.test_client()
    register(client)
    assert setup(client, academic_context='college',college_program='Biology',college_term='Fall 2026',
        term_credit_goal='0',study_hours='24',default_task_minutes='90',work_session_minutes='45',
        theme='dark',text_scale='150',dashboard_mode='focus',preferences_submitted='yes',reduce_motion='on').status_code == 302
    html = client.get('/onboarding').data
    assert b'value="0.0"' in html
    setup(client)
    with app.app_context():
        prefs = UserSettings.query.one()
        assert prefs.academic_context == 'high_school'
        assert prefs.college_program == 'Biology' and prefs.college_term == 'Fall 2026'
        assert prefs.default_task_minutes == 90 and prefs.work_session_minutes == 45
        assert prefs.reduce_motion and not prefs.reminders_enabled
        assert prefs.theme == 'dark' and prefs.text_scale == 150


@pytest.mark.parametrize('path', ['/access/create','/access/open','/access/replace','/account/login',
    '/account/signup','/account/forgot-password','/account/upgrade','/account/confirm/unused'])
def test_old_auth_endpoints_are_removed(app, path):
    client = app.test_client()
    assert client.get(path).status_code == 404
    assert client.post(path).status_code == 404
    html = client.get('/login').data
    assert b'name="username"' in html and b'name="password"' in html
    assert b'name="email"' not in html and b'name="access_code"' not in html


def test_login_has_generic_errors_and_rate_limit(app):
    client = app.test_client()
    token = csrf(client)
    for _ in range(10):
        response = client.post('/login',data={'username':'unknown','password':PASSWORD,'csrf_token':token})
        assert response.status_code == 400
        assert b'Username or password was not recognized.' in response.data
    assert client.post('/login',data={'username':'unknown','password':PASSWORD,'csrf_token':token}).status_code == 429


def legacy_user(app):
    code = 'SS-' + secrets.token_urlsafe(32)
    with app.app_context():
        user = User(username='private-legacy',password_hash=hash_password(secrets.token_urlsafe(32)))
        user.profile = StudentProfile(first_name='Saved planner',grade=12,graduation_year=2027,
            current_gpa=3,target_gpa=4,study_hours_per_week=15)
        user.access_credential = AccessCredential(digest=code_digest(code))
        db.session.add(user)
        db.session.commit()
        return user.id, code


def test_one_time_transfer_preserves_planner_and_revokes_old_access(app):
    identifier, code = legacy_user(app)
    stale = app.test_client()
    with stale.session_transaction() as session:
        session['user_id'],session['access_version'],session['auth_version'] = identifier,1,0
    assert stale.get('/dashboard').location == '/transfer-planner'
    client = app.test_client()
    form = dict(previous_access=code,username='new-learner',password=PASSWORD,confirm_password=PASSWORD)
    assert client.post('/transfer-planner',data=form).status_code == 400
    response = client.post('/transfer-planner',data={**form,'csrf_token':csrf(client,'/transfer-planner')})
    assert response.location == '/onboarding'
    with app.app_context():
        user = User.query.one()
        assert user.id == identifier and user.username == 'new-learner'
        assert user.profile.first_name == 'Saved planner' and user.profile.grade == 12
        assert AccessCredential.query.count() == 0 and user.auth_version == 1
    assert stale.get('/dashboard').location == '/login'
    assert stale.post('/transfer-planner',data={**form,'csrf_token':csrf(stale,'/transfer-planner')}).status_code == 400
    assert setup(client).status_code == 302
    with app.app_context():
        assert User.query.one().profile.first_name == 'Saved planner'


def test_bad_transfer_and_username_collision_leave_existing_account_intact(app):
    identifier, code = legacy_user(app)
    other = app.test_client()
    create(other)
    with app.app_context():
        taken = User.query.filter(User.id != identifier).one().username
    client = app.test_client()
    token = csrf(client,'/transfer-planner')
    form = dict(username=taken,password=PASSWORD,confirm_password=PASSWORD,csrf_token=token)
    assert client.post('/transfer-planner',data={**form,'previous_access':'wrong'}).status_code == 400
    assert client.post('/transfer-planner',data={**form,'previous_access':code}).status_code == 400
    with app.app_context():
        assert db.session.get(User,identifier).username == 'private-legacy'
        assert AccessCredential.query.count() == 1


def test_password_change_revokes_other_sessions(app):
    client = app.test_client()
    credentials, _ = create(client)
    other = app.test_client()
    login(other,credentials)
    new = 'four brand new notebook pages'
    response = client.post('/settings/password',data={'current_password':PASSWORD,'new_password':new,'csrf_token':csrf(client)})
    assert response.status_code == 302
    assert client.get('/dashboard').status_code == 200
    assert other.get('/dashboard').location == '/login'
    client.post('/logout')
    assert login(client,credentials).status_code == 400
    assert login(client,{**credentials,'password':new}).location == '/dashboard'


def test_existing_mixed_case_username_can_finish_setup(app):
    with app.app_context():
        user = User(username='StudyOwl',password_hash=hash_password(PASSWORD))
        user.username = 'StudyOwl'  # Simulate a row predating normalization.
        db.session.add(user)
        db.session.commit()
    client = app.test_client()
    assert login(client,dict(username='StudyOwl',password=PASSWORD)).location == '/onboarding'
    assert setup(client).location == '/dashboard'
