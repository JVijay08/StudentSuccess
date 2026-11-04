"""Check suggestion follow-ups in an isolated browser and disposable database."""
import logging
import sys
import threading
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from models import Task
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
        page.goto(base)
        page.locator('#sample-scenario').click()
        expect(page.locator('#sample-priority-reason')).to_contain_text('overdue')
        start_demo(page.context.request, base)
        page.goto(base + '/dashboard')
        page.locator('.study-insights > summary').click()
        expect(page.locator('.completion-donut')).to_be_visible()
        page.locator('[data-park-open]').first.click()
        page.locator('#park-text').fill('Draft from a parked thought')
        with app.app_context():
            count = Task.query.count()
        page.locator('#park-to-task').click()
        expect(page.locator('#task-form [name=title]')).to_have_value('Draft from a parked thought')
        with app.app_context():
            assert Task.query.count() == count
        expect(page.locator('.quick-controls button')).not_to_have_count(1)
        page.locator('.quick-controls button').nth(1).click()
        expect(page.locator('[data-task-search-status]')).to_contain_text('matching task')
        page.goto(base + '/settings')
        search = page.locator('[data-settings-search] input')
        search.fill('timezone')
        expect(page.locator('#workspace-settings > details:visible')).to_have_count(1)
        search.fill('')
        assert page.locator('#workspace-settings > details:visible').count() > 1
        for path in ('/dashboard', '/tasks', '/settings', '/courses/plan', '/privacy', '/cookies'):
            page.goto(base + path)
            assert page.locator('h1').count()
            for width in (390, 1440):
                page.set_viewport_size({'width': width, 'height': 960})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (path, width)
        expect(page.locator('#notice-contents')).to_be_visible()
        expect(page.locator('[data-storage-status]')).to_contain_text('No browser plan saved')
        assert not errors, errors
        browser.close()
        print('Usability browser checks passed: sample, charts, draft-only thought transfer, course filters, settings search, legal navigation, storage inspector, mobile/desktop.')
finally:
    server.shutdown()
