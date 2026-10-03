"""Exercise reminder state and real college lookup feedback in an isolated database."""
from browser_test_support import start_demo
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
    output = Path('.test-planner-controls'); output.mkdir(exist_ok=True)
    errors, issues, coverage = [], [], []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel='chrome',headless=True)
            page = browser.new_page(viewport={'width':390,'height':844})
            page.on('pageerror',lambda error:errors.append(str(error)))
            start_demo(page.context.request, origin)
            def audit(name):
                issues.extend([name,issue] for issue in page.evaluate(BOUNDS))
                coverage.append(name)
            page.goto(origin+'/settings')
            page.evaluate("document.querySelectorAll('.mobile-disclosure').forEach(e=>e.open=true)")
            toggle = page.get_by_role('checkbox',name='In-app reminders',exact=True)
            expect(toggle).not_to_be_checked()
            toggle.focus()
            toggle.press('Space')
            expect(toggle).to_be_checked()
            expect(page.locator('.bell-toggle__on')).to_be_visible()
            with page.expect_navigation(wait_until='load'):
                page.get_by_role('button',name='Save all settings',exact=True).click()
            page.evaluate("document.querySelectorAll('.mobile-disclosure').forEach(e=>e.open=true)")
            expect(toggle).to_be_checked()
            page.goto(origin+'/onboarding')
            expect(toggle).to_be_checked()
            toggle.uncheck()
            if page.locator('[name=nonpersonal_confirmed]').count(): page.locator('[name=nonpersonal_confirmed]').check()
            with page.expect_navigation(wait_until='load'):
                page.get_by_role('button',name='Save planning preferences',exact=True).click()
            page.evaluate("document.querySelectorAll('.mobile-disclosure').forEach(e=>e.open=true)")
            expect(toggle).not_to_be_checked()
            # No ring on initial render; user/OS reduced motion must also prevent rings.
            assert page.locator('.bell-toggle__icon').evaluate('(e)=>e.getAnimations().length') == 0
            page.emulate_media(reduced_motion='reduce')
            toggle.check()
            assert page.locator('.bell-toggle__icon').evaluate('(e)=>e.getAnimations().length') == 0
            page.emulate_media(reduced_motion='no-preference')
            page.locator('[name=reduce_motion]').check()
            toggle.uncheck(); toggle.check()
            assert page.locator('.bell-toggle__icon').evaluate('(e)=>e.getAnimations().length') == 0
            for width in [320,375,390,430,768,1440]:
                page.set_viewport_size({'width':width,'height':844})
                for path in ['/settings','/onboarding']:
                    page.goto(origin+path)
                    page.evaluate("document.querySelectorAll('.mobile-disclosure').forEach(e=>e.open=true)")
                    toggle.check(); audit(f'{path} on {width}')
                    toggle.uncheck(); audit(f'{path} off {width}')
                    if width in [390,1440]:
                        page.evaluate('window.scrollTo(0,0)')
                        page.screenshot(path=str(output/f'{path[1:]}-{width}.png'),full_page=True)
            for theme in ['dark','high-contrast']:
                page.set_viewport_size({'width':320,'height':844})
                for path in ['/settings','/onboarding']:
                    page.goto(origin+path)
                    page.evaluate("document.querySelectorAll('.mobile-disclosure').forEach(e=>e.open=true)")
                    page.evaluate("theme=>Object.assign(document.documentElement.dataset,{theme,textScale:'200',motion:'reduced'})",theme)
                    toggle.check(); audit(f'{path} {theme} 200%')
            page.set_viewport_size({'width':390,'height':844})
            for path in ['/courses?course_source=dual','/terms']:
                page.goto(origin+path)
                page.locator('#college-entry').evaluate('(el)=>el.open=true')
                page.locator('.college-finder').evaluate('(el)=>el.open=true')
                finder = page.locator('[data-college-finder]')
                feedback = page.locator('[data-college-feedback]')
                select = page.locator('#term-form [name=institution_id]')
                title = page.locator('#term-form [name=title]')
                title.fill('Keep this draft')
                finder.locator('[name=college_q]').fill('Alabama A & M')
                finder.locator('[name=college_state]').select_option('AL')
                finder.get_by_role('button',name='Find colleges',exact=True).click()
                expect(feedback).to_have_attribute('data-state','done')
                select.select_option('100654')
                expect(title).to_have_value('Keep this draft')
                held = []
                pattern = '**/colleges/search?*'
                page.route(pattern,lambda route:held.append(route))
                finder.get_by_role('button',name='Find colleges',exact=True).click()
                expect(feedback).to_have_attribute('data-state','running')
                expect(select).to_have_attribute('aria-busy','true')
                assert held
                for width in [320,390,768,1440]:
                    page.set_viewport_size({'width':width,'height':844}); audit(f'{path} running {width}')
                page.emulate_media(reduced_motion='reduce')
                assert feedback.locator('svg').evaluate('(e)=>getComputedStyle(e).animationName') == 'none'
                page.emulate_media(reduced_motion='no-preference')
                held.pop().fulfill(status=503,body='unavailable')
                expect(feedback).to_have_attribute('data-state','error')
                expect(select).to_have_value('100654')
                expect(title).to_have_value('Keep this draft')
                for width in [320,390,768,1440]:
                    page.set_viewport_size({'width':width,'height':844}); audit(f'{path} error {width}')
                page.screenshot(path=str(output/f'search-error-{path.split("?")[0][1:]}.png'),full_page=True)
                page.unroute(pattern)
                retry = finder.get_by_role('button',name='Retry college search',exact=True)
                retry.focus(); retry.press('Enter')
                expect(feedback).to_have_attribute('data-state','done')
                expect(retry).to_be_hidden()
                expect(select).to_be_focused()
                expect(select).to_have_value('100654')
                finder.locator('[name=college_q]').fill('no-such-college-abcdefghijk')
                finder.get_by_role('button',name='Find colleges',exact=True).click()
                expect(feedback).to_have_attribute('data-state','done')
                expect(feedback).to_contain_text('No colleges found')
                expect(finder.locator('[name=college_q]')).to_be_focused()
                expect(select).to_have_value('100654')
                expect(title).to_have_value('Keep this draft')
                for width in [320,390,768,1440]:
                    page.set_viewport_size({'width':width,'height':844}); audit(f'{path} empty {width}')
                # A slow response becomes an actionable error instead of an endless spinner.
                page.clock.install()
                held = []
                page.route(pattern,lambda route:held.append(route))
                finder.get_by_role('button',name='Find colleges',exact=True).click()
                expect(feedback).to_have_attribute('data-state','running')
                page.clock.fast_forward(15001)
                expect(feedback).to_have_attribute('data-state','error')
                expect(feedback).to_contain_text('took too long')
                expect(select).to_have_value('100654')
                for route in held: route.abort()
                page.unroute(pattern)
                # Handle large text and themes in the longest status state.
                for theme in ['dark','high-contrast']:
                    page.set_viewport_size({'width':320,'height':844})
                    page.evaluate("theme=>Object.assign(document.documentElement.dataset,{theme,textScale:'200'})",theme)
                    audit(f'{path} {theme} timeout 200%')
            # Native controls and GET lookup still work without JavaScript.
            context = browser.new_context(java_script_enabled=False)
            start_demo(context.request, origin)
            plain = context.new_page()
            plain.goto(origin+'/settings')
            plain.get_by_role('checkbox',name='In-app reminders',exact=True).check()
            plain.get_by_role('button',name='Save all settings',exact=True).click()
            expect(plain.get_by_role('checkbox',name='In-app reminders',exact=True)).to_be_checked()
            plain.goto(origin+'/courses?course_source=dual')
            plain.locator('.college-finder > summary').click()
            plain.get_by_label('College name or city').fill('Alabama A & M')
            plain.get_by_role('button',name='Find colleges',exact=True).click()
            expect(plain.locator('[data-college-feedback]')).to_have_attribute('data-state','done')
            expect(plain.locator('#term-form [name=institution_id] option[value="100654"]')).to_have_count(1)
            browser.close()
        result = dict(javascript_errors=errors,layout_issues=issues,coverage=coverage)
        (output/'results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps(dict(javascript_errors=errors,layout_issue_count=len(issues),views=len(coverage),examples=issues[:8])))
        assert not errors and not issues
    finally:
        server.shutdown()


if __name__ == '__main__':
    main()
