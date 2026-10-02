"""Exercise AI review with a stub provider; no external requests or credentials."""
import logging
import sys
import threading
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
from extensions import db
from models import User,Task
from services.auth_service import hash_password
from services import ai_planning
from playwright.sync_api import sync_playwright,expect
from werkzeug.serving import make_server
from audit_responsive import BOUNDS

app=create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":"sqlite://",
                "SECRET_KEY":"isolated-browser-check","GROQ_API_KEY":"stub-only","AI_ENABLED":True})
client=app.test_client();client.post("/demo")
with app.app_context():
    user=User.query.one();user.username="ai-browser";user.password_hash=hash_password("sample-browser-password")
    task=Task.query.filter_by(status="not_started").first();task_id=task.id;db.session.commit()
original=ai_planning.generate
ai_planning.generate=lambda description,budget:[
    {"title":"Read the assignment requirements","minutes":15},
    {"title":"Work through the first problems","minutes":35}]
logging.getLogger("werkzeug").setLevel(logging.ERROR)
server=make_server("127.0.0.1",0,app,threaded=True)
threading.Thread(target=server.serve_forever,daemon=True).start()
base=f"http://127.0.0.1:{server.server_port}"
errors=[];issues=[]
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(channel="chrome")
        page=browser.new_page(viewport={"width":1440,"height":960})
        page.on("pageerror",lambda e:errors.append(str(e)))
        page.goto(base+"/login")
        page.locator("[name=username]").fill("ai-browser")
        page.locator("[name=password]").fill("sample-browser-password")
        page.locator("button[type=submit]").click()
        page.wait_for_url("**/dashboard")
        page.goto(base+f"/tasks/{task_id}")
        page.get_by_role("link",name="Suggest steps with AI").click()
        for width in [320,390,1440]:
            page.set_viewport_size({"width":width,"height":960})
            issues.extend(page.evaluate(BOUNDS))
        page.locator("[name=consent]").check()
        page.get_by_role("button",name="Suggest steps",exact=True).click()
        expect(page.get_by_role("heading",name="Make these steps your own.")).to_be_visible()
        for width in [320,390,1440]:
            page.set_viewport_size({"width":width,"height":960})
            issues.extend(page.evaluate(BOUNDS))
        page.locator("[name=title_0]").fill("Check the rubric")
        page.locator("[name=nonpersonal_confirmed]").check()
        page.get_by_role("button",name="Add selected steps").click()
        expect(page.get_by_role("link",name="Check the rubric",exact=True)).to_be_visible()
        with app.app_context():
            assert Task.query.filter_by(parent_task_id=task_id).count()==2
        browser.close()
    assert not errors,errors
    assert not issues,issues
    print("AI draft, edit, apply, and 6 responsive views passed without JavaScript errors.")
finally:
    ai_planning.generate=original
    server.shutdown()
