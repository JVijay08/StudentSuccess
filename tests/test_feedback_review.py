from datetime import datetime, timedelta, timezone

from extensions import db
from models import Task, TermCourse
from services.course_service import browse_courses, load_courses, course_title_needs_review, get_catalogs, get_course_by_id, course_name_key
from tests.test_course_routes import complete_profile
from tests.test_colleges import course_data


def test_course_status_and_saved_picker(app, authed_client):
    complete_profile(authed_client)
    assert authed_client.post('/terms', data=course_data(status='in_progress')).status_code == 302
    page = authed_client.get('/tasks').get_data(as_text=True)
    assert 'name="saved_course"' in page
    assert '<option value="Introduction to Biology"' in page
    authed_client.post('/tasks', data=dict(title='Lab', saved_course='Introduction to Biology', subject='Old draft', due_at='2027-12-10', estimated_minutes='60', break_minutes='30', nonpersonal_confirmed='yes'))
    with app.app_context():
        task = Task.query.one()
        assert task.subject == 'Introduction to Biology'
        assert task.break_minutes == 30 and task.estimated_minutes == 60
        assert TermCourse.query.one().status == 'in_progress'
        identifier = task.id
    assert b'90 minutes to allow' in authed_client.get(f'/tasks/{identifier}').data


def test_task_steps_complete_and_reopen(app, authed_client):
    complete_profile(authed_client)
    authed_client.post('/tasks', data=dict(title='Essay', due_at='2027-12-10', estimated_minutes='60', nonpersonal_confirmed='yes'))
    with app.app_context():
        identifier = Task.query.one().id
    return_to = f'/tasks/{identifier}'
    authed_client.post(f'/tasks/{identifier}/subtasks', data=dict(title='Outline', estimated_minutes='20', nonpersonal_confirmed='yes', _return_to=return_to))
    with app.app_context():
        child = Task.query.filter(Task.parent_task_id == identifier).one()
        child_id = child.id
    response = authed_client.post(f'/tasks/{child_id}/complete', data={'_return_to':return_to}, follow_redirects=True)
    assert b'1 of 1 complete' in response.data
    authed_client.post(f'/tasks/{child_id}/undo-complete')
    with app.app_context():
        assert db.session.get(Task, identifier).status != 'completed'
    assert app.test_client().get(return_to).status_code == 302


def test_catalog_scope_and_quarantine(authed_client):
    complete_profile(authed_client)
    page = authed_client.get('/courses?scope=ga&catalog=ap&page=3').get_data(as_text=True)
    assert 'Personal Fitness' in page and '9th Grade Literature and Composition Honors' in page
    assert 'Page 3 of 3' in page
    assert 'name="scope"' in page and 'name="state"' not in page
    assert any(course_title_needs_review(c) for c in load_courses('ap'))
    assert not any(course_title_needs_review(c) for c in browse_courses('ap'))
    grouped = [c for c in browse_courses('ap') if c['course_id']=='AP_ENGLISH_LANGUAGE'][0]
    assert len(grouped['alternate_ids']) > 1


def test_expired_action_shows_recovery(authed_client):
    complete_profile(authed_client)
    with authed_client.session_transaction() as session:
        session['_last_active'] = (datetime.now(timezone.utc)-timedelta(days=1)).isoformat()
    response = authed_client.post('/session/extend', follow_redirects=True)
    assert b'Your session has ended' in response.data


def test_invalid_break_allowance_is_not_saved(app, authed_client):
    complete_profile(authed_client)
    response = authed_client.post('/tasks', data=dict(title='Invalid', due_at='2027-12-10', estimated_minutes='60', break_minutes='-1', nonpersonal_confirmed='yes'))
    assert b'Break allowance' in response.data
    with app.app_context():
        assert Task.query.count() == 0


def test_all_catalogs_keep_ids_but_exclude_bad_titles():
    assert not course_title_needs_review({'course_name': 'Descriptive Geometry'})
    for catalog in get_catalogs():
        visible = browse_courses(catalog)
        names = [course_name_key(c['course_name']) for c in visible]
        assert len(names) == len(set(names))
        assert all(not course_title_needs_review(c) for c in visible)
        for course in load_courses(catalog):
            assert get_course_by_id(course['course_id'], catalog) is not None
            assert len(course['display_name']) <= 180


def test_course_add_returns_to_card_and_rejects_bad_import(authed_client, app):
    from models import PlannedCourse
    complete_profile(authed_client)
    target = '/courses?scope=ga#course-GA_FCS_FITNESS'
    response = authed_client.post('/courses/plan/add/GA_FCS_FITNESS', data=dict(catalog='ga', school_year='9', _return_to=target))
    assert response.location == target
    bad = next(c for c in load_courses('ap') if c['quality_review'])
    authed_client.post('/courses/plan/add/'+bad['course_id'], data=dict(catalog='ap', school_year='9'))
    with app.app_context():
        assert PlannedCourse.query.count() == 1


def test_task_detail_rejects_other_account(app, authed_client):
    from models import User, StudentProfile
    complete_profile(authed_client)
    with app.app_context():
        other = User(username='someoneelse', password_hash='unused', onboarding_completed=True)
        db.session.add(other)
        db.session.flush()
        profile = StudentProfile(user_id=other.id, first_name='Student', grade=11, graduation_year=2028, current_gpa=3, target_gpa=3.5, study_hours_per_week=10)
        db.session.add(profile)
        db.session.flush()
        task = Task(student_profile_id=profile.id, title='Private', due_at=datetime.now(timezone.utc), estimated_minutes=30)
        db.session.add(task)
        db.session.commit()
        identifier = task.id
    assert authed_client.get(f'/tasks/{identifier}').status_code == 404
