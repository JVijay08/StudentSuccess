"""Audit mobile page overflow in Chrome; --check fails on regressions."""
import json
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server
from app import create_app
from extensions import db
from models import Task


def main():
    app = create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":"sqlite://"})
    server = make_server("127.0.0.1", 0, app)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    origin = f"http://127.0.0.1:{server.server_port}"
    screenshots = Path(".test-mobile-layout-visual")
    screenshots.mkdir(exist_ok=True)
    failures = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome",headless=True)
            public = browser.new_context()
            public.add_init_script("localStorage.setItem('studentsuccess.welcome.v1','seen')")
            authed = browser.new_context()
            authed.request.post(origin + "/demo")
            with app.app_context():
                task = Task.query.first()
                task.title = "Assignment" * 16
                task.subject = "Science" * 11
                task_id = task.id
                db.session.commit()
            for context, paths in ((public,["/","/register","/login","/planner"]),(authed,["/dashboard","/tasks",f"/tasks/{task_id}/edit","/courses","/courses/plan","/courses/SCI_AP_CHEMISTRY","/courses/compare?id=SCI_AP_CHEMISTRY&id=SCI_AP_BIOLOGY","/settings","/onboarding"])):
                page=context.new_page()
                for width, scale in ((320,"100"),(390,"100"),(390,"200"),(768,"100")):
                    page.set_viewport_size({"width":width,"height":844})
                    for path in paths:
                        page.goto(origin+path)
                        page.evaluate("scale => document.documentElement.dataset.textScale=scale",scale)
                        result=page.evaluate("""() => ({width:innerWidth,scroll:document.documentElement.scrollWidth, offenders:[...document.querySelectorAll('body *')].filter(e=>e.getClientRects().length && e.getBoundingClientRect().right>innerWidth+1).slice(0,12).map(e=>({tag:e.tagName,cls:e.className,width:Math.round(e.getBoundingClientRect().width)}))})""")
                        if result["scroll"] > width+1:
                            failures.append({"path":path,"scale":scale,**result})
                        if width == 390 and scale == "100" and path in ("/dashboard","/tasks","/courses","/planner","/settings"):
                            page.screenshot(path=str(screenshots/(path.strip("/")+".png")),full_page=True)
                page.close()
            browser.close()
        print(json.dumps(failures,indent=2),flush=True)
        print(f"Audited 52 page/width/text-scale combinations; {len(failures)} overflow failures.",flush=True)
        if "--check" in sys.argv:
            assert not failures, "Mobile layout overflow detected"
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
