"""Motion must remain optional, honest about saves, and keyboard/mobile usable."""
import logging
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from extensions import db
from models import Task
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright, expect
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
        context=browser.new_context(viewport={'width':1440,'height':900})
        page=context.new_page()
        page.on('pageerror',lambda e:errors.append(str(e)))
        context.request.post(base+'/demo')
        page.goto(base+'/dashboard')
        page.locator('.start-next-task button').first.click()
        expect(page.locator('html')).to_have_attribute('data-paper-confirmed','start')
        expect(page.locator('.task-state').first).to_have_text('In progress')
        page.locator('.complete-next-task button').first.click()
        expect(page.locator('html')).to_have_attribute('data-paper-confirmed','complete')
        page.goto(base+'/tasks')
        # Native summary keyboard semantics survive height animation.
        summary=page.locator('.task-entry>summary')
        summary.focus();page.keyboard.press('Enter')
        expect(page.locator('.task-entry')).to_have_attribute('open','')
        page.locator('#task-form [name=title]').fill('Motion regression task')
        page.locator('#task-form [name=due_at]').fill('2027-12-10')
        page.locator('#task-form [name=estimated_minutes]').fill('30')
        if page.locator('#task-form [name=nonpersonal_confirmed]').count(): page.locator('#task-form [name=nonpersonal_confirmed]').check()
        page.locator('#task-form button[type=submit]').click()
        expect(page.locator('html')).to_have_attribute('data-paper-confirmed','add-task')
        with app.app_context():
            identifier=Task.query.filter_by(title='Motion regression task').one().id
        card=page.locator(f'#task-{identifier}')
        card.locator('.task-menu>summary').click()
        page.keyboard.press('Escape')
        expect(card.locator('.task-menu')).not_to_have_attribute('open','')
        expect(card.locator('.task-menu>summary')).to_be_focused()
        # Deliberately invalid server submission must never show a completion effect.
        card.locator('.task-menu>summary').click()
        card.get_by_text('Record time & complete',exact=True).click()
        minutes=card.locator('[name=actual_minutes]')
        minutes.evaluate("input=>input.removeAttribute('min')")
        minutes.fill('0')
        card.get_by_role('button',name='Save time & complete').click()
        expect(page.locator('.flash-error')).to_be_visible()
        expect(page.locator('html')).not_to_have_attribute('data-paper-confirmed','complete')
        with app.app_context(): assert db.session.get(Task,identifier).status!='completed'
        page.goto(base+'/settings')
        page.get_by_role('button',name='Save all settings',exact=True).click()
        expect(page.locator('html')).to_have_attribute('data-paper-confirmed','settings')
        expect(page.get_by_role('button',name='Saved',exact=False)).to_be_visible()
        page.locator('[name=reduce_motion]').check()
        expect(page.locator('html')).to_have_attribute('data-motion','reduced')
        assert page.evaluate("document.getAnimations().filter(a=>a.playState==='running').length") == 0
        page.locator('[name=reduce_motion]').uncheck()
        expect(page.locator('html')).to_have_attribute('data-motion','standard')
        page.emulate_media(reduced_motion='reduce')
        page.goto(base+'/tasks')
        page.locator('.task-entry>summary').click()
        assert page.evaluate("document.getAnimations().filter(a=>a.playState==='running').length") == 0
        page.emulate_media(reduced_motion='no-preference')
        page.goto(base+'/courses?scope=ga')
        boxes=page.locator('input[form=compare-form]')
        expect(page.locator('.compare-tray')).to_be_hidden()
        boxes.nth(0).check()
        expect(page.locator('.compare-tray')).to_be_visible()
        expect(page.locator('#compare-count')).to_contain_text('1 selected')
        boxes.nth(0).uncheck()
        expect(page.locator('.compare-tray')).to_be_hidden()
        card=page.locator('.course-card:has(button[data-course-id])').first
        card.get_by_role('button',name='Add to plan',exact=True).click()
        card.get_by_role('button',name='Add course',exact=True).click()
        expect(page.locator('html')).to_have_attribute('data-paper-confirmed','add-course')
        page.goto(base+'/updates')
        page.locator('#update-query').fill('not-a-real-update-match')
        expect(page.locator('#no-updates')).to_be_visible()
        for width in [320,375,390,430]:
            page.set_viewport_size({'width':width,'height':844})
            for path in ['/dashboard','/tasks','/courses?scope=ga','/courses/plan','/settings','/updates']:
                page.goto(base+path)
                issues.extend((width,path,issue) for issue in page.evaluate(BOUNDS))
        # JavaScript animation/storage support must not be required for task actions.
        fallback=browser.new_context(viewport={'width':390,'height':844},has_touch=True)
        fallback.add_init_script("Object.defineProperty(window,'sessionStorage',{get(){throw new Error('blocked')}});Element.prototype.animate=undefined;")
        fallback.request.post(base+'/demo')
        other=fallback.new_page();other.on('pageerror',lambda e:errors.append(str(e)))
        other.goto(base+'/dashboard')
        other.locator('.start-next-task button').first.click()
        expect(other.locator('.task-state').first).to_have_text('In progress')
        other.locator('.complete-next-task button').first.click()
        expect(other.locator('.task-overview').first).to_be_visible()
        browser.close()
    assert not errors, errors
    assert not issues, issues
    print('Motion checks passed: confirmed actions, rejected completion, keyboard, immediate/OS reduced motion, comparison, blocked storage/no WAAPI fallback, 24 mobile views.')
finally:
    server.shutdown()
