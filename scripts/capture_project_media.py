"""Refresh repository screenshots using only disposable, synthetic local data.

Requires Playwright and installed Chrome. Never connects to the hosted database.
"""
import logging
import secrets
import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from extensions import db
from models import Task, User
from models.term_course import TermCourse
from services.auth_service import hash_password
from services.settings_service import get_or_create_settings
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

ROOT = Path(__file__).resolve().parents[1]


def main():
    destination = ROOT / "docs/screenshots"
    destination.mkdir(exist_ok=True)
    app = create_app({"TESTING": True, "SECRET_KEY": secrets.token_hex(32),
                      "SQLALCHEMY_DATABASE_URI": "sqlite://"})
    # Reuse the sample fixture, then make it a normal local account without a tour.
    client = app.test_client()
    client.post("/demo")
    password = secrets.token_urlsafe(24)
    now = datetime.now(timezone.utc)
    with app.app_context():
        user = User.query.one()
        user.username = "project-preview"
        user.password_hash = hash_password(password)
        user_id = user.id
        profile = user.profile
        settings = get_or_create_settings(user)
        settings.dashboard_mode = "standard"
        settings.default_task_minutes = 45
        for course in profile.planned_courses:
            course.status = "in_progress"
        Task.query.delete()
        def add(title, subject, days, minutes, **kwargs):
            task = Task(student_profile_id=profile.id, title=title, subject=subject,
                        task_type="Homework", due_at=now+timedelta(days=days),
                        estimated_minutes=minutes, **kwargs)
            db.session.add(task)
            db.session.flush()
            return task
        add("Practice derivatives and tangent lines", "AP Calculus AB", 1, 45,
            status="in_progress", planned_start_at=now-timedelta(minutes=20),
            started_at=now-timedelta(minutes=15))
        add("Revise the rhetorical analysis introduction", "AP English Language", 2, 50)
        add("Read chapter 4 and make retrieval cards", "Introduction to Psychology", 3, 40)
        add("Build a temperature converter", "Introduction to Computer Programming", 4, 75)
        project = add("Cleaner energy for our community", "Chemistry", 7, 180)
        project_id = project.id
        for i, (title, minutes) in enumerate([
            ("Choose a research question",25), ("Annotate three sources",45),
            ("Compare renewable energy options",50), ("Build slides and rehearse",60)]):
            add(title,"Chemistry",i+2,minutes,parent_task_id=project_id,
                status="completed" if i==0 else "not_started",
                completed_at=now-timedelta(hours=2) if i==0 else None,
                actual_minutes=25 if i==0 else None)
        for i in range(8):
            end = now-timedelta(days=i+1)
            add(["Review limits and continuity","Annotate a persuasive speech",
                 "Balance chemical equations","Practice retrieval cards"][i%4],
                ["AP Calculus AB","AP English Language","Chemistry","Introduction to Psychology"][i%4],
                -i,35,status="completed",planned_start_at=end-timedelta(hours=2),
                started_at=end-timedelta(hours=2)+timedelta(minutes=[0,10,25,-10][i%4]),
                completed_at=end,actual_minutes=[30,40,35,25][i%4])
        for title,code,institution in [
            ("Introduction to Psychology","PSYC 1101","139940"),
            ("Introduction to Computer Programming","CIST 1305","140012")]:
            db.session.add(TermCourse(user_id=user.id,title=title,course_code=code,
                institution_id=institution,term="Fall 2026",credits=3,weekly_hours=5,
                enrollment_type="dual",school_year=11,status="in_progress"))
        db.session.commit()
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    server=make_server("127.0.0.1",0,app,threaded=True)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    origin=f"http://127.0.0.1:{server.server_port}"
    errors=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(channel="chrome")
            context=browser.new_context(viewport={"width":1440,"height":960},device_scale_factor=1)
            page=context.new_page()
            page.on("pageerror",lambda e: errors.append(str(e)))
            def shot(name,route=None):
                if route:
                    assert page.goto(origin+route).status==200,route
                if name == "dual-enrollment":
                    page.locator("#college-entry > summary").click()
                if name == "college":
                    page.locator(".term-grid").evaluate("(el) => window.scrollTo(0, el.offsetTop - 110)")
                page.evaluate("document.fonts.ready")
                page.screenshot(path=str(destination/(("dashboard-current-2026-09-30" if name=="dashboard" else name)+".png")),animations="disabled")
                print("Captured "+name,flush=True)
            shot("landing","/")
            page.evaluate("document.documentElement.dataset.theme='dark'")
            shot("landing-dark")
            page.set_viewport_size({"width":390,"height":844})
            shot("landing-mobile","/")
            page.set_viewport_size({"width":1440,"height":960})
            page.goto(origin+"/login")
            page.locator("[name=username]").fill("project-preview")
            page.locator("[name=password]").fill(password)
            page.locator("button[type=submit]").click()
            page.wait_for_url("**/dashboard")
            for name,route in [
                ("dashboard","/dashboard"),("tasks","/tasks"),
                ("subtasks",f"/tasks/{project_id}"),("courses","/courses"),
                ("dual-enrollment","/courses?course_source=dual"),
                ("comparison","/courses/compare?id=SCI_AP_CHEMISTRY&id=SCI_AP_BIOLOGY"),
                ("four-year-plan","/courses/plan"),("settings","/settings"),
                ("calendar","/calendar")]:
                shot(name,route)
            shot("tasks-by-course","/tasks?view=courses")
            shot("bulk-selection","/tasks/select")
            shot("onboarding","/onboarding")
            page.goto(origin+"/tasks")
            menu=page.locator(".task-menu").filter(has=page.locator(".reschedule-control")).first
            menu.locator(":scope > summary").click()
            menu.locator(".reschedule-control > summary").click()
            menu.scroll_into_view_if_needed()
            shot("rescheduling")
            page.goto(origin+"/tasks")
            page.locator("#completed-tasks > summary").click()
            page.locator("#completed-tasks").evaluate("(el) => window.scrollTo(0, el.offsetTop - 100)")
            shot("completed-tasks")
            page.set_viewport_size({"width":390,"height":844})
            shot("mobile-dashboard","/dashboard")
            page.set_viewport_size({"width":1440,"height":960})
            with app.app_context():
                settings=get_or_create_settings(db.session.get(User,user_id))
                settings.academic_context="college"
                settings.college_program="Computer Science"
                settings.college_term="Fall 2026"
                settings.term_credit_goal=15
                for course in TermCourse.query.filter_by(user_id=user_id):
                    course.enrollment_type="college"
                    course.school_year=None
                    course.requirement_area="elective"
                db.session.add(TermCourse(user_id=user_id,title="College Algebra",
                    course_code="MATH 1111",institution_id="139940",
                    term="Spring 2027",credits=4,weekly_hours=7,
                    enrollment_type="college",status="planned"))
                db.session.commit()
            shot("college","/terms")
            page.goto(origin+"/")
            # Use a fresh signed-out context to capture the real tutorial entry.
            tutorial=browser.new_page(viewport={"width":1440,"height":960})
            tutorial.goto(origin+"/")
            tutorial.get_by_role("button",name="Start tutorial",exact=True).first.click()
            tutorial.locator("#tutorial-show").wait_for()
            tutorial.screenshot(path=str(destination/"tutorial.png"),animations="disabled")
            assert not errors,errors
            browser.close()
    finally:
        server.shutdown()
    print("Saved 20 current screenshots; no JavaScript errors.")


if __name__=="__main__":
    main()
