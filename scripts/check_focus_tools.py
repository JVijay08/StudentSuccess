"""Native micro-start, timer persistence, parked notes, and modal keyboard checks."""
from browser_test_support import start_demo
import sys,threading,logging
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
from extensions import db
from models import User,Task
from services.auth_service import hash_password
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright,expect
from audit_responsive import BOUNDS
app=create_app({'TESTING':True,'SECRET_KEY':'focus-browser-check','SQLALCHEMY_DATABASE_URI':'sqlite://'})
client=app.test_client();start_demo(client)
with app.app_context():
 user=User.query.one();user.username='focus-preview';user.password_hash=hash_password('focus-sample-password');db.session.commit()
logging.getLogger('werkzeug').setLevel(logging.ERROR)
server=make_server('127.0.0.1',0,app,threaded=True)
threading.Thread(target=server.serve_forever,daemon=True).start()
base=f'http://127.0.0.1:{server.server_port}'
errors=[]
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(channel='chrome');page=browser.new_page()
  page.on('pageerror',lambda e:errors.append(str(e)))
  def audit_dialog():
   page.emulate_media(reduced_motion='reduce')
   page.add_script_tag(path='.test-policy-audit/axe.min.js')
   for theme in ['light','dark','high-contrast']:
    page.evaluate('(theme)=>document.documentElement.dataset.theme=theme',theme)
    violations=page.evaluate("async()=> (await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})).violations")
    assert not violations,violations
   page.evaluate("document.documentElement.dataset.theme='light'")

  page.goto(base+'/login');page.locator('[name=username]').fill('focus-preview');page.locator('[name=password]').fill('focus-sample-password');page.locator('button[type=submit]').click();page.wait_for_url('**/dashboard')
  page.get_by_role('button',name='Just 5 minutes').click()
  expect(page.locator('#focus-dialog')).to_be_visible()
  audit_dialog()
  with app.app_context(): assert Task.query.filter_by(status='in_progress').count()>=1
  page.locator('#focus-pause').click();expect(page.locator('#focus-status')).to_contain_text('Paused')
  value=page.locator('#focus-time').inner_text()
  page.reload();page.locator('#resume-focus').click();expect(page.locator('#focus-time')).to_have_text(value)
  page.keyboard.press('Tab');assert page.evaluate("document.activeElement.closest('#focus-dialog') !== null")
  page.locator('#focus-dialog [data-park-open]').click()
  audit_dialog()
  page.locator('#park-text').fill('<script>not executable</script> Remember library books')
  page.locator('#park-form button').click();expect(page.locator('#park-list')).to_contain_text('Remember library books')
  assert page.locator('#park-list script').count()==0
  for width in [320,390,1440]:
   page.set_viewport_size({'width':width,'height':900});assert not page.evaluate(BOUNDS)
  page.keyboard.press('Escape');expect(page.locator('#park-dialog')).not_to_be_visible();expect(page.locator('#focus-dialog')).to_be_visible()
  page.keyboard.press('Escape');expect(page.locator('#focus-dialog')).not_to_be_visible()
  page.reload();page.locator('.focus-utilities [data-park-open]').click();expect(page.locator('#park-list')).to_contain_text('Remember library books');page.locator('#park-clear').click();expect(page.locator('#park-list li')).to_have_count(0);page.keyboard.press('Escape')
  page.evaluate("""() => {const k='studentsuccess-focus-'+document.querySelector('[data-focus-user]').dataset.focusUser; const s=JSON.parse(sessionStorage.getItem(k));s.paused=false;s.end=Date.now()-1000;sessionStorage.setItem(k,JSON.stringify(s));}""")
  page.reload();page.locator('#resume-focus').click();expect(page.locator('#focus-time')).to_have_text('00:00');expect(page.locator('#focus-status')).to_contain_text('Five minutes done')
  page.locator('#focus-end').click();expect(page.locator('#resume-focus')).not_to_be_visible()
  with app.app_context(): assert Task.query.filter_by(status='in_progress').count()>=1
  browser.close()
 assert not errors,errors
 print('Focus checks passed: native start, pause/reload, elapsed timer, no automatic completion, tab notes, safe text, modal keyboard, three viewport sizes.')
finally:server.shutdown()
