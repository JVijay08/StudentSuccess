"""Browser transfer and calendar refresh using isolated data and a mocked school feed."""
import logging
import sys
import threading
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from extensions import db
from models import Task
from tests.test_import_followup import backup, calendar
from tests.account_helpers import PASSWORD
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
        page.goto(base + '/planner')
        page.evaluate('(data) => localStorage.setItem("studentsuccess.local-plan.v1", JSON.stringify(data))', backup())
        original = page.evaluate('localStorage.getItem("studentsuccess.local-plan.v1")')
        page.get_by_role('link', name='Copy this plan into an account').click()
        expect(page).to_have_url(__import__('re').compile('/login\\?next='))
        page.get_by_role('link', name='Create an account', exact=True).click()
        expect(page.locator('[name=next]')).to_have_value('/planner/transfer')
        page.locator('[name=username]').fill('browser-check')
        page.locator('[name=password]').fill(PASSWORD)
        page.locator('[name=confirm_password]').fill(PASSWORD)
        page.locator('[name=understood]').check()
        page.get_by_role('button', name='Create account & personalize').click()
        expect(page).to_have_url(base + '/onboarding')
        token = page.locator('[name=csrf_token]').first.input_value()
        response = page.request.post(base + '/onboarding', form={'csrf_token': token, 'academic_context': 'high_school',
            'grade': '10', 'study_hours': '12', 'timezone_name': 'America/New_York'})
        assert response.ok
        page.goto(base + '/planner/transfer')
        page.get_by_role('button', name='Use the plan saved in this browser').click()
        page.locator('[name=confirmed]').check()
        page.get_by_role('button', name='Preview transfer', exact=True).click()
        expect(page.get_by_role('heading', name='Transfer preview')).to_be_visible()
        with app.app_context():
            assert Task.query.count() == 0
        for width in (390, 1440):
            page.set_viewport_size({'width': width, 'height': 960})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.locator('[name=confirmed]').check()
        page.get_by_role('button', name='Save transfer', exact=True).click()
        expect(page).to_have_url(base + '/dashboard')
        assert page.evaluate('localStorage.getItem("studentsuccess.local-plan.v1")') == original
        page.goto(base + '/courses/plan')
        expect(page.get_by_text('Custom ceramics', exact=True)).to_be_visible()
        with patch('services.calendar_fetch.fetch_calendar', return_value=calendar()):
            page.goto(base + '/tasks/import')
            page.locator('[name=feed_url]').fill('https://school.example/calendar.ics')
            page.locator('form').filter(has=page.locator('[name=feed_url]')).locator('[name=nonpersonal_confirmed]').check()
            page.get_by_role('button', name='Preview calendar URL').click()
            expect(page.get_by_role('heading', name='Review changes')).to_be_visible()
            page.locator('[name=nonpersonal_confirmed]').check()
            page.get_by_role('button', name='Save selected assignments').click()
        with patch('services.calendar_fetch.fetch_calendar', return_value=calendar('Updated school essay')):
            page.goto(base + '/tasks/import')
            page.locator('[name=feed_url]').fill('https://school.example/calendar.ics')
            page.locator('form').filter(has=page.locator('[name=feed_url]')).locator('[name=nonpersonal_confirmed]').check()
            page.get_by_role('button', name='Preview calendar URL').click()
            expect(page.locator('[name=selected]')).not_to_be_checked()
            page.locator('[name=selected]').check()
            page.locator('[name=nonpersonal_confirmed]').check()
            page.get_by_role('button', name='Save selected assignments').click()
        with app.app_context():
            assert Task.query.filter_by(title='Updated school essay').count() == 1
            assert Task.query.count() == 3
        assert not errors, errors
        browser.close()
    print('Import browser checks passed: sign-up return, local preview/save, preserved browser copy, custom course, calendar import and reviewed refresh.')
finally:
    server.shutdown()
