from browser_test_support import start_demo
import sys,threading,logging,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path('scripts').resolve()))
from app import create_app
from extensions import db
from models import Task
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright,expect
from audit_responsive import BOUNDS
logging.getLogger('werkzeug').setLevel(logging.ERROR)
app=create_app({'TESTING':True,'SQLALCHEMY_DATABASE_URI':'sqlite://'})
server=make_server('127.0.0.1',0,app,threaded=True)
threading.Thread(target=server.serve_forever,daemon=True).start()
base=f'http://127.0.0.1:{server.server_port}'
issues=[];errors=[]
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(channel='chrome',headless=True)
  page=browser.new_page(viewport={'width':390,'height':844})
  page.on('pageerror',lambda e:errors.append(str(e)))
  start_demo(page.context.request, base)
  with app.app_context(): db.session.query(Task).delete();db.session.commit()
  page.goto(base+'/dashboard')
  expect(page.get_by_role('link',name='Add a task',exact=True)).to_have_count(1)
  page.context.request.post(base+'/tasks',form={'title':'Card redesign check','due_at':'2027-12-01','estimated_minutes':'10080','nonpersonal_confirmed':'yes'})
  page.goto(base+'/dashboard')
  expect(page.get_by_role('link',name='Add a task',exact=True)).to_have_count(1)
  card=page.locator('.task-overview').first
  expect(card.locator('[name=actual_minutes]')).not_to_be_visible()
  card.locator('.task-menu>summary').click()
  card.locator('.reschedule-control>summary').click()
  card.get_by_role('button',name='Tomorrow, 9 AM',exact=True).click()
  expect(page.get_by_role('button',name='Undo schedule change')).to_be_visible()
  page.get_by_role('button',name='Undo schedule change').click()
  page.goto(base+'/dashboard')
  page.get_by_role('button',name='Start this task',exact=True).click()
  expect(page.locator('.task-state').first).to_have_text('In progress')
  expect(page.locator('[name=actual_minutes]')).not_to_be_visible()
  for width in [320,390,768,1440]:
   page.set_viewport_size({'width':width,'height':844})
   for path in ['/dashboard','/tasks']:
    page.goto(base+path)
    issues.extend([width,path,i] for i in page.evaluate(BOUNDS))
    menu=page.locator('.task-menu').first
    menu.locator(':scope>summary').click()
    menu.get_by_text('Record time & complete',exact=True).click()
    issues.extend([width,path,'open',i] for i in page.evaluate(BOUNDS))
    menu.locator('[name=actual_minutes]').focus()
    page.keyboard.press('Escape')
    expect(menu).not_to_have_attribute('open','')
  for theme in ['dark','high-contrast']:
   page.set_viewport_size({'width':320,'height':844})
   for path in ['/dashboard','/tasks']:
    page.goto(base+path)
    page.evaluate("theme=>Object.assign(document.documentElement.dataset,{theme,textScale:'200'})",theme)
    page.locator('.task-menu>summary').first.click()
    page.locator('.task-menu').first.get_by_text('Record time & complete',exact=True).click()
    issues.extend([theme,path,'200%',i] for i in page.evaluate(BOUNDS))
  page.goto(base+'/dashboard')
  page.get_by_role('button',name='Complete task',exact=True).click()
  with app.app_context():
   task=Task.query.one();assert task.status=='completed' and task.actual_minutes is None
  page.goto(base+'/dashboard')
  expect(page.get_by_role('link',name='Add a task',exact=True)).to_have_count(1)
  expect(page.get_by_role('heading',name='You are caught up.',exact=True)).to_be_visible()
  browser.close()
 print(json.dumps({'issues':issues,'javascript_errors':errors}))
 assert not issues and not errors
finally: server.shutdown()
