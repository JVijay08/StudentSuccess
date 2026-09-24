import pytest
from extensions import db
from models import TermCourse, User, UserSettings
from services.college_directory import directory, institution, search, states
from services.course_service import US_STATES
from tests.test_course_routes import complete_profile


def course_data(**changes):
    values = dict(title='Introduction to Biology', term='Fall 2027', weekly_hours='4',
        institution_id='100654', enrollment_type='dual', school_year='11', status='considering',
        course_code='BIO 101', credits='3', description='Cells and laboratory work.',
        catalog_url='https://example.edu/catalog/bio101', nonpersonal_confirmed='yes')
    values.update(changes)
    return values


def test_directory_source_coverage_and_search():
    assert directory()['release_year'] == 2024
    assert directory()['source_url'].startswith('https://nces.ed.gov/')
    assert len(directory()['institutions']) == 5994
    assert len(states()) >= 51
    assert set(US_STATES) <= set(states())
    assert institution('100654')['state'] == 'AL'
    assert search('Alabama A & M', 'AL')[0]['id'] == '100654'
    assert search('Alabama A & M', 'CA') == []
    assert institution('invalid') is None


def test_college_selection_and_dual_enrollment(app, authed_client):
    complete_profile(authed_client)
    response = authed_client.get('/colleges?q=Alabama+A+%26+M&state=AL')
    assert b'Alabama A &amp; M University' in response.data
    assert authed_client.post('/colleges/select', data={'institution_id':'100654'}).status_code == 302
    form = authed_client.get('/terms',follow_redirects=True).get_data(as_text=True)
    assert 'value="100654" selected' in form
    assert authed_client.post('/terms', data=course_data()).status_code == 302
    with app.app_context():
        course = TermCourse.query.one()
        identifier = course.id
        assert (course.enrollment_type, course.school_year, course.credits) == ('dual', 11, 3)
    plan = authed_client.get('/courses/plan').get_data(as_text=True)
    assert 'Introduction to Biology' in plan and 'Alabama A &amp; M University' in plan
    year11 = plan.split('<h2>11th grade</h2>')[1].split('<h2>12th grade</h2>')[0]
    assert 'Introduction to Biology' in year11
    assert 'Introduction to Biology' in authed_client.get('/tasks?view=courses').get_data(as_text=True)
    assert authed_client.post(f'/terms/{identifier}/edit', data=course_data(status='planned')).status_code == 302
    assert b'4.0 study hours' in authed_client.get('/courses?course_source=dual').data
    exported = authed_client.get('/settings/export').json
    assert exported['institution_id'] == '100654'
    assert exported['term_courses'][0]['course_code'] == 'BIO 101'
    assert exported['term_courses'][0]['catalog_url'].startswith('https://')
    authed_client.post('/colleges/select', data={'institution_id':''})
    with app.app_context():
        assert TermCourse.query.one().institution_id == '100654'
        assert UserSettings.query.filter_by(user_id=authed_client.user_id).one().institution_id is None


def test_preset_switch_preserves_dual_courses(app, authed_client):
    complete_profile(authed_client)
    authed_client.post('/terms', data=course_data())
    authed_client.post('/settings', data={'academic_context':'college'})
    assert authed_client.get('/colleges').status_code == 200
    assert b'DUAL ENROLLMENT' in authed_client.get('/terms').data
    authed_client.post('/terms', data=course_data(title='Calculus', enrollment_type='college', school_year=''))
    with app.app_context():
        assert TermCourse.query.count() == 2
        assert TermCourse.query.filter_by(title='Calculus').one().school_year is None
    authed_client.post('/settings', data={'academic_context':'high_school'})
    assert b'Introduction to Biology' in authed_client.get('/courses/plan').data


@pytest.mark.parametrize('changes', [dict(institution_id='fake'), dict(school_year='8'),
    dict(enrollment_type='invalid'), dict(status='invalid'), dict(credits='nan'), dict(credits='-1'),
    dict(weekly_hours='inf'), dict(description='x'*1001), dict(catalog_url='javascript:alert(1)'),
    dict(catalog_url='https://user:pass@example.com'), dict(nonpersonal_confirmed='')])
