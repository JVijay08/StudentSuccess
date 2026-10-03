"""Browser check for finite repeats, one course picker and calendar handoff."""
import logging
import sys
import threading
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
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
        page=browser.new_page(viewport={'width':390,'height':844})
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.context.request.post(base+'/demo')
        page.goto(base+'/tasks')
        page.locator('.task-entry>summary').click()
        form=page.locator('#task-form')
        expect(form.locator('input[list]')).to_have_count(0)
        form.locator('[name=saved_course]').select_option(index=1)
        expect(form.locator('[name=subject]')).to_be_hidden()
        form.locator('[name=title]').fill('Practice daily reading')
        form.locator('[name=due_at]').fill('2026-10-04')
        form.locator('[name=due_time]').fill('18:15')
        form.locator('[name=recurrence_rule]').select_option('daily')
        form.locator('[name=repeat_start]').fill('2026-09-28')
        expect(form.locator('[data-due-label]')).to_have_text('Repeat through (inclusive)')
        if form.locator('[name=nonpersonal_confirmed]').count(): form.locator('[name=nonpersonal_confirmed]').check()
        for width in [320,375,390,430]:
            page.set_viewport_size({'width':width,'height':844})
            issues.extend((width,'form',issue) for issue in page.evaluate(BOUNDS))
        form.get_by_role('button',name='Add repeating tasks',exact=True).click()
        expect(page.locator('.flash-success').first).to_contain_text('7 occurrences')
        with app.app_context():
            tasks=Task.query.filter_by(title='Practice daily reading').all()
            assert len(tasks)==7
            identifier=tasks[0].id
        page.goto(base+f'/tasks/{identifier}')
        link=page.get_by_role('link',name='Add deadline to Google Calendar',exact=False)
        expect(link).to_have_attribute('target','_blank')
        assert 'calendar.google.com/calendar/r/eventedit?' in link.get_attribute('href')
        # Inspect the handoff without saving anything to a real Google account.
        page.get_by_role('link',name='Calendar options & how copies work').click()
        expect(page.get_by_role('heading',name='Add deadlines to Google Calendar.')).to_be_visible()
        for width in [320,375,390,430]:
            page.set_viewport_size({'width':width,'height':844})
            issues.extend((width,'calendar',issue) for issue in page.evaluate(BOUNDS))
        response=page.context.request.get(base+'/settings/calendar.ics')
        assert response.ok and response.text().count('SUMMARY:Practice daily reading due')==7
        page.goto(base+'/tasks')
        page.locator('.task-entry>summary').click()
        page.screenshot(path='.test-overhaul-browser/task-creation-calendar-mobile.png',full_page=False)
        browser.close()
    assert not errors,errors
    assert not issues,issues
    print('Task/calendar browser checks passed: one course picker, seven inclusive occurrences, Google link, bulk export and eight mobile views.')
finally:
    server.shutdown()
