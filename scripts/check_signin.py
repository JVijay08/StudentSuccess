"""Check sign-in feedback, submit locking, recovery, and small screens."""
import logging
import sys
import threading
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright, expect
logging.getLogger('werkzeug').setLevel(logging.ERROR)
app=create_app({'TESTING':True,'SQLALCHEMY_DATABASE_URI':'sqlite://'})
server=make_server('127.0.0.1',0,app,threaded=True)
threading.Thread(target=server.serve_forever,daemon=True).start()
base=f'http://127.0.0.1:{server.server_port}'
try:
    with sync_playwright() as pw:
        browser=pw.chromium.launch(channel='chrome',headless=True)
        page=browser.new_page()
        page.goto(base+'/login')
        for width in [320,390,1440]:
            page.set_viewport_size({'width':width,'height':900})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.locator('#signin-submit').click()
        expect(page.locator('#username-error')).to_have_text('Enter your username.')
        expect(page.locator('#signin-submit')).to_be_enabled()
        page.locator('#username').fill('test-missing-user')
        page.locator('#password').fill('incorrect-password')
        page.get_by_role('button',name='Show password',exact=True).click()
        expect(page.locator('#password')).to_have_attribute('type','text')
        page.route('**/login',lambda route:route.fulfill(status=204))
        page.locator('#signin-submit').click()
        expect(page.locator('#signin-submit')).to_be_disabled()
        expect(page.locator('#signin-submit')).to_have_text('Signing in...')
        page.evaluate('window.dispatchEvent(new Event("pageshow"))')
        expect(page.locator('#signin-submit')).to_be_enabled()
        page.unroute('**/login')
        page.locator('#signin-submit').click()
        expect(page.locator('#signin-errors')).to_contain_text('Username or password was not recognized.')
        expect(page.locator('#signin-errors')).to_be_focused()
        expect(page.locator('#username')).to_have_value('test-missing-user')
        expect(page.locator('#password')).to_have_value('')
        expect(page.locator('#signin-submit')).to_be_enabled()
        browser.close()
    print('Sign-in checks passed: responsive layout, required fields, password toggle, submit locking, restored navigation, and credential errors.')
finally:
    server.shutdown()
