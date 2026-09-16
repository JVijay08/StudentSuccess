"""Browser regression for the full workspace and per-submission privacy checks."""
import re
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from playwright.sync_api import sync_playwright, expect
from werkzeug.serving import make_server

from app import create_app


def main():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://"})
    server = make_server("127.0.0.1", 0, app)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f"http://127.0.0.1:{server.server_port}"
    screenshots = Path(".test-full-workspace-visual")
    screenshots.mkdir(exist_ok=True)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True)
            context = browser.new_context(viewport={"width":1440, "height":1000})
            page = context.new_page()
            errors = []
            posts = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("request", lambda request: posts.append(request.url) if request.method == "POST" else None)
            page.goto(origin + "/register")
            page.locator("#welcome-close").click()
            expect(page.get_by_role("link", name="Use the browser-only planner")).to_be_visible()
            page.locator("[name=understood]").check()
            page.get_by_role("button", name="Create my private planner").click()
            page.locator("input[type=checkbox]").check()
            page.get_by_role("button", name="Continue to my planner").click()
            expect(page.locator('nav a[href="/courses"]')).to_be_visible()
            page.goto(origin + "/tasks")
            page.locator("[name=title]").fill("Sample algebra")
            page.locator("[name=due_at]").fill("2027-06-15T15:00")
            page.locator("[name=difficulty]").select_option("medium")
            page.locator("[name=interest_level]").select_option("medium")
            confirm = page.locator("[name=nonpersonal_confirmed]")
            posts.clear()
            page.get_by_role("button", name="Add task", exact=True).click()
            assert not posts
            assert not confirm.is_checked()
            confirm.check()
            page.locator("[name=subject]").fill("Math")
            assert not confirm.is_checked()
            confirm.check()
            # Silent/autofill edits cannot reuse acknowledgment of old values.
            page.evaluate("document.querySelector('[name=title]').value = 'Sample algebra practice'")
            page.get_by_role("button", name="Add task", exact=True).click()
            assert not posts
            assert not confirm.is_checked()
            confirm.check()
            page.get_by_role("button", name="Add task", exact=True).click()
            expect(page.locator(".task-card")).to_have_count(1)
            assert not page.locator("[name=nonpersonal_confirmed]").is_checked()
            page.get_by_role("link", name="Edit", exact=True).click()
            confirm = page.locator("[name=nonpersonal_confirmed]")
            assert not confirm.is_checked()
            page.locator("[name=title]").fill("Updated sample task")
            confirm.check()
            page.get_by_role("button", name="Save changes", exact=True).click()
            expect(page.locator(".task-card")).to_contain_text("Updated sample task")
            page.screenshot(path=str(screenshots / "tasks-desktop.png"), full_page=True)
            page.set_viewport_size({"width":390, "height":844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(screenshots / "tasks-mobile.png"), full_page=True)
            page.goto(origin + "/courses")
            expect(page.locator(".course-card").first).to_be_visible()
            page.locator("[name=q]").fill("Calculus")
            posts.clear()
            page.get_by_role("button", name="Apply filters").click()
            assert not posts
            page.locator("[name=nonpersonal_confirmed]").check()
            page.get_by_role("button", name="Apply filters").click()
            expect(page.locator(".course-card").first).to_contain_text(re.compile("calculus", re.I))
            assert "q=" not in page.url
            page.locator("[name=q]").fill("")
            assert not page.locator("[name=nonpersonal_confirmed]").is_checked()
            page.get_by_role("button", name="Apply filters").click()
            expect(page.locator(".course-card").first).to_be_visible()
            assert not errors, errors
            browser.close()
        print("Browser checks passed: full dashboard/catalog, optional browser link, task and search confirmations, reset on edits, server navigation, mobile layout.")
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
