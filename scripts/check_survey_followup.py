"""Exercise the daily list and tracking preference in a disposable browser account."""
import logging
import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from extensions import db
from models import Task, User
from browser_test_support import start_demo
from playwright.sync_api import sync_playwright, expect
from werkzeug.serving import make_server

logging.getLogger('werkzeug').setLevel(logging.ERROR)
app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite://'})
server = make_server('127.0.0.1', 0, app, threaded=True)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f'http://127.0.0.1:{server.server_port}'
errors = []
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel='chrome', headless=True)
        page = browser.new_page(viewport={'width': 390, 'height': 844})
        page.on('pageerror', lambda error: errors.append(str(error)))
        start_demo(page.context.request, base)
        with app.app_context():
            user = User.query.first()
            profile_id = Task.query.first().student_profile_id
            now = datetime.now(timezone.utc)
            local = now.astimezone(ZoneInfo(user.settings.timezone_name))
            deadline = local.replace(hour=23, minute=59, second=59).astimezone(timezone.utc)
            for title, due, planned in [('Due today check', deadline, None),
                                        ('Planned today check', now + timedelta(days=2), now),
                                        ('Overdue check', now - timedelta(days=1), now),
                                        ('Future only check', now + timedelta(days=3), None)]:
                db.session.add(Task(student_profile_id=profile_id, title=title, due_at=due,
                                    planned_start_at=planned, estimated_minutes=30))
            db.session.commit()
        page.goto(base + '/dashboard?view=today')
        expect(page.locator('.recommendation-reason')).to_be_visible()
        daily = page.locator('.daily-tasks')
        for title in ('Due today check', 'Planned today check', 'Overdue check'):
            expect(daily.get_by_role('link', name=title, exact=True)).to_be_visible()
        expect(daily.get_by_role('link', name='Future only check', exact=True)).to_have_count(0)
        for width in (390, 1440):
            page.set_viewport_size({'width': width, 'height': 960})
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), width
        page.goto(base + '/settings')
        page.get_by_text('Task planning', exact=True).click()
        page.locator('[name=time_tracking_enabled]').select_option('no')
        page.get_by_role('button', name='Save all settings', exact=True).click()
        page.goto(base + '/dashboard?view=today')
        expect(page.get_by_text('Timing and work history', exact=True)).to_have_count(0)
        item = page.locator('.daily-task-list li').filter(has=page.get_by_role('link', name='Due today check', exact=True))
        item.get_by_role('button', name='Start Due today check', exact=True).click()
        expect(page).to_have_url(base + '/dashboard?view=today')
        item = page.locator('.daily-task-list li').filter(has=page.get_by_role('link', name='Due today check', exact=True))
        item.get_by_role('button', name='Complete Due today check', exact=True).click()
        expect(page.locator('.daily-tasks').get_by_role('link', name='Due today check', exact=True)).to_have_count(0)
        with app.app_context():
            task = Task.query.filter_by(title='Due today check').one()
            assert task.status == 'completed' and task.started_at is None and task.timing_excluded
        assert not errors, errors
        browser.close()
        print('Survey follow-up browser checks passed: desktop/mobile, visible reasons, daily list, settings, start/complete without tracking.')
finally:
    server.shutdown()
