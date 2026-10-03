"""Check comparison selection, evidence filtering, and planning with fictional data."""
from browser_test_support import start_demo
import sys
import threading
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server
from app import create_app
from extensions import db
from models import PlannedCourse


def main():
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite://'})
    server = make_server('127.0.0.1', 0, app)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    output = Path('output/comparison-release')
    output.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel='chrome', headless=True)
            context = browser.new_context(viewport={'width':1440,'height':1000})
            start_demo(context.request, origin)
            page = context.new_page()
            errors=[]
            page.on('pageerror',lambda e: errors.append(str(e)))
            page.goto(origin+'/courses')
            assert page.locator('.example-pairs a').count() > 0
            boxes=page.locator('input[form="compare-form"][name="id"]')
            for i in range(3): boxes.nth(i).check()
            boxes.nth(3).click()
            assert not boxes.nth(3).is_checked()
            assert 'up to three' in page.locator('#compare-count').inner_text()
            assert page.locator('.compare-tray').bounding_box()['y'] < 1000
            page.locator('#compare-selection button').first.click()
            assert page.locator('input[form="compare-form"]:checked').count()==2
            page.get_by_role('button',name='Compare selected courses').click()
            page.wait_for_load_state('networkidle')
            assert page.locator('.comparison-options article').count()==2
            route='/courses/compare?id=SCI_AP_CHEMISTRY&id=SCI_AP_BIOLOGY'
            page.goto(origin+route)
            assert 'does not identify a lighter option' in page.locator('.tradeoff-summary').inner_text()
            toggle=page.locator('#differences-only')
            toggle.focus()
            page.keyboard.press('Space')
            assert page.locator('.comparison-table tbody tr:visible').count()==2
            toggle.uncheck()
            assert page.locator('.comparison-table tbody tr:visible').count()==8
            for width in [1440,390]:
                page.set_viewport_size({'width':width,'height':1000})
                page.goto(origin+route)
                page.screenshot(path=str(output/f'comparison-{width}.png'),full_page=True)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
                page.goto(origin+'/courses')
                page.screenshot(path=str(output/f'courses-{width}.png'),full_page=True)
            page.goto(origin+route)
            page.locator('.comparison-options article').first.get_by_role('button',name='Add to my plan').click()
            page.wait_for_load_state('networkidle')
            assert 'Already in your plan' in page.locator('.comparison-options article').first.inner_text()
            with app.app_context():
                assert PlannedCourse.query.filter_by(course_id='SCI_AP_CHEMISTRY',catalog_id='national').count()==1
            assert not errors,errors
            browser.close()
        print('Comparison selection, maximum count, removal, keyboard differences filter, mobile layout, and saved plan passed.')
    finally:
        server.shutdown()


if __name__=='__main__':
    main()
