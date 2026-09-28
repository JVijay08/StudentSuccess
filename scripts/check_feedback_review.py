"""Isolated browser regression checks for Test 1 feedback."""
import sys
import threading
import logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from extensions import db
from models import Task, TermCourse, User
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright, expect
from audit_responsive import BOUNDS

logging.getLogger('werkzeug').setLevel(logging.ERROR)
app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite://'})
server = make_server('127.0.0.1', 0, app, threaded=True)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f'http://127.0.0.1:{server.server_port}'
issues, errors = [], []
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel='chrome', headless=True)
        page = browser.new_page(viewport={'width':390,'height':844})
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.context.request.post(base+'/demo')
        with app.app_context():
            user = User.query.first()
            db.session.add(TermCourse(user_id=user.id, title='Dual biology', term='Fall', weekly_hours=3, enrollment_type='dual', school_year=11, status='in_progress'))
            db.session.commit()
            task_id = Task.query.first().id
        page.goto(base+'/tasks')
        page.locator('.task-entry>summary').click()
        page.locator('[name=saved_course]').select_option('Dual biology')
        expect(page.locator('#task-form [name=subject]')).to_be_hidden()
        page.goto(base+'/courses?scope=ga')
        expect(page.locator('#catalog-scope')).to_have_value('ga')
        page.get_by_text('Filter courses',exact=True).click()
        form=page.locator('.filter-panel form')
        form.locator('[name=q]').fill('Personal Fitness')
        form.locator('[name=nonpersonal_confirmed]').check()
        form.get_by_role('button',name='Apply filters',exact=True).first.click()
        card = page.locator('#course-GA_FCS_FITNESS')
        card.get_by_role('button',name='Add to plan',exact=True).click()
        card.get_by_role('button',name='Add course',exact=True).click()
        assert page.url.endswith('#course-GA_FCS_FITNESS')
        expect(page.locator('#course-GA_FCS_FITNESS .saved-label')).to_be_visible()
        page.goto(base+'/courses?course_source=dual')
        expect(page.get_by_role('heading',name='1. Find your college')).to_be_visible()
        page.locator('[name=college_q]').fill('Alabama')
        page.get_by_role('button',name='Find colleges',exact=True).click()
        expect(page.locator('[data-college-feedback]')).to_have_attribute('data-state','done')
        assert page.locator('#term-form [name=institution_id] option').count() > 1
        page.goto(base+f'/tasks/{task_id}')
        page.get_by_role('button',name='Create',exact=False).click()
        expect(page.locator('.step-trail')).to_be_visible()
        page.get_by_role('button',name='Complete step 1',exact=True).click()
        expect(page.get_by_role('button',name='Reopen step 1',exact=True)).to_be_visible()
        for width in [320,390,768,1440]:
            page.set_viewport_size({'width':width,'height':844})
            for path in ['/courses?scope=ga','/courses?scope=ap','/courses?course_source=dual',f'/tasks/{task_id}','/tasks']:
                page.goto(base+path)
                issues.extend((width,path,i) for i in page.evaluate(BOUNDS))
        page.set_viewport_size({'width':390,'height':844})
        page.goto(base+f'/tasks/{task_id}')
        page.screenshot(path='.test-overhaul-browser/feedback-task-390.png',full_page=True)
        page.goto(base+'/courses?scope=ga')
        page.screenshot(path='.test-overhaul-browser/feedback-courses-390.png',full_page=False)
        page.goto(base+'/dashboard')
        page.evaluate("document.getElementById('session-warning').hidden=false")
        page.route('**/session/extend', lambda route: route.fulfill(status=503,body='Unavailable'))
        page.locator('#extend-session').click()
        expect(page.locator('#session-warning-message')).to_contain_text('could not reconnect')
        expect(page.locator('#extend-session')).to_be_enabled()
        page.unroute('**/session/extend')
        page.route('**/session/extend', lambda route: route.fulfill(status=401,body='Expired'))
        page.locator('#extend-session').click()
        expect(page.locator('#session-warning-message')).to_contain_text('session has ended')
        expect(page.locator('#session-recovery')).to_be_visible()
        page.unroute('**/session/extend')
        page.locator('#extend-session').click()
        expect(page.locator('#session-warning')).to_be_hidden()
        browser.close()
    assert not errors, errors
    assert not issues, issues
    print('Feedback browser checks passed: course anchor, college search, saved picker, task steps, session recovery, 20 responsive views.')
finally:
    server.shutdown()
