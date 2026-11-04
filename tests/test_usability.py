from datetime import datetime, timezone
from types import SimpleNamespace as NS

from extensions import db
from models import PlannedCourse
from services.study_insights import study_insights
from tests.test_course_routes import complete_profile


def test_insights_count_leaf_work_and_only_recorded_minutes():
    now = datetime(2026, 11, 3, 1, tzinfo=timezone.utc)
    settings = NS(timezone_name='America/New_York', week_start='Monday', time_tracking_enabled=True)
    def task(**values):
        return NS(**(dict(children=[], subject='Math', status='completed', timing_excluded=False,
                         estimated_minutes=60, actual_minutes=30, completed_at=now) | values))
    tasks = [task(), task(children=[1]), task(actual_minutes=None), task(timing_excluded=True),
             task(completed_at=datetime(2026, 11, 2, 1, tzinfo=timezone.utc)),
             task(status='in_progress', actual_minutes=None)]
    result = study_insights(tasks, settings, 10, now)
    assert result['total'] == 5 and result['completed'] == 4
    assert result['weekly_minutes'] == 30 and result['measured'] == 2
    assert result['courses'][0]['actual'] == 60
    assert result['courses'][0]['actual_width'] == 50
    settings.time_tracking_enabled = False
    assert study_insights(tasks, settings, 10, now)['measured'] == 0


def test_move_grade_preserves_data_rejects_duplicates_and_other_owners(app, authed_client):
    complete_profile(authed_client)
    for year in (10, 11):
        authed_client.post('/courses/plan/add/MATH_AP_STATISTICS',
                           data=dict(school_year=year, term='Fall', status='planned'))
    with app.app_context():
        pid = PlannedCourse.query.filter_by(school_year=11).one().id
    url = f'/courses/plan/{pid}/move'
    for year in (10, 13):
        assert authed_client.post(url, data={'school_year': year}).status_code == 302
        with app.app_context():
            assert db.session.get(PlannedCourse, pid).school_year == 11
    other = app.test_client()
    other.post('/demo')
    assert other.post(url, data={'school_year': 12}).status_code == 404
    assert authed_client.post(url, data={'school_year': 12}).status_code == 302
    with app.app_context():
        row = db.session.get(PlannedCourse, pid)
        assert (row.school_year, row.term, row.status) == (12, 'Fall', 'planned')
        assert PlannedCourse.query.filter_by(student_profile_id=row.student_profile_id).count() == 2


def test_quota_read_does_not_spend_requests(app):
    from models.ai_planning import AIQuota
    from services.ai_planning import remaining_requests
    with app.app_context():
        app.config['AI_USER_DAILY_LIMIT'] = 5
        assert remaining_requests(123) == 5
        assert AIQuota.query.count() == 0
        key = 'day:' + datetime.now(timezone.utc).strftime('%Y-%m-%d') + ':user:123'
        db.session.add(AIQuota(key=key, used=3)); db.session.commit()
        assert remaining_requests(123) == 2
        assert db.session.get(AIQuota, key).used == 3
