import io
import json
import re
import socket
from datetime import datetime
from unittest.mock import patch

import pytest
from extensions import db
from models import Task, PlannedCourse, TermCourse, User
from services.browser_transfer import validate_backup
from services.calendar_fetch import fetch_calendar, _target
from tests.test_course_routes import complete_profile


def backup(**extra):
    data = dict(version=1, context='high_school', budget=12, tasks=[
        dict(id='project', title='Browser project', subject='Math', due='2027-01-01T20:00:00Z',
             planned=None, started=None, completed=None, status='not_started', minutes=60),
        dict(id='step', parent='project', title='Browser step', subject='Math', due='2027-01-01T20:00:00Z',
             planned=None, started=None, completed=None, status='not_started', minutes=30)],
        courses=[dict(id='course', title='Custom ceramics', hours=3, year=10)])
    data.update(extra)
    return data


def preview_token(response):
    assert response.status_code == 200
    match = re.search(rb'name="preview" value="([^"]+)"', response.data)
    assert match, response.get_data(as_text=True)
    return match.group(1).decode()


def transfer_preview(client, data):
    return client.post('/planner/transfer', data={'confirmed': 'yes',
        'backup': (io.BytesIO(json.dumps(data).encode()), 'backup.json')})


def test_browser_transfer_preview_merge_and_replay(app, authed_client):
    complete_profile(authed_client)
    token = preview_token(transfer_preview(authed_client, backup()))
    with app.app_context():
        assert Task.query.count() == 0
    form = dict(confirmed='yes', save='yes', preview=token, apply_budget='yes')
    assert authed_client.post('/planner/transfer', data=form).status_code == 302
    assert authed_client.post('/planner/transfer', data=form).status_code == 302
    with app.app_context():
        assert Task.query.count() == 2 and PlannedCourse.query.count() == 1
        parent = Task.query.filter_by(title='Browser project').one()
        child = Task.query.filter_by(title='Browser step').one()
        assert child.parent_task_id == parent.id
        assert parent.student_profile.study_hours_per_week == 12
        course = PlannedCourse.query.one()
        assert course.catalog_id == 'browser' and course.imported_details['hours'] == 3
    plan = authed_client.get('/courses/plan')
    assert plan.status_code == 200 and b'Custom ceramics' in plan.data
    assert b'Custom ceramics' in authed_client.get('/tasks').data
    assert authed_client.get('/dashboard').status_code == 200


def test_browser_existing_records_are_not_overwritten(app, authed_client):
    complete_profile(authed_client)
    data = backup()
    token = preview_token(transfer_preview(authed_client, data))
    authed_client.post('/planner/transfer', data=dict(confirmed='yes', save='yes', preview=token))
    with app.app_context():
        Task.query.filter_by(title='Browser step').one().title = 'Edited in account'
        db.session.commit()
    data['tasks'][1]['title'] = 'Changed browser version'
    data['courses'][0]['year'] = 11
    token = preview_token(transfer_preview(authed_client, data))
    authed_client.post('/planner/transfer', data=dict(confirmed='yes', save='yes', preview=token))
    with app.app_context():
        assert Task.query.count() == 2
        assert Task.query.filter_by(title='Edited in account').count() == 1
        assert PlannedCourse.query.count() == 1 and PlannedCourse.query.one().school_year == 10


def test_college_transfer_deduplicates_courses_and_respects_tracking(app, authed_client):
    complete_profile(authed_client)
    data = backup(context='college', courses=[dict(id='c1', title='Calculus', hours=4, term='Fall'),
                                             dict(id='c2', title='Calculus', hours=4, term='Fall')])
    data['tasks'][1].update(status='completed', started='2026-10-01T12:00:00Z',
                            completed='2026-10-01T13:00:00Z', actual=60)
    authed_client.post('/settings', data={'time_tracking_enabled': 'no'})
    token = preview_token(transfer_preview(authed_client, data))
    authed_client.post('/planner/transfer', data=dict(confirmed='yes', save='yes', preview=token, apply_context='yes'))
    with app.app_context():
        assert TermCourse.query.count() == 1
        task = Task.query.filter_by(title='Browser step').one()
        assert task.started_at is None and task.actual_minutes is None and task.timing_excluded
        assert task.completed_at is not None
        assert db.session.get(User, authed_client.user_id).settings.academic_context == 'college'


@pytest.mark.parametrize('change', [
    lambda d: d['tasks'][1].update(parent='missing'),
    lambda d: d['tasks'][0].update(parent='step'),
    lambda d: d['tasks'][0].update(minutes=float('nan')),
    lambda d: d['tasks'][0].update(due='2027-01-01T12:00:00'),
    lambda d: d['courses'][0].update(hours=-1),
    lambda d: d['courses'][0].update(hours=10 ** 1000),
])
def test_browser_validation_rejects_bad_records_atomically(change):
    data = backup()
    change(data)
    with pytest.raises(ValueError):
        validate_backup(json.dumps(data).encode())


def test_browser_confirmation_and_tokens_are_required(app, authed_client):
    complete_profile(authed_client)
    assert b'Confirm that' in authed_client.post('/planner/transfer', data={}).data
    assert b'preview expired or is invalid' in authed_client.post('/planner/transfer',
        data=dict(confirmed='yes', save='yes', preview='tampered')).data
    with app.app_context():
        assert Task.query.count() == 0


def calendar(title='School essay', due='20270101T120000Z'):
    return f'BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nUID:school-essay\r\nSUMMARY:{title}\r\nDTSTART:{due}\r\nEND:VEVENT\r\nEND:VCALENDAR'.encode()


def feed_preview(client, raw):
    with patch('services.calendar_fetch.fetch_calendar', return_value=raw):
        return client.post('/tasks/import', data={'feed_url': 'https://school.example/feed.ics?secret=private',
                                                 'nonpersonal_confirmed': 'yes'})


