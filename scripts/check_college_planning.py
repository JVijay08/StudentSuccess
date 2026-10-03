"""Exercise college/dual planning in an isolated in-memory demo database."""
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
from check_notebook_v2 import CONTROL_AUDIT


def main():
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    app = create_app({'TESTING':True, 'SQLALCHEMY_DATABASE_URI':'sqlite://'})
    server = make_server('127.0.0.1', 0, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    destination = Path('.test-colleges')
    destination.mkdir(exist_ok=True)
    errors, issues = [], []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel='chrome', headless=True)
            page = browser.new_page(viewport={'width':1440,'height':1000})
            page.on('pageerror', lambda error: errors.append(str(error)))
            start_demo(page.context.request, origin)
            page.goto(origin+'/courses/plan')
            page.evaluate("document.documentElement.dataset.motion='reduced'")
            assert page.locator('.skip-link').bounding_box()['y'] < 0
            page.locator('.skip-link').focus()
            assert page.locator('.skip-link').bounding_box()['y'] >= 0
            page.get_by_role('link', name='Choose courses', exact=True).click()
            page.locator('#college-entry > summary').click()
            page.locator('#term-form [name=title]').fill('Draft preserved')
            page.get_by_text('Find a college by state or name', exact=True).click()
            page.get_by_label('College name or city').fill('Alabama A & M')
            page.get_by_label('College state / territory').select_option('AL')
            page.get_by_role('button', name='Find colleges', exact=True).click()
            expect(page.locator('#term-form [name=institution_id] option[value="100654"]')).to_have_count(1)
            expect(page.locator('#term-form [name=title]')).to_have_value('Draft preserved')
            page.locator('#term-form [name=institution_id]').select_option('100654')
            form = page.locator('#term-form')
            expect(form.locator('[name=institution_id]')).to_have_value('100654')
            expect(form.locator('[name=enrollment_type]')).to_have_value('dual')
            form.get_by_label('Course name', exact=True).fill('Introduction to Biology')
            form.get_by_label('Term', exact=True).fill('Fall 2027')
            form.locator('[name=school_year]').select_option('11')
            form.get_by_label('Planning status').select_option('planned')
            form.get_by_label('Weekly study hours').fill('4')
            form.get_by_text('Course code, credits & catalog details', exact=True).click()
            form.locator('[name=course_code]').fill('BIO 101')
            form.locator('[name=credits]').fill('3')
            form.locator('[name=description]').fill('Cells and lab practice')
            form.locator('[name=catalog_url]').fill('https://example.edu/catalog/bio101')
            if form.locator('[name=nonpersonal_confirmed]').count(): form.locator('[name=nonpersonal_confirmed]').check()
            form.get_by_role('button',name='Add course',exact=True).click()
            expect(page.get_by_role('heading',name='BIO 101: Introduction to Biology')).to_be_visible()
            page.get_by_role('link',name='Edit course',exact=True).click()
            form.locator('[name=status]').select_option('completed')
            if form.locator('[name=nonpersonal_confirmed]').count(): form.locator('[name=nonpersonal_confirmed]').check()
            form.get_by_role('button',name='Save course',exact=True).click()
            expect(page.locator('.dual-course-card .saved-label')).to_contain_text('Completed')
            paths=['/colleges?state=AL','/terms','/courses/plan','/settings','/profile']
            for width in [320,390,768,1440]:
                page.set_viewport_size({'width':width,'height':1000})
                for i,path in enumerate(paths):
                    assert page.goto(origin+path).status == 200
                    if path == '/terms':
                        page.locator('#college-entry').evaluate('(el)=>el.open=true')
                    if page.evaluate('document.documentElement.scrollWidth>innerWidth+1'):
                        issues.append([width,path,'overflow'])
                    issues.extend([width,path,issue] for issue in page.evaluate(CONTROL_AUDIT))
                    if width in [390,1440]:
                        page.screenshot(path=str(destination/f'page-{i}-{width}.png'),full_page=True)
            for theme in ['dark','high-contrast']:
                page.set_viewport_size({'width':390,'height':844})
                for path in ['/colleges?state=AL','/terms']:
                    page.goto(origin+path)
                    if path == '/terms': page.locator('#college-entry').evaluate('(el)=>el.open=true')
                    page.evaluate("theme=>Object.assign(document.documentElement.dataset,{theme,textScale:'200'})",theme)
                    page.wait_for_timeout(250)  # Let existing color transitions finish.
                    if page.evaluate('document.documentElement.scrollWidth>innerWidth+1'):
                        issues.append([theme,path,'200% overflow'])
                    issues.extend([theme,path,issue] for issue in page.evaluate(CONTROL_AUDIT))
            # Search and selection work without JavaScript or an external API.
            context=browser.new_context(java_script_enabled=False)
            start_demo(context.request, origin)
            nojs=context.new_page()
            nojs.goto(origin+'/courses?course_source=dual&college_q=Alabama+A+%26+M&college_state=AL')
            nojs.locator('#term-form [name=institution_id]').select_option('100654')
            expect(nojs.locator('#term-form [name=institution_id]')).to_have_value('100654')
            browser.close()
        result = {'javascript_errors':errors,'visual_issues':issues}
        (destination/'results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps(result))
        assert not errors and not issues
    finally:
        server.shutdown()


if __name__ == '__main__':
    main()
