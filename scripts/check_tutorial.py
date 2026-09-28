"""Exercise the real tutorial, optional exercises, keyboard and small screens."""
import logging
import sys
import threading
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright, expect
from audit_responsive import BOUNDS
from routes.tutorial_routes import STEPS

logging.getLogger('werkzeug').setLevel(logging.ERROR)
app=create_app({'TESTING':True,'SQLALCHEMY_DATABASE_URI':'sqlite://'})
server=make_server('127.0.0.1',0,app,threaded=True)
threading.Thread(target=server.serve_forever,daemon=True).start()
base=f'http://127.0.0.1:{server.server_port}'
errors,issues=[],[]
try:
    with sync_playwright() as pw:
        browser=pw.chromium.launch(channel='chrome',headless=True)
        page=browser.new_page(viewport={'width':1440,'height':1000})
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(base)
        page.get_by_role('button',name='Start tutorial',exact=True).first.click()
        expect(page.locator('#tutorial-guide')).to_be_visible()
        for index in range(len(STEPS)):
            expect(page.locator('#tutorial-guide')).to_have_attribute('data-step',str(index))
            page.locator('#tutorial-show').click()
            expect(page.locator('.tutorial-target')).to_have_count(1)
            if index==1:
                page.locator('.tutorial-target').click()
                expect(page.locator('.task-state').first).to_have_text('In progress')
                page.reload()
                expect(page.locator('#tutorial-guide')).to_have_attribute('data-step','1')
            if index==2:
                page.locator('.complete-next-task button').first.click()
                expect(page.locator('.task-state').first).not_to_have_text('In progress')
            if index==4:
                page.locator('.tutorial-target').press('Enter')
                expect(page.locator('.task-menu[open]').first).to_be_visible()
            for width in [320,375,390,430]:
                page.set_viewport_size({'width':width,'height':844})
                issues.extend((index,width,issue) for issue in page.evaluate(BOUNDS))
            if index==8:
                page.screenshot(path='.test-overhaul-browser/tutorial-mobile.png',full_page=True)
            page.set_viewport_size({'width':1440,'height':1000})
            if index<len(STEPS)-1:
                page.get_by_role('button',name='Next section',exact=True).click()
        page.get_by_role('button',name='Finish tutorial',exact=True).click()
        expect(page.get_by_role('heading',name='Make room for your own plans.')).to_be_visible()
        # Server-rendered tutorial navigation must not depend on JavaScript.
        context=browser.new_context(java_script_enabled=False)
        other=context.new_page()
        other.goto(base)
        other.get_by_role('button',name='Start tutorial',exact=True).first.click()
        other.get_by_role('button',name='Next section',exact=True).click()
        expect(other.locator('#tutorial-guide')).to_have_attribute('data-step','1')
        other.screenshot(path='.test-overhaul-browser/tutorial-nojs.png',full_page=True)
        other.get_by_role('button',name='Exit tutorial',exact=True).click()
        expect(other.get_by_role('heading',name='Make room for your own plans.')).to_be_visible()
        browser.close()
    assert not errors,errors
    assert not issues,issues
    print(f'Tutorial passed: {len(STEPS)} sections, real start/completion, refresh, keyboard, {len(STEPS)*4} mobile checks, exit, and no-JavaScript navigation.')
finally:
    server.shutdown()
