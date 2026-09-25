"""Exercise streamlined tasks using an isolated database."""
import json
import logging
import re
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from playwright.sync_api import sync_playwright, expect
from werkzeug.serving import make_server
from audit_responsive import BOUNDS


def main():
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    app = create_app({'TESTING':True, 'SQLALCHEMY_DATABASE_URI':'sqlite://'})
    server = make_server('127.0.0.1', 0, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    destination = Path('.test-streamlined'); destination.mkdir(exist_ok=True)
    errors, issues = [], []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel='chrome', headless=True)
            page = browser.new_page(viewport={'width':390,'height':844})
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.context.request.post(origin+'/demo')
            for number in range(3):
                page.context.request.post(origin+'/tasks',form=dict(title=f'Extra task {number}',
                    due_at='2027-12-01',estimated_minutes='30',nonpersonal_confirmed='yes'))
            page.goto(origin+'/tasks')
            page.locator('[data-task-search]>summary').click()
            page.locator('[data-task-query]').fill('Extra task 1')
            expect(page.locator('.task-card:visible')).to_have_count(1)
            page.locator('[data-task-query]').fill('')
            row = page.locator('.task-card').first
            identifier = int(row.get_attribute('id').split('-')[1])
            def saved():
                return next(t for t in page.context.request.get(origin+'/settings/export').json()['tasks'] if t['id']==identifier)
            before=saved()
            row.locator('.reschedule-control>summary').click()
            row.get_by_role('button',name='Tomorrow, 9 AM',exact=True).click()
            after=saved()
            assert after['due_at']==before['due_at'] and after['planned_start_at']!=before['planned_start_at']
            page.get_by_role('button',name='Undo schedule change').click()
            assert saved()['planned_start_at']==before['planned_start_at']
            page.locator(f'#task-{identifier}').get_by_role('button',name='Complete',exact=True).click()
            assert saved()['status']=='completed' and saved()['actual_minutes'] is None
            for width in [320,375,390,430,768,1440]:
                page.set_viewport_size({'width':width,'height':844})
                for path in ['/tasks','/tasks?view=courses','/dashboard','/settings']:
                    assert page.goto(origin+path).status==200
                    issues.extend([width,path,item] for item in page.evaluate(BOUNDS))
                    if path=='/tasks' and width in [390,1440]:
                        page.screenshot(path=str(destination/f'tasks-{width}.png'),full_page=True)
                    page.evaluate("document.querySelectorAll('details').forEach(e=>e.open=true)")
                    issues.extend([width,path,'expanded',item] for item in page.evaluate(BOUNDS))
            browser.close()
        result=dict(javascript_errors=errors,layout_issues=issues)
        (destination/'results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps(dict(javascript_errors=errors,layout_issue_count=len(issues),examples=issues[:6])))
        assert not errors and not issues
    finally:
        server.shutdown()


if __name__=='__main__':
    main()
