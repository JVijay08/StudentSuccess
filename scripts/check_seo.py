"""Public discovery remains readable, responsive and usable without JavaScript."""
import logging,sys,threading
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
        page=browser.new_page()
        page.on('pageerror',lambda error:errors.append(str(error)))
        for width in [320,390,1440]:
            page.set_viewport_size({'width':width,'height':900})
            for path in ['/','/features','/updates']:
                page.goto(base+path)
                expect(page.locator('h1')).to_have_count(1)
                expect(page.locator('link[rel=canonical]')).to_have_count(1)
                expect(page.locator('meta[name=description]')).to_have_count(1)
                issues.extend((width,path,issue) for issue in page.evaluate(BOUNDS))
        page.goto(base+'/')
        page.get_by_role('tab',name='Today',exact=True).focus()
        page.keyboard.press('ArrowRight')
        expect(page.get_by_role('tab',name='Project steps')).to_be_focused()
        expect(page.get_by_role('tabpanel')).to_contain_text('Write an outline')
        page.keyboard.press('End')
        expect(page.get_by_role('tabpanel')).to_contain_text('Dual enrollment')
        page.get_by_role('link',name='About',exact=True).click()
        expect(page).to_have_url(base+'/#about')
        expect(page.locator('#about')).to_contain_text('Jayesh Vijay')
        page.emulate_media(reduced_motion='reduce')
        assert page.evaluate("getComputedStyle(document.documentElement).scrollBehavior") == 'auto'
        captures=Path('.test-landing');captures.mkdir(exist_ok=True)
        for width in [390,1440]:
            page.set_viewport_size({'width':width,'height':960})
            page.goto(base+'/')
            page.screenshot(path=str(captures/f'landing-{width}.png'),full_page=True)
        context=browser.new_context(java_script_enabled=False)
        other=context.new_page();other.goto(base+'/')
        expect(other.get_by_role('heading',name='Draft your introduction')).to_be_visible()
        other.get_by_role('link',name='About',exact=True).click()
        expect(other).to_have_url(base+'/#about')
        other.goto(base+'/features')
        expect(other.get_by_role('heading',name='A student planner for assignments and courses.')).to_be_visible()
        other.get_by_text('Do I need an email address or real name?',exact=True).click()
        expect(other.get_by_text('No. Accounts use a username and password.',exact=False)).to_be_visible()
        browser.close()
    assert not issues,issues
    assert not errors,errors
    print('SEO browser check passed: nine responsive public pages, unique metadata/H1, no JavaScript errors, and no-JavaScript FAQ.')
finally:
    server.shutdown()
