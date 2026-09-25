"""Exercise tasks and email UI using an isolated DB and a fake email transport."""
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
    messages = []
    app = create_app({'TESTING':True, 'SQLALCHEMY_DATABASE_URI':'sqlite://',
                      'EMAIL_TEST_DELIVERY':messages.append, 'PUBLIC_BASE_URL':'https://example.test'})
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
            public=browser.new_page(viewport={'width':390,'height':844})
            public.on('pageerror',lambda error:errors.append(str(error)))
            for width in [320,390,430,1440]:
                public.set_viewport_size({'width':width,'height':844})
                for path in ['/register','/login','/account/forgot-password']:
                    assert public.goto(origin+path).status==200
                    issues.extend([width,path,item] for item in public.evaluate(BOUNDS))
            public.set_viewport_size({'width':390,'height':844})
            for theme in ['dark','high-contrast']:
                for path in ['/register','/account/login','/account/forgot-password']:
                    public.goto(origin+path)
                    public.evaluate("theme=>{Object.assign(document.documentElement.dataset,{theme,textScale:'200'});document.querySelectorAll('details').forEach(e=>e.open=true)}",theme)
                    issues.extend([theme,path,'200%',item] for item in public.evaluate(BOUNDS))
            public.goto(origin+'/register')
            public.get_by_label('Email',exact=True).fill('browser@example.org')
            public.get_by_label('New password',exact=True).fill('quiet notebook study hours')
            public.get_by_label('Confirm password',exact=True).fill('quiet notebook study hours')
            public.locator('[name=understood]').check()
            public.get_by_role('button',name='Send verification email').click()
            expect(public.get_by_role('heading',name='Check your inbox')).to_be_visible()
            link=re.search(r'/account/confirm/[^\s]+',messages[-1]['text'])[0]
            public.goto(origin+link)
            public.get_by_role('button',name='Confirm email & continue').click()
            expect(public.locator('.focus-card')).to_be_visible()
            public.goto(origin+'/onboarding')
            expect(public.get_by_role('heading',name='Set up your plan.')).to_be_visible()
            browser.close()
        result=dict(javascript_errors=errors,layout_issues=issues)
        (destination/'results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps(dict(javascript_errors=errors,layout_issue_count=len(issues),examples=issues[:6])))
        assert not errors and not issues
    finally:
        server.shutdown()


if __name__=='__main__':
    main()
