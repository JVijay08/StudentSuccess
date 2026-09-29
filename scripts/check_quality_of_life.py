import logging, sys, threading
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright,expect
from audit_responsive import BOUNDS
logging.getLogger('werkzeug').setLevel(logging.ERROR)
app=create_app({'TESTING':True,'SQLALCHEMY_DATABASE_URI':'sqlite://'})
server=make_server('127.0.0.1',0,app,threaded=True)
threading.Thread(target=server.serve_forever,daemon=True).start()
base=f'http://127.0.0.1:{server.server_port}'
errors,issues=[],[]
try:
    with sync_playwright() as pw:
        browser=pw.chromium.launch(channel='chrome',headless=True)
        page=browser.new_page(viewport={'width':390,'height':844})
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(base)
        page.get_by_role('button',name='Start tutorial',exact=True).first.click()
        page.locator('#tutorial-show').click()
        page.get_by_role('button',name='Back to tutorial',exact=True).click()
        expect(page.locator('#tutorial-show')).to_be_focused()
        expect(page.get_by_role('button',name='Back to tutorial',exact=True)).to_be_hidden()
        page.goto(base+'/tasks')
        page.locator('.task-menu>summary').first.click()
        page.get_by_role('link',name='Use as template',exact=True).first.click()
        expect(page.locator('#task-form [name=title]')).not_to_have_value('')
        expect(page.locator('#task-form [name=due_at]')).to_have_value('')
        page.get_by_role('button',name='Tomorrow',exact=True).click()
        expected=page.evaluate("(()=>{const d=new Date(document.querySelector('.due-shortcuts').dataset.plannerToday+'T12:00:00Z');d.setUTCDate(d.getUTCDate()+1);return d.toISOString().slice(0,10)})()")
        expect(page.locator('#task-form [name=due_at]')).to_have_value(expected)
        for width in [320,390,430]:
            page.set_viewport_size({'width':width,'height':844});issues.extend(page.evaluate(BOUNDS))
        page.goto(base+'/tasks/select')
        boxes=page.locator('input[name=task_ids]')
        boxes.nth(0).click();boxes.nth(3).click(modifiers=['Shift'])
        expect(page.locator('#selection-count')).to_contain_text('4 selected')
        page.get_by_role('button',name='Review deletion',exact=True).first.click()
        expect(page.get_by_role('heading',name='Delete 4 tasks?',exact=True)).to_be_visible()
        browser.close()
    assert not errors,errors
    assert not issues,issues
    print('Quality-of-life checks passed: tutorial return, template, timezone-based date shortcut, Shift selection, mobile widths and no JavaScript errors.')
finally:
    server.shutdown()
