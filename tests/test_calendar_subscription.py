import re
from datetime import datetime, timezone
from extensions import db
from models import CalendarSubscription, User, Task, StudentProfile
from tests.test_course_routes import complete_profile


def create_link(client):
    response = client.post('/calendar/subscription')
    assert response.status_code == 200
    return re.search(rb'/calendar/feed/[A-Za-z0-9_-]+\.ics', response.data).group().decode()


def test_feed_rotation_revoke_and_ownership(app, authed_client):
    complete_profile(authed_client)
    with app.app_context():
        profile = StudentProfile.query.filter_by(user_id=authed_client.user_id).first()
        task = Task(student_profile_id=profile.id, title='Test, deadline', estimated_minutes=30, due_at=datetime(2026,10,20,tzinfo=timezone.utc))
        db.session.add(task)
        db.session.commit()
        task_id = task.id
    path = create_link(authed_client)
    anonymous = app.test_client()
    response = anonymous.get(path)
    assert response.status_code == 200
    assert b'Test\\, deadline' in response.data
    assert response.headers['Cache-Control'] == 'no-store'
    with app.app_context():
        subscription = db.session.get(CalendarSubscription, authed_client.user_id)
        assert len(subscription.token_hash) == 64
        assert subscription.token_hash not in path
        task = db.session.get(Task, task_id)
        task.title = 'Updated deadline'
        db.session.commit()
    assert b'Updated deadline' in anonymous.get(path).data
    with app.app_context():
        db.session.get(Task, task_id).status = 'completed'
        db.session.commit()
    assert b'BEGIN:VEVENT' not in anonymous.get(path).data
    replacement = create_link(authed_client)
    assert anonymous.get(path).status_code == 404
    assert anonymous.get(replacement).status_code == 200
    authed_client.post('/calendar/subscription/revoke')
    assert anonymous.get(replacement).status_code == 404


def test_password_change_and_export_disable_revoke(app, authed_client):
    path = create_link(authed_client)
    with app.app_context():
        db.session.get(User, authed_client.user_id).auth_version += 1
        db.session.commit()
    assert app.test_client().get(path).status_code == 404


def test_disable_export_and_delete_account(app, authed_client):
    path = create_link(authed_client)
    authed_client.post('/settings', data={'timezone_name':'America/New_York'})
    assert app.test_client().get(path).status_code == 404
    with app.app_context():
        assert db.session.get(CalendarSubscription, authed_client.user_id) is None
        db.session.get(User, authed_client.user_id).settings.calendar_export_enabled = True
        db.session.commit()
    path = create_link(authed_client)
    with app.app_context():
        db.session.delete(db.session.get(User, authed_client.user_id))
        db.session.commit()
        assert CalendarSubscription.query.count() == 0
    assert app.test_client().get(path).status_code == 404


def test_feed_rejects_bad_tokens_and_requires_login_to_create(app):
    client = app.test_client()
    assert client.get('/calendar/feed/invalid.ics').status_code == 404
    assert client.post('/calendar/subscription').status_code in (302,400)


def test_subscription_does_not_leak_other_accounts(app, authed_client):
    complete_profile(authed_client)
    from services.auth_service import hash_password
    with app.app_context():
        other = User(username='otherstudent',password_hash=hash_password('other-password'))
        db.session.add(other)
        db.session.flush()
        from tests.test_settings import add_profile
        profile = add_profile(other.id)
        db.session.add(Task(student_profile_id=profile.id,title='Other account secret',estimated_minutes=10,due_at=datetime.now(timezone.utc)))
        db.session.commit()
    path = create_link(authed_client)
    assert b'Other account secret' not in app.test_client().get(path).data


def test_settings_reject_invalid_timezone_without_partial_save(app, authed_client):
    authed_client.get('/settings')
    with app.app_context():
        original = db.session.get(User,authed_client.user_id).settings.theme
    authed_client.post('/settings',data={'theme':'dark','timezone_name':'Invalid/Zone'})
    with app.app_context():
        assert db.session.get(User,authed_client.user_id).settings.theme == original
