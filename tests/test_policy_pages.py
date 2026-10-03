from datetime import datetime, timedelta, timezone
from extensions import db
from models import User, Task, StudentProfile, UserSettings, TermCourse, AIDraft, AIQuota, AccountAgreement
from tests.account_helpers import register, create, csrf, PASSWORD


def test_notices_public_and_available_during_onboarding(app):
    client = app.test_client()
    paths = ['/privacy', '/terms-of-service', '/cookies', '/data-deletion', '/accessibility']
    for path in paths:
        response = client.get(path)
        assert response.status_code == 200
        assert b'Policies and support' in response.data
    register(client)
    for path in paths:
        assert client.get(path).status_code == 200
    assert b'not a monitored address' in client.get('/privacy').data
    assert b'Georgia, United States' in client.get('/privacy').data
    assert client.get('/dashboard').status_code == 302  # Onboarding still enforced.


def test_signup_acknowledgment_is_required_and_recorded(app):
    client = app.test_client()
    _, response = register(client, understood='')
    assert response.status_code == 400
    with app.app_context():
        assert User.query.count() == 0
        assert AccountAgreement.query.count() == 0
    register(client)
    with app.app_context():
        record = AccountAgreement.query.one()
        assert record.version == '2026-10-03'
        assert record.accepted_at
        assert record.user_id == User.query.one().id


def test_deletion_requires_owner_password_and_clears_related_data(app):
    client = app.test_client()
    create(client)
    with app.app_context():
        user = User.query.one()
        uid = user.id
        task = Task(student_profile_id=user.profile.id, title='Sample work', subject='Math',
                    due_at=datetime.now(timezone.utc), estimated_minutes=20,
                    difficulty='medium', interest_level='medium', status='not_started')
        db.session.add(task)
        db.session.flush()
        db.session.add(AIDraft(id='sample', user_id=uid, task_id=task.id, snapshot='sample',
                              steps=[{'title': 'Read', 'minutes': 20}],
                              expires_at=datetime.now(timezone.utc) + timedelta(minutes=30)))
        db.session.add(AIQuota(key=f'day:2026-10-03:user:{uid}', used=1))
        db.session.add(AIQuota(key='day:2026-10-03:global', used=1))
        db.session.commit()
    assert client.post('/settings/delete-account', data={'password': PASSWORD}).status_code == 400
    token = csrf(client)
    client.post('/settings/delete-account', data={'password': 'wrong', 'csrf_token': token})
    with app.app_context():
        assert User.query.count() == 1
    response = client.post('/settings/delete-account', data={'password': PASSWORD, 'csrf_token': token})
    assert response.status_code == 302
    with app.app_context():
        for model in (User, Task, StudentProfile, UserSettings, TermCourse, AIDraft, AccountAgreement):
            assert model.query.count() == 0, model
        assert AIQuota.query.filter(AIQuota.key.like(f'%:user:{uid}')).count() == 0
        assert AIQuota.query.filter_by(key='day:2026-10-03:global').count() == 1
    with client.session_transaction() as session:
        assert 'user_id' not in session


def test_clear_history_protects_against_cross_site_submissions(app):
    client = app.test_client()
    create(client)
    assert client.post('/settings/clear-history').status_code == 400
    assert client.post('/settings/clear-history', data={'csrf_token': csrf(client)}).status_code == 302
