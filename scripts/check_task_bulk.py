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
issues,errors=[],[]
try:
    with sync_playwright() as pw:
        browser=pw.chromium.launch(channel='chrome',headless=True)
        page=browser.new_page(viewport={'width':390,'height':844})
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.context.request.post(base+'/demo')
        page.goto(base+'/tasks')
        page.get_by_role('link',name='Select tasks',exact=True).click()
        page.locator('#selection-status').select_option('completed')
        page.get_by_role('button',name='Select all visible',exact=True).click()
        expect(page.locator('#selection-count')).to_contain_text('4 selected')
        page.locator('#selection-status').select_option('active')
        expect(page.locator('#selection-count')).to_contain_text('4 selected outside this filter')
        page.get_by_role('button',name='Clear selection',exact=True).click()
        page.locator('#selection-search').fill('algebra')
        page.get_by_role('button',name='Select all visible',exact=True).click()
        expect(page.locator('#selection-count')).to_contain_text('1 selected')
        page.locator('#selection-search').fill('')
        page.get_by_role('button',name='Select all visible',exact=True).click()
        for width in [320,375,390,430]:
            page.set_viewport_size({'width':width,'height':844})
            issues.extend(page.evaluate(BOUNDS))
        page.get_by_role('button',name='Review deletion',exact=True).first.click()
        expect(page.get_by_role('heading',name='Delete 3 tasks?',exact=True)).to_be_visible()
        for width in [320,375,390,430]:
            page.set_viewport_size({'width':width,'height':844})
            issues.extend(page.evaluate(BOUNDS))
        page.get_by_role('button',name='Delete 3 tasks',exact=True).click()
        expect(page.locator('.flash-success')).to_contain_text('Deleted 3 tasks')
        exported=page.context.request.get(base+'/settings/export').json()['tasks']
        assert len(exported)==4 and all(t['status']=='completed' for t in exported)
        browser.close()
    assert not issues,issues
    assert not errors,errors
    print('Bulk deletion passed: filtering, hidden selection counts, exact review/deletion, completed history preserved, eight mobile views, no JavaScript errors.')
finally:
    server.shutdown()