def test_invalid_course_is_not_saved(app, authed_client, changes):
    response = authed_client.post('/terms', data=course_data(**changes))
    assert b'role="alert"' in response.data
    with app.app_context():
        assert TermCourse.query.count() == 0


def test_directory_pagination_and_user_isolation(app, authed_client):
    assert authed_client.get('/colleges?page=99999').status_code == 200
    assert authed_client.get('/colleges?q=%3Cscript%3E').status_code == 200
    assert authed_client.post('/colleges/select', data={'institution_id':'bogus'}).status_code == 400
    with app.app_context():
        other = User(username='other-college', password_hash='unused')
        db.session.add(other)
        db.session.flush()
        course = TermCourse(user_id=other.id, title='Private course', term='Fall', weekly_hours=3)
        db.session.add(course)
        db.session.commit()
        identifier = course.id
    assert authed_client.get(f'/terms/{identifier}/edit').status_code == 404
    assert authed_client.post(f'/terms/{identifier}/edit', data=course_data()).status_code == 404
    assert authed_client.post(f'/terms/{identifier}/delete').status_code == 404
    assert b'Private course' not in authed_client.get('/terms').data


def test_inline_selection_and_search_fallback(authed_client):
    complete_profile(authed_client)
    assert '/courses' in authed_client.get('/terms').location
    result=authed_client.get('/colleges/search?q=Alabama+A+%26+M&state=AL').json
    assert result['results'][0]['id']=='100654'
    assert len(authed_client.get('/colleges/search').json['results'])<=40
    assert authed_client.get('/colleges/search?state=invalid').json['total']==0
    page=authed_client.get('/courses?course_source=dual&college_q=Alabama&college_state=AL').text
    assert 'id="college-entry"' in page and 'Alabama A &amp; M University' in page
    response=authed_client.post('/terms',data=course_data(credits='nan'))
    assert 'value="100654" selected' in response.text
    response=authed_client.post('/terms',data=course_data())
    assert '/courses?course_source=dual' in response.location
    assert 'Introduction to Biology' in authed_client.get(response.location).text


def test_college_preferences_and_summary(app,authed_client):
    from services.college_planning import term_summary
    complete_profile(authed_client)
    authed_client.post('/settings',data={'academic_context':'college'})
    authed_client.get('/onboarding')
    with authed_client.session_transaction() as session:
        token=session['access_csrf']
    values=dict(csrf_token=token,college_program='Biology',college_term='Fall 2027',
        term_credit_goal='15',study_hours='20',nonpersonal_confirmed='yes')
    assert authed_client.post('/onboarding',data=values).status_code==302
    for changes in [dict(title='Planned',status='planned',credits='3'),
                    dict(title='Unknown',status='planned',credits=''),
                    dict(title='Considering',status='considering',credits='5'),
                    dict(title='Completed',status='completed',credits='5'),
                    dict(title='Other term',status='planned',term='Spring 2028',credits='5')]:
        authed_client.post('/terms',data=course_data(enrollment_type='college',school_year='',requirement_area='major',**changes))
    with app.app_context():
        summary=term_summary(db.session.get(User,authed_client.user_id))
        assert summary['course_count']==2 and summary['credits']==3 and summary['unknown_credits']==1
        assert summary['weekly_hours']==8 and summary['goal']==15 and summary['program']=='Biology'
    for invalid in ['nan','61','-1']:
        assert 'role="alert"' in authed_client.post('/onboarding',data={**values,'term_credit_goal':invalid}).text
    assert 'role="alert"' in authed_client.post('/onboarding',data={**values,'nonpersonal_confirmed':''}).text
    authed_client.post('/settings',data={'academic_context':'high_school'})
    assert 'Planned' in authed_client.get('/courses?course_source=dual').text
    with app.app_context():
        assert UserSettings.query.filter_by(user_id=authed_client.user_id).one().college_program=='Biology'
