"""Cross-page UI and new AI intake checks with isolated sample data."""
from browser_test_support import start_demo
import sys,threading,logging
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
from extensions import db
from models import User,Task
from services.auth_service import hash_password
from services import ai_planning, ai_task_batch
from models.ai_planning import AIQuota
from tests.test_ai_task_batch import samples
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright,expect
from audit_responsive import BOUNDS
app=create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":"sqlite://","SECRET_KEY":"ui-check",
               "GROQ_API_KEY":"stub","AI_ENABLED":True})
client=app.test_client();start_demo(client)
with app.app_context():
 user=User.query.one();user.username="refresh-preview";user.password_hash=hash_password("sample-refresh-password")
 tid=Task.query.filter_by(status="not_started").first().id
 db.session.commit()
original_assignment=ai_planning.generate_assignment
ai_planning.generate_assignment=lambda *args:dict(title="Energy presentation", subject="Science", due_at="2027-06-01T23:59", estimated_minutes=60, steps=[{"title":"Read the brief","minutes":20},{"title":"Draft and self-check","minutes":40}])
original_batch=ai_task_batch.generate
ai_task_batch.generate=lambda *args:samples()
original=ai_planning.generate
ai_planning.generate=lambda *args:[{"title":"Read the brief","minutes":20},{"title":"Draft and revise","minutes":40}]
logging.getLogger("werkzeug").setLevel(logging.ERROR)
server=make_server("127.0.0.1",0,app,threaded=True)
threading.Thread(target=server.serve_forever,daemon=True).start()
base=f"http://127.0.0.1:{server.server_port}"
out=Path(".test-workspace-refresh");out.mkdir(exist_ok=True)
errors=[];issues=[];views=0
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(channel="chrome")
  page=browser.new_page(viewport={"width":1440,"height":960})
  page.on("pageerror",lambda e:errors.append(str(e)))
  page.goto(base+"/login");page.locator("[name=username]").fill("refresh-preview")
  page.locator("[name=password]").fill("sample-refresh-password")
  page.locator("button[type=submit]").click();page.wait_for_url("**/dashboard")
  for route in ["/dashboard","/tasks","/tasks?view=courses",f"/tasks/{tid}",
                "/courses","/courses/plan","/settings","/onboarding","/calendar","/tasks/ai/new","/planner"]:
   page.goto(base+route)
   for width in [320,390,1440]:
    page.set_viewport_size({"width":width,"height":960})
    issues.extend([{"route":route,"width":width,**x} for x in page.evaluate(BOUNDS)])
    views+=1
   if route in ["/dashboard","/tasks","/courses","/settings"]:
    page.screenshot(path=str(out/(route.strip("/")+".png")),animations="disabled")
  page.goto(base+"/settings")
  expect(page.locator(".settings-group")).to_have_count(7)
  assert page.locator("#workspace-settings").locator("[name=theme]").count()==1
  appearance=page.locator(".settings-group").filter(has=page.locator("[name=theme]"))
  appearance.locator(":scope > summary").click()
  page.locator("[name=theme]").select_option("dark")
  page.get_by_role("button",name="Save all settings").click()
  expect(page.locator("html")).to_have_attribute("data-theme","dark")
  for theme in ["dark","high-contrast"]:
   page.evaluate("(theme)=>document.documentElement.dataset.theme=theme",theme)
   page.set_viewport_size({"width":390,"height":960})
   issues.extend(page.evaluate(BOUNDS));views+=1
   page.screenshot(path=str(out/("settings-"+theme+".png")),animations="disabled")
  page.goto(base+"/tasks/ai/new?classic=1")
  page.locator("[name=description]").fill("Prepare a renewable energy presentation")
  page.locator("[name=consent]").check()
  page.get_by_role("button",name="Draft my assignment").click()
  expect(page.locator("[name=parent_title]")).to_be_visible()
  page.locator("[name=parent_title]").fill("Renewable energy presentation")
  page.get_by_text("Spread the work across study sessions",exact=True).click()
  page.locator("[name=first_start]").fill("2027-05-20T17:00")
  page.locator("[name=daily_minutes]").fill("30")
  page.get_by_role("button",name="Preview study sessions").click()
  expect(page.locator("[name=start_2]")).to_have_value("2027-05-22T17:00")
  for width in [320,390,1440]:
   page.set_viewport_size({"width":width,"height":960})
   issues.extend(page.evaluate(BOUNDS));views+=1
  page.get_by_role("button",name="Create assignment & steps").click()
  expect(page.get_by_role("heading",name="Renewable energy presentation",exact=True)).to_be_visible()
  with app.app_context():
   task=Task.query.filter_by(title="Renewable energy presentation").one()
   assert len(task.children)==3 and all(child.planned_start_at for child in task.children)
  with app.app_context():
   AIQuota.query.delete();db.session.commit()
  page.goto(base+"/tasks/ai/new")
  page.locator('[name=description]').fill('Math homework and a history essay')
  page.locator('[name=output_format]').select_option('mixed')
  page.locator('[name=detail_style]').select_option('detailed')
  page.locator('[name=consent]').check()
  page.get_by_role('button',name='Draft my tasks').click()
  expect(page.get_by_role('heading',name='Review drafted tasks')).to_be_visible()
  page.locator('[name=save_as_1]').select_option('separate')
  page.get_by_role('button',name='Preview selection').click()
  expect(page.get_by_role('status')).to_contain_text('3 tasks')
  for width in [320,390,1440]:
   page.set_viewport_size({'width':width,'height':960})
   issues.extend(page.evaluate(BOUNDS));views+=1
  page.screenshot(path=str(out/'ai-batch-review.png'),full_page=True)
  page.get_by_role('button',name='Save selected tasks').click()
  page.wait_for_url('**/tasks')
  with app.app_context():
   assert Task.query.filter_by(title='Math exercises').one().parent_task_id is None
   assert Task.query.filter_by(title='History essay').count()==0
   assert Task.query.filter_by(title='Research').one().parent_task_id is None
  browser.close()
 assert not errors,errors
 assert not issues,issues
 print(f"Passed {views} cross-page responsive checks, settings save, themes, and AI assignment creation.")
finally:
 ai_task_batch.generate=original_batch
 ai_planning.generate=original
 ai_planning.generate_assignment=original_assignment
 server.shutdown()
