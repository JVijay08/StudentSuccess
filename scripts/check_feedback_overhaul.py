"""Exercise new planner flows in desktop/mobile Chrome against an isolated database."""
import json
import logging
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from playwright.sync_api import sync_playwright, expect
from werkzeug.serving import make_server


def main():
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://"})
    server = make_server("127.0.0.1", 0, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f"http://127.0.0.1:{server.server_port}"
    destination = Path(".test-overhaul-browser")
    destination.mkdir(exist_ok=True)
    errors, overflow = [], []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True)
            context = browser.new_context(viewport={"width": 390, "height": 844})
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(origin + "/planner")
            # Readability regression: old dark-card text must not survive on white surfaces.
            contrast = page.locator("#next-reason").evaluate(r"""e => {
                const lum = c => {
                    const rgb = c.match(/[\d.]+/g).slice(0,3).map(v => {
                        v = Number(v)/255; return v <= .04045 ? v/12.92 : ((v+.055)/1.055)**2.4;
                    });
                    return rgb[0]*.2126 + rgb[1]*.7152 + rgb[2]*.0722;
                };
                const foreground = lum(getComputedStyle(e).color);
                const background = lum(getComputedStyle(e.closest('.focus-card')).backgroundColor);
                return (Math.max(foreground,background)+.05)/(Math.min(foreground,background)+.05);
            }""")
            assert contrast >= 4.5
            expect(page.locator("#orientation-reopen")).not_to_be_visible()
            page.locator("#orientation-dismiss").click()
            page.reload()
            assert page.locator("#planner-orientation").is_hidden()
            page.locator("#orientation-reopen").click()
            assert page.locator("#planner-orientation").is_visible()
            page.locator("#task-title").fill("Example research project")
            page.locator("#task-due").fill("2027-02-01")
            page.locator("#task-minutes").fill("1800")
            if page.locator("#task-form [name=nonpersonal_confirmed]").count(): page.locator("#task-form [name=nonpersonal_confirmed]").check()
            page.locator("#save-task").click()
            assert page.locator("#tasks h3").count() == 1
            page.locator("#task-title").fill("Example outline")
            page.locator("#task-due").fill("2027-02-01")
            page.locator("#task-minutes").fill("30")
            page.locator("#local-more summary").click()
            page.locator("#task-parent").select_option(index=1)
            if page.locator("#task-form [name=nonpersonal_confirmed]").count(): page.locator("#task-form [name=nonpersonal_confirmed]").check()
            page.locator("#save-task").click()
            assert page.locator("#next-heading").inner_text() == "Example outline"
            page.locator("#local-view").select_option("courses")
            assert page.locator("#tasks .subtask-branch h3").inner_text() == "Example outline"
            page.locator("#local-view").select_option("queue")
            page.get_by_role("button", name="Start this task", exact=True).click()
            page.once("dialog", lambda dialog: dialog.accept("35"))
            page.locator("#tasks").get_by_role("button", name="Complete", exact=True).click()
            assert page.locator("#completed-list h3").count() == 2
            page.locator("#local-completed > summary").click()
            page.locator("#completed-list").get_by_role("button", name="Reopen", exact=True).click()
            assert page.locator("#tasks h3").count() == 2
            page.locator("#local-context").select_option("college")
            assert page.locator("#catalog").is_hidden()
            assert page.locator("#courses-heading").inner_text() == "Your term plan"
            page.locator("#local-term").fill("Fall 2027")
            page.locator("#course-title").fill("Example Biology")
            page.locator("#course-hours").fill("4")
            if page.locator("#course-form [name=nonpersonal_confirmed]").count(): page.locator("#course-form [name=nonpersonal_confirmed]").check()
            page.locator("#course-form button").click()
            assert "Fall 2027" in page.locator("#courses").inner_text()
            page.reload()
            assert page.locator("#local-context").input_value() == "college"
            context.request.post(origin + "/demo")
            page.goto(origin + "/tasks#task-form")
            page.locator('[name="title"]').fill("Example long assignment")
            page.locator('[name="due_at"]').fill("2027-02-01")
            page.locator('[name="estimated_minutes"]').first.fill("1800")
            if page.locator('#task-form [name="nonpersonal_confirmed"]').count(): page.locator('#task-form [name="nonpersonal_confirmed"]').check()
            page.locator('#task-form button[type="submit"]').click()
            row = page.locator(".task-card", has=page.get_by_role("heading", name="Example long assignment", exact=True))
            row.get_by_text("Task actions", exact=True).click()
            row.get_by_role("link", name="Edit", exact=True).click()
            page.get_by_role("button", name="Create 25-minute work blocks", exact=True).click()
            assert "72 subtasks" in page.locator("main").inner_text()
            # Core actions stay exposed, while task entry remains secondary.
            page.goto(origin + "/tasks")
            assert page.locator("#task-queue").evaluate("e => e.compareDocumentPosition(document.querySelector('.task-entry')) & Node.DOCUMENT_POSITION_FOLLOWING")
            row = page.locator("#task-queue > .task-card").first
            row.get_by_role("button", name="Start now", exact=True).click()
            row = page.locator("#task-queue > .task-card").first
            expect(row.get_by_role("button", name="Complete", exact=True)).to_be_visible()
            row.get_by_role("button", name="Complete", exact=True).click()
            page.goto(origin + "/dashboard?view=today")
            assert not page.locator(".insights-disclosure").get_attribute("open")
            assert page.locator("#planner-orientation").count() == 1
            page.get_by_role("button", name="Start this task", exact=False).click()
            expect(page.locator(".complete-next-task button")).to_be_visible()
            page.locator(".complete-next-task input[name=actual_minutes]").fill("35")
            page.locator(".complete-next-task button").click()
            expect(page.locator(".complete-next-task")).to_have_count(0)
            page.goto(origin + "/tasks")
            assert page.locator("#completed-tasks").count() == 1
            assert page.locator('link[href*="studio.css"], link[href*="fieldnotes.css"], link[href*="depth.css"]').count() == 0
            for width in (320, 390, 768, 1440):
                page.set_viewport_size({"width": width, "height": 900})
                for path in ("/dashboard", "/tasks", "/settings", "/terms", "/tasks/import", "/planner", "/courses", "/courses/plan", "/courses/compare?catalog=ap&id=AP_CALCULUS_AB&id=AP_STATISTICS"):
                    response = page.goto(origin + path)
                    assert response.status == 200
                    if page.evaluate("document.documentElement.scrollWidth > innerWidth + 1"):
                        overflow.append([width, path])
                    if width in (390, 1440) and path in ("/dashboard", "/tasks", "/planner", "/courses", "/courses/plan", "/settings"):
                        page.screenshot(path=str(destination / f"{path[1:].replace('/', '-')}-{width}.png"), full_page=False)
            public = browser.new_page(viewport={"width":390,"height":844})
            public.goto(origin)
            assert public.get_by_role("button", name="Explore Demo", exact=True).first.is_visible()
            public.screenshot(path=str(destination / "landing-390.png"), full_page=True)
            assert not public.evaluate("document.documentElement.scrollWidth > innerWidth + 1")
            public.set_viewport_size({"width":1440,"height":1000})
            public.screenshot(path=str(destination / "landing-1440.png"), full_page=True)
            for path in ("/register", "/login"):
                public.goto(origin + path)
                assert not public.evaluate("document.documentElement.scrollWidth > innerWidth + 1")
                public.screenshot(path=str(destination / (path[1:] + "-1440.png")))
            for theme in ("dark", "high-contrast"):
                for path in ("/dashboard", "/tasks", "/terms"):
                    page.set_viewport_size({"width":390,"height":844})
                    page.goto(origin + path)
                    page.evaluate("theme => {document.documentElement.dataset.theme=theme;document.documentElement.dataset.motion='reduced';document.documentElement.dataset.textScale='200';}", theme)
                    if page.evaluate("document.documentElement.scrollWidth > innerWidth + 1"):
                        overflow.append([theme, "200%", path])
                    page.keyboard.press("Tab")
                    assert page.evaluate("document.activeElement !== document.body")
            browser.close()
        print(json.dumps({"javascript_errors": errors, "overflow": overflow}))
        assert not errors and not overflow
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