def save_calendar(client, token):
    return client.post('/tasks/import', data={'preview': token, 'selected': '0', 'confirm': 'yes',
                                            'estimated_minutes': '45', 'nonpersonal_confirmed': 'yes'})


def test_calendar_url_review_refresh_and_stale_changes(app, authed_client):
    complete_profile(authed_client)
    response = feed_preview(authed_client, calendar())
    assert b'secret=private' not in response.data
    token = preview_token(response)
    save_calendar(authed_client, token)
    save_calendar(authed_client, token)
    with app.app_context():
        assert Task.query.count() == 1
    response = feed_preview(authed_client, calendar('Revised essay', '20270103T120000Z'))
    assert b'Update' in response.data and b'Currently: School essay' in response.data
    save_calendar(authed_client, preview_token(response))
    with app.app_context():
        task = Task.query.one()
        assert task.title == 'Revised essay' and task.due_at == datetime(2027, 1, 3, 12)
        assert task.estimated_minutes == 45
    token = preview_token(feed_preview(authed_client, calendar('Stale update')))
    with app.app_context():
        Task.query.one().title = 'Local edit after preview'
        db.session.commit()
    save_calendar(authed_client, token)
    with app.app_context():
        assert Task.query.one().title == 'Local edit after preview'
        Task.query.one().status = 'completed'
        db.session.commit()
    token = preview_token(feed_preview(authed_client, calendar('Do not reopen')))
    save_calendar(authed_client, token)
    with app.app_context():
        assert Task.query.one().status == 'completed' and Task.query.one().title == 'Local edit after preview'


@pytest.mark.parametrize('url', ['http://example.com/a.ics', 'https://user:pass@example.com/a',
                                'https://example.com:444/a', 'file:///etc/passwd', 'https://example.com/a#fragment'])
def test_calendar_fetch_rejects_unsafe_url_shapes(url):
    with pytest.raises(ValueError):
        _target(url)


@pytest.mark.parametrize('ip', ['127.0.0.1', '10.0.0.1', '169.254.169.254', '::1', 'fc00::1', '2002:7f00:1::'])
def test_calendar_fetch_rejects_internal_and_transition_addresses(ip):
    with patch('socket.getaddrinfo', return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, 443))]):
        with pytest.raises(ValueError):
            _target('https://school.example/calendar')


def test_calendar_fetch_pins_public_dns_and_rejects_redirects():
    address = (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('8.8.8.8', 443))
    with patch('socket.getaddrinfo', return_value=[address]), patch('services.calendar_fetch._PinnedHTTPS') as conn:
        response = conn.return_value.getresponse.return_value
        response.status = 302
        with pytest.raises(ValueError, match='redirects'):
            fetch_calendar('https://school.example/calendar')
        conn.assert_called_once_with('school.example', address)
        conn.return_value.close.assert_called_once()


def test_previews_cannot_cross_accounts(app, authed_client):
    from tests.account_helpers import create
    complete_profile(authed_client)
    browser_token = preview_token(transfer_preview(authed_client, backup()))
    calendar_token = preview_token(feed_preview(authed_client, calendar()))
    other = app.test_client()
    create(other)
    assert other.post('/planner/transfer', data=dict(confirmed='yes', save='yes', preview=browser_token)).status_code == 404
    assert save_calendar(other, calendar_token).status_code == 404
    with app.app_context():
        assert Task.query.count() == 0 and PlannedCourse.query.count() == 0


def test_new_account_resumes_transfer_after_setup(app):
    from tests.account_helpers import register, setup
    client = app.test_client()
    _, response = register(client, next='/planner/transfer')
    assert response.location.endswith('/onboarding')
    assert setup(client).location == '/planner/transfer'
    assert client.get('/planner/transfer').status_code == 200


def test_new_account_rejects_external_setup_destination(app):
    from tests.account_helpers import register, setup
    client = app.test_client()
    register(client, next='https://outside.example/')
    assert setup(client).location == '/dashboard'


def test_calendar_download_limits_and_public_success():
    address = (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('8.8.8.8', 443))
    with patch('socket.getaddrinfo', return_value=[address]), patch('services.calendar_fetch._PinnedHTTPS') as conn:
        response = conn.return_value.getresponse.return_value
        response.status = 200
        response.getheader.side_effect = lambda name, default=None: {'Content-Encoding': 'identity', 'Content-Length': '1048577'}.get(name, default)
        with pytest.raises(ValueError, match='1 MB'):
            fetch_calendar('https://school.example/calendar')
        response.getheader.side_effect = lambda name, default=None: default
        response.read1.side_effect = [calendar(), b'']
        assert fetch_calendar('https://school.example/calendar') == calendar()
        response.read1.side_effect = [b'x' * 65536] * 16 + [b'x']
        with pytest.raises(ValueError, match='1 MB'):
            fetch_calendar('https://school.example/calendar')


def test_mixed_public_and_private_dns_answers_are_rejected():
    answers = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, 443)) for ip in ('8.8.8.8', '10.0.0.2')]
    with patch('socket.getaddrinfo', return_value=answers):
        with pytest.raises(ValueError, match='public'):
            _target('https://school.example/calendar')


def test_cancelled_calendar_event_is_not_imported():
    from services.calendar_import import parse_calendar
    raw = calendar().replace(b'END:VCALENDAR', b'BEGIN:VEVENT\r\nUID:cancelled\r\nSUMMARY:Cancelled\r\nDTSTART:20270101T120000Z\r\nSTATUS:CANCELLED\r\nEND:VEVENT\r\nEND:VCALENDAR')
    assert [row['title'] for row in parse_calendar(raw, 'America/New_York')] == ['School essay']
