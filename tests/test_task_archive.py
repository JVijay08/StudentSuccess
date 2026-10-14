from datetime import datetime, timedelta, timezone
from extensions import db
from models import Task, StudentProfile
from tests.test_course_routes import complete_profile


def test_completed_archive_pagination_search_and_bounds(app, authed_client):
    complete_profile(authed_client)
    with app.app_context():
        profile=StudentProfile.query.filter_by(user_id=authed_client.user_id).one()
        now=datetime.now(timezone.utc)
        for index in range(25):
            db.session.add(Task(student_profile_id=profile.id,title=f'Archive item {index:02}',subject='Chemistry' if index==0 else 'Math',due_at=now,completed_at=now+timedelta(minutes=index),estimated_minutes=30,difficulty='medium',interest_level='medium',status='completed'))
        db.session.commit()
    page=authed_client.get('/tasks').data
    assert page.count(b'class="archive-row"') == 10
    assert b'Archive item 24' in page and b'Archive item 00' not in page
    assert b'25 of 25 tasks and steps completed' in page
    assert b'Actual Not recorded' not in page
    page=authed_client.get('/tasks?history_page=2').data
    assert page.count(b'class="archive-row"') == 10
    assert b'Archive item 14' in page and b'Archive item 24' not in page
    page=authed_client.get('/tasks?history_page=999').data
    assert page.count(b'class="archive-row"') == 5
    assert b'Page 3 of 3' in page
    page=authed_client.get('/tasks?history_q=Chemistry').data
    assert page.count(b'class="archive-row"') == 1
    assert b'Archive item 00' in page
    assert b'No matching completed tasks.' in authed_client.get('/tasks?history_q=missing').data
    assert authed_client.get('/tasks?history_page=invalid').status_code == 200
