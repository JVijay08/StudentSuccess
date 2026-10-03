"""Check task and course button outcomes without touching a real planner."""
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server


def main():
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite://'})
    server = make_server('127.0.0.1', 0, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel='chrome', headless=True)
            page = browser.new_page(viewport={'width': 390, 'height': 844})
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(origin + '/planner')
            page.evaluate('''() => {
                const task = {id:'test-task',title:'Sample algebra',subject:'Math',due:'2027-01-01T18:00:00Z',planned:null,minutes:30,started:null,completed:null,status:'not_started',challenge:'medium',interest:'medium'};
                localStorage.setItem('studentsuccess.local-plan.v1', JSON.stringify({version:1,tasks:[task],courses:[],budget:null}));
            }''')
            page.reload()
            row = page.locator('#browser-task-test-task')
            row.get_by_role('button', name='Edit', exact=True).click()
            page.locator('#task-title').fill('Unsaved change')
            page.get_by_role('button', name='Cancel edit').click()
            assert row.evaluate('(element) => element === document.activeElement')
            assert row.get_by_role('heading').inner_text() == 'Sample algebra'
            row.get_by_role('button', name='Edit', exact=True).click()
            page.locator('#task-title').fill('Updated sample algebra')
            # Simulate the privacy-confirmed submission after filling the form.
            if page.locator('#task-form [name=nonpersonal_confirmed]').count(): page.locator('#task-form [name=nonpersonal_confirmed]').check()
            page.get_by_role('button', name='Save task', exact=True).click()
            assert row.get_by_role('heading').inner_text() == 'Updated sample algebra'
            assert row.evaluate('(element) => element === document.activeElement')
            page.get_by_role('button', name='Start this task', exact=True).click()
            assert page.get_by_role('button', name='View task in progress').count() == 1
            assert row.get_by_role('button', name='Start', exact=True).count() == 0
            row.get_by_role('button', name='Complete', exact=True).click()
            assert page.locator('#tasks-heading').evaluate('(element) => element === document.activeElement')
            assert 'Task completed' in page.locator('#task-action-status').inner_text()
            page.get_by_label('Show completed', exact=True).check()
            row.get_by_role('button', name='Reopen', exact=True).click()
            assert row.get_by_role('button', name='Complete', exact=True).count() == 1
            page.get_by_role('button', name='Load course catalog').click()
            first = page.locator('#catalog-results article').first
            first.get_by_role('button', name='Compare course', exact=True).click()
            assert page.locator('#view-comparison').inner_text() == 'View comparison (1)'
            assert first.get_by_role('button', name='Remove from comparison').get_attribute('aria-pressed') == 'true'
            page.locator('#view-comparison').click()
            assert page.url.endswith('#browser-comparison')
            page.locator('#course-comparison').get_by_role('button', name='Remove from comparison').click()
            assert page.locator('#view-comparison').is_hidden()
            assert first.get_by_role('button', name='Compare course').get_attribute('aria-pressed') == 'false'
            first.get_by_role('button', name='Add to four-year plan').click()
            assert 'Added to year' in first.locator('[role=status]').inner_text()
            first.get_by_role('button', name='Add to four-year plan').click()
            assert 'already planned' in first.locator('[role=status]').inner_text()
            assert page.evaluate("JSON.parse(localStorage.getItem('studentsuccess.local-plan.v1')).courses.length") == 1
            first.get_by_role('link', name='View my four-year plan').click()
            assert page.url.endswith('#course-area')
            assert not errors, errors
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            browser.close()
            print('PASS: browser task edit/save/cancel/start/complete/reopen, comparison toggle/jumps, course add/duplicate/view-plan, mobile overflow.')
    finally:
        server.shutdown()


if __name__ == '__main__':
    main()
