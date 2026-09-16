"""Optional browser smoke test: pip install playwright; requires local Chrome.

Run from the repository root with: python scripts/check_local_planner.py
Uses an isolated in-memory database and a temporary browser profile.
"""
import json
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

from app import create_app


def main():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://"})
    server = make_server("127.0.0.1", 0, app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True)
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(origin + "/planner")
            page.locator("#welcome-close").click()
            requests = []
            page.on("request", lambda request: requests.append(request.url))
            page.locator("#task-title").fill("<img src=x onerror=alert(1)> Algebra")
            page.locator("#task-due").fill("2027-05-01T16:00")
            page.locator("#task-start").fill("2027-05-01T15:00")
            page.locator("#task-form [name=nonpersonal_confirmed]").check()
            page.locator("#save-task").click()
            assert page.locator("#tasks h3").inner_text().startswith("<img")
            assert page.locator("#tasks img").count() == 0
            page.reload()
            assert page.locator("#tasks h3").count() == 1
            requests.clear()
            page.get_by_role("button", name="Start", exact=True).click()
            assert "Already in progress" in page.locator("#next-reason").inner_text()
            page.get_by_role("button", name="Complete", exact=True).click()
            assert "All caught up" in page.locator("#next-heading").inner_text()
            page.locator("#show-completed").check()
            page.get_by_role("button", name="Reopen", exact=True).click()
            page.get_by_role("button", name="Edit", exact=True).click()
            page.locator("#task-title").fill("Updated algebra")
            page.locator("#task-form [name=nonpersonal_confirmed]").check()
            page.locator("#save-task").click()
            page.locator("#budget").fill("5")
            page.get_by_role("button", name="Save availability").click()
            page.locator("#course-title").fill("Algebra")
            page.locator("#course-hours").fill("7")
            page.locator("#course-form [name=nonpersonal_confirmed]").check()
            page.get_by_role("button", name="Add course", exact=True).click()
            assert "2 hours over" in page.locator("#courses").inner_text()
            with page.expect_download() as download:
                page.get_by_role("button", name="Download backup", exact=True).click()
            backup = Path(download.value.path()).read_bytes()
            assert json.loads(backup)["tasks"][0]["title"] == "Updated algebra"
            page.on("dialog", lambda dialog: dialog.accept())
            page.locator("#clear").click()
            assert page.locator("#tasks h3").count() == 0
            page.locator("#import").set_input_files({"name":"backup.json", "mimeType":"application/json", "buffer":backup})
            page.wait_for_function("document.querySelectorAll('#tasks h3').length === 1")
            assert "Updated algebra" in page.locator("#tasks").inner_text()
            page.locator("#import").set_input_files({"name":"bad.json", "mimeType":"application/json", "buffer":b'{"version":1}'})
            page.wait_for_function("document.querySelector('#message').textContent.includes('not a valid')")
            assert page.locator("#tasks h3").count() == 1
            assert not requests, f"Planner actions sent network requests: {requests}"
            # Only the public catalog bundle is fetched; filters and plans remain local.
            page.locator("#load-catalog").click()
            page.wait_for_function("!document.querySelector('#catalog-filter').hidden")
            assert page.locator("#catalog-choice option").count() > 20
            requests.clear()
            page.locator("#catalog-search").fill("Statistics")
            page.locator("#catalog-filter [name=nonpersonal_confirmed]").check()
            page.get_by_role("button", name="Apply filters", exact=True).click()
            card = page.locator("#catalog-results article").first
            assert "Statistics" in card.inner_text()
            card.get_by_role("button", name="Compare course", exact=True).click()
            assert page.locator("#course-comparison article").count() == 1
            card.locator("select").select_option("11")
            card.locator("input[type=number]").fill("4")
            card.get_by_role("button", name="Add to four-year plan").click()
            assert page.evaluate("JSON.parse(localStorage.getItem('studentsuccess.local-plan.v1')).courses.some(c => c.year === 11 && c.catalog === 'national')")
            assert not requests, f"Catalog selections leaked through requests: {requests}"
            # A stale tab must not overwrite another tab's saved plan.
            other = context.new_page()
            other.goto(origin + "/planner")
            page.locator("#budget").fill("10")
            page.get_by_role("button", name="Save availability").click()
            other.locator("#budget").fill("20")
            other.get_by_role("button", name="Save availability").click()
            assert "another tab" in other.locator("#message").inner_text()
            assert page.evaluate("JSON.parse(localStorage.getItem('studentsuccess.local-plan.v1')).budget") == 10
            other.close()
            # Corrupted browser data remains recoverable.
            page.evaluate("localStorage.setItem('studentsuccess.local-plan.v1', 'broken')")
            page.reload()
            assert page.locator("#original-download").is_visible()
            assert page.evaluate("localStorage.getItem('studentsuccess.local-plan.v1')") == "broken"
            # Saving failures must be explicit, and in-memory work remains exportable.
            page.locator("#clear").click()
            page.evaluate("() => { Storage.prototype.setItem = () => { throw new Error('quota'); }; }")
            page.locator("#task-title").fill("Memory only")
            page.locator("#task-due").fill("2027-05-01T16:00")
            page.locator("#task-form [name=nonpersonal_confirmed]").check()
            page.locator("#save-task").click()
            assert "only in memory" in page.locator("#storage-state").inner_text()
            assert page.locator("#tasks h3").inner_text() == "Memory only"
            page.set_viewport_size({"width":390, "height":844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            screenshot_dir = Path(".test-browser-planner-visual")
            screenshot_dir.mkdir(exist_ok=True)
            page.evaluate("scrollTo(0,0)")
            page.screenshot(path=str(screenshot_dir / "mobile.png"), full_page=True)
            page.set_viewport_size({"width":1440, "height":1000})
            page.evaluate("scrollTo(0,0)")
            assert page.locator(".grid .card").first.bounding_box()["width"] > 250
            page.screenshot(path=str(screenshot_dir / "desktop.png"), full_page=True)
            assert not errors, errors
            browser.close()
        print("Browser checks passed: tasks, persistence, courses, backup/restore, invalid imports, no data requests, tab conflicts, corruption, storage failure, mobile width.")
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
