"""Capture the Fieldnotes UI with isolated fictional data; verify its interaction."""
from browser_test_support import start_demo
import sys
import threading
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server
from app import create_app
from extensions import db
from models import Task


def main():
    destination = Path('output/fieldnotes-screenshots')
    destination.mkdir(parents=True, exist_ok=True)
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite://'})
    server = make_server('127.0.0.1', 0, app)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel='chrome', headless=True)
            context = browser.new_context(viewport={'width': 1440, 'height': 1000}, device_scale_factor=1)
            context.add_init_script("localStorage.setItem('studentsuccess-demo-tour-dismissed','1')")
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(origin)
            scene = page.locator('#desk-scene')
            scene.hover(position={'x':100, 'y':100})
            page.wait_for_function("document.querySelector('#desk-scene').style.getPropertyValue('--tilt-x') !== ''")
            assert not page.locator('#welcome-dialog').evaluate('(dialog) => dialog.open')
            page.get_by_role('button', name='How this works & privacy').click()
            assert page.locator('#welcome-dialog').evaluate('(dialog) => dialog.open')
            page.keyboard.press('Escape')
            arrange = page.locator('#arrange-desk')
            arrange.focus()
            page.keyboard.press('Enter')
            assert arrange.get_attribute('aria-pressed') == 'true'
            assert 'One assignment.' in page.locator('#desk-status').inner_text()
            page.emulate_media(reduced_motion='reduce')
            page.wait_for_function("document.querySelector('#desk-scene').style.getPropertyValue('--tilt-x') === ''")
            assert float(page.locator('.note-assignment').evaluate('(el) => parseFloat(getComputedStyle(el).transitionDuration)')) < .01
            arrange.click()
            assert arrange.get_attribute('aria-pressed') == 'false'
            page.emulate_media(reduced_motion='no-preference')
            page.get_by_role('button', name='Essay', exact=True).click()
            assert page.locator('#lab-task').inner_text() == 'Write one sentence. Let it be rough.'
            page.locator('#lab-done').focus()
            page.keyboard.press('Space')
            assert 'One small step.' in page.locator('#lab-feedback').inner_text()
            page.get_by_role('button', name='Exam', exact=True).click()
            assert not page.locator('#lab-done').is_checked()
            assert page.get_by_role('button', name='Exam', exact=True).get_attribute('aria-pressed') == 'true'
            page.get_by_role('button', name='Problem set', exact=True).click()
            page.locator('h1').click()
            page.evaluate('window.scrollTo(0, 0)')
            page.screenshot(path=str(destination/'landing.png'), full_page=True)
            arrange.click()
            page.wait_for_timeout(750)
            page.screenshot(path=str(destination/'landing-arranged.png'), full_page=True)
            for theme in ['dark', 'high-contrast']:
                page.evaluate('(theme) => document.documentElement.dataset.theme = theme', theme)
                page.screenshot(path=str(destination/f'landing-{theme}.png'), full_page=True)
            page.set_viewport_size({'width':390,'height':844})
            page.goto(origin)
            page.screenshot(path=str(destination/'landing-mobile.png'), full_page=True)
            start_demo(context.request, origin)
            page.set_viewport_size({'width':1440,'height':1000})
            for name, route in [('dashboard','/dashboard'),('tasks','/tasks'),('courses','/courses'),('comparison','/courses/compare?id=SCI_AP_CHEMISTRY&id=SCI_AP_BIOLOGY'),('four-year-plan','/courses/plan'),('settings','/settings')]:
                assert page.goto(origin+route).status == 200
                page.screenshot(path=str(destination/f'{name}.png'), full_page=True)
            page.set_viewport_size({'width':390,'height':844})
            page.goto(origin+'/dashboard')
            page.screenshot(path=str(destination/'mobile-dashboard.png'), full_page=True)
            form = page.locator('.start-next-task')
            task_id = int(form.get_attribute('action').split('/')[-2])
            form.get_by_role('button', name='Start this task').click()
            page.wait_for_load_state('networkidle')
            assert page.url.endswith('/dashboard')
            with app.app_context():
                assert db.session.get(Task, task_id).status == 'in_progress'
            for theme in ['dark', 'high-contrast']:
                page.evaluate('(theme) => document.documentElement.dataset.theme = theme', theme)
                page.screenshot(path=str(destination/f'dashboard-{theme}.png'), full_page=True)
            page.set_viewport_size({'width':1440,'height':1000})
            page.goto(origin+'/settings')
            sections = page.locator('.settings-form>section')
            first, second = sections.nth(0).bounding_box(), sections.nth(1).bounding_box()
            assert abs(first['y'] - second['y']) < 2 and second['x'] > first['x'] + first['width']
            page.locator('[name="default_task_minutes"]').select_option('45')
            page.evaluate('window.scrollTo(0, 600)')
            save = page.get_by_role('button', name='Save all settings')
            assert 0 <= save.bounding_box()['y'] < 1000
            save.click()
            page.wait_for_load_state('networkidle')
            assert page.locator('[name="default_task_minutes"]').input_value() == '45'
            page.goto(origin+'/dashboard')
            logout = page.get_by_role('button', name='Log out')
            assert logout.bounding_box()['y'] < 700
            page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            assert 0 <= logout.bounding_box()['y'] < 1000
            logout.click()
            page.wait_for_load_state('networkidle')
            assert not page.url.endswith('/dashboard')
            assert not errors, errors
            browser.close()
        print('Desk interaction, keyboard activation, reduced motion, privacy dialog, task start persistence, and browser error checks passed. Captured 14 screenshots.')
    finally:
        server.shutdown()


if __name__ == '__main__':
    main()
