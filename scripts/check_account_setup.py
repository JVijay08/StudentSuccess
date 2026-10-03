"""Verify the real account/onboarding UI against an isolated database."""
import json
import logging
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
    app = create_app({'TESTING':True,'SQLALCHEMY_DATABASE_URI':'sqlite://'})
    server = make_server('127.0.0.1',0,app,threaded=True)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    destination = Path('.test-account-setup'); destination.mkdir(exist_ok=True)
    errors, issues, coverage = [], [], []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel='chrome',headless=True)
            page = browser.new_page(viewport={'width':390,'height':844})
            page.on('pageerror',lambda error:errors.append(str(error)))
            def audit(path, state):
                issues.extend([path,state,item] for item in page.evaluate(BOUNDS))
                coverage.append([path,state])
            for width in [320,375,390,430,768,1440]:
                page.set_viewport_size({'width':width,'height':844})
                for path in ['/login','/register','/transfer-planner']:
                    assert page.goto(origin+path).status == 200
                    audit(path,width)
                    if width in [390,1440]: page.screenshot(path=str(destination/f'{path[1:]}-{width}.png'),full_page=True)
            page.set_viewport_size({'width':390,'height':844})
            for theme in ['dark','high-contrast']:
                for path in ['/login','/register','/transfer-planner']:
                    page.goto(origin+path)
                    page.evaluate("theme=>Object.assign(document.documentElement.dataset,{theme,textScale:'200'})",theme)
                    audit(path,theme+' 200%')
            page.goto(origin+'/register')
            page.get_by_label('Choose a username',exact=True).fill('browser-student')
            page.get_by_label('Choose a password',exact=True).fill('quiet notebook study hours')
            page.get_by_role('button',name='Show password',exact=True).click()
            expect(page.locator('#password')).to_have_attribute('type','text')
            page.get_by_label('Confirm password',exact=True).fill('quiet notebook study hours')
            page.locator('[name=understood]').check()
            page.get_by_role('button',name='Create account & personalize').click()
            expect(page.get_by_role('heading',name='A planner that fits you.')).to_be_visible()
            for width in [320,375,390,430,768,1440]:
                page.set_viewport_size({'width':width,'height':844})
                for context in ['high_school','college']:
                    page.locator('[name=academic_context]').select_option(context)
                    audit('/onboarding',f'{width} {context}')
                    if width in [390,1440]: page.screenshot(path=str(destination/f'onboarding-{context}-{width}.png'),full_page=True)
            for theme in ['dark','high-contrast']:
                page.set_viewport_size({'width':390,'height':844})
                page.evaluate("theme=>Object.assign(document.documentElement.dataset,{theme,textScale:'200'})",theme)
                audit('/onboarding',theme+' 200%')
            page.goto(origin+'/tasks')
            expect(page).to_have_url(origin+'/onboarding')
            page.get_by_role('button',name='Sign out',exact=True).click()
            page.get_by_label('Username',exact=True).fill('browser-student')
            page.get_by_label('Password',exact=True).fill('quiet notebook study hours')
            page.get_by_role('button',name='Sign in',exact=True).click()
            expect(page).to_have_url(origin+'/onboarding')
            page.locator('[name=academic_context]').select_option('college')
            page.locator('[name=college_program]').fill('Biology')
            page.locator('[name=college_term]').fill('Fall 2026')
            page.locator('[name=term_credit_goal]').fill('15')
            page.locator('[name=default_task_minutes]').select_option('90')
            if page.locator('[name=nonpersonal_confirmed]').count(): page.locator('[name=nonpersonal_confirmed]').check()
            page.get_by_role('button',name='Finish setup & open my planner').click()
            expect(page).to_have_url(origin+'/dashboard')
            page.goto(origin+'/onboarding')
            expect(page.locator('[name=college_program]')).to_have_value('Biology')
            expect(page.locator('[name=default_task_minutes]')).to_have_value('90')
            expect(page.get_by_role('link',name='Cancel',exact=True)).to_be_visible()
            # No-JS sign-in and setup remain usable.
            context = browser.new_context(java_script_enabled=False)
            plain = context.new_page()
            plain.goto(origin+'/register')
            plain.locator('[name=username]').fill('nojs-student')
            plain.locator('[name=password]').fill('quiet notebook study hours')
            plain.locator('[name=confirm_password]').fill('quiet notebook study hours')
            plain.locator('[name=understood]').check()
            plain.get_by_role('button',name='Create account & personalize').click()
            expect(plain).to_have_url(origin+'/onboarding')
            if plain.locator('[name=nonpersonal_confirmed]').count(): plain.locator('[name=nonpersonal_confirmed]').check()
            plain.get_by_role('button',name='Finish setup & open my planner').click()
            expect(plain).to_have_url(origin+'/dashboard')
            browser.close()
        result = dict(javascript_errors=errors,layout_issues=issues,coverage=coverage)
        (destination/'results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps(dict(javascript_errors=errors,layout_issue_count=len(issues),checks=len(coverage),examples=issues[:8])))
        assert not errors and not issues
    finally:
        server.shutdown()


if __name__ == '__main__':
    main()
