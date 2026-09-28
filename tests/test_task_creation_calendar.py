from datetime import date, datetime, timezone
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo
import pytest
from extensions import db
from models import Task, User
from services.recurrence_service import bounded_dates
from services.calendar_export import calendar_file, google_deadline_url
from tests.test_course_routes import complete_profile
from tests.test_feedback_overhaul import create


def test_daily_through_october_fourth_and_completion_stops(app,authed_client):
    complete_profile(authed_client)
    response=create(authed_client,title='Daily reading',due_at='2026-10-04',repeat_start='2026-09-28',recurrence_rule='daily',repeat_mode='bounded')
    assert response.status_code==302
    with app.app_context():
        tasks=Task.query.order_by(Task.due_at).all()
        assert len(tasks)==7
        local=[t.due_at.replace(tzinfo=timezone.utc).astimezone(ZoneInfo('America/New_York')) for t in tasks]
        assert local[0].date()==date(2026,9,28) and local[-1].date()==date(2026,10,4)
        assert all((d.hour,d.minute)==(23,59) for d in local)
        assert all(t.recurrence_rule is None and t.prep_for_id is None for t in tasks)
        identifiers=[t.id for t in tasks]
    for identifier in identifiers:
        assert authed_client.post(f'/tasks/{identifier}/complete').status_code==302
    with app.app_context():
        assert Task.query.count()==7
        assert Task.query.filter(Task.status!='completed').count()==0


def test_repeat_time_and_timezone_survive_dst(app,authed_client):
    complete_profile(authed_client)
    with app.app_context():
        db.session.get(User,authed_client.user_id).settings.timezone_name='America/Los_Angeles'
        db.session.commit()
    create(authed_client,due_at='2026-11-03',due_time='18:15',repeat_start='2026-10-30',repeat_mode='bounded',recurrence_rule='daily')
    with app.app_context():
        tasks=Task.query.order_by(Task.due_at).all()
        assert len(tasks)==5
        local=[t.due_at.replace(tzinfo=timezone.utc).astimezone(ZoneInfo('America/Los_Angeles')) for t in tasks]
        assert all((d.hour,d.minute)==(18,15) for d in local)
        assert local[0].utcoffset()!=local[-1].utcoffset()


def test_invalid_repeat_range_is_atomic(app,authed_client):
    complete_profile(authed_client)
    for start,end in [('2026-10-05','2026-10-04'),('2020-01-01','2026-10-04'),('bad','2026-10-04')]:
        response=create(authed_client,due_at=end,repeat_start=start,repeat_mode='bounded',recurrence_rule='daily')
        assert b'class="errors"' in response.data
    with app.app_context():
        assert Task.query.count()==0


def test_weekly_range_is_inclusive():
    end=datetime(2026,10,4,23,59,tzinfo=ZoneInfo('America/New_York'))
    dates=bounded_dates(date(2026,9,20),end,'weekly')
    assert [d.astimezone(ZoneInfo('America/New_York')).day for d in dates]==[20,27,4]


def test_google_link_encodes_text_and_exact_deadline():
    task=SimpleNamespace(title='Read & review + #1',due_at=datetime(2026,10,5,3,59))
    parsed=urlparse(google_deadline_url(task))
    params=parse_qs(parsed.query)
    assert parsed.netloc=='calendar.google.com'
    assert params['text']==['Read & review + #1 — due']
    assert params['dates']==['20261005T035900Z/20261005T040000Z']
    assert 'do not sync' in params['details'][0]


def test_calendar_escaping_folding_and_ownership(app,authed_client):
    complete_profile(authed_client)
    create(authed_client,title='Calendar test')
    response=authed_client.get('/settings/calendar.ics')
    assert response.status_code==200 and response.headers['Cache-Control']=='no-store'
    assert b'SUMMARY:Calendar test due' in response.data
    assert b'DTEND:' in response.data and b'TRANSP:TRANSPARENT' in response.data
    assert app.test_client().get('/settings/calendar.ics').status_code==302
    task=SimpleNamespace(id=123,title='文'*80+'\r\nBEGIN:VEVENT',due_at=datetime(2026,10,5,3,59))
    ics=calendar_file([task])
    assert all(len(line.encode('utf-8'))<=75 for line in ics.split('\r\n'))
    assert ics.count('\r\nBEGIN:VEVENT\r\n')==1


def test_export_preference_hides_google_links(app,authed_client):
    complete_profile(authed_client)
    create(authed_client)
    with app.app_context():
        task_id=Task.query.one().id
        db.session.get(User,authed_client.user_id).settings.calendar_export_enabled=False
        db.session.commit()
    assert b'calendar.google.com/calendar/r/eventedit' not in authed_client.get(f'/tasks/{task_id}').data
    assert authed_client.get('/settings/calendar.ics').status_code==404
    assert b'Calendar export is turned off' in authed_client.get('/calendar').data
