"""Browser checks for welcome/access-code flows. Requires Playwright and Chrome."""
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
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f"http://127.0.0.1:{server.server_port}"
    screenshots = Path(".test-private-code-visual")
    screenshots.mkdir(exist_ok=True)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True)
            context = browser.new_context(viewport={"width":1440,"height":1050})
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(origin)
            assert page.locator("#welcome-dialog").is_visible()
            assert page.evaluate("document.activeElement.id") == "welcome-title"
            assert "blur" in page.evaluate("getComputedStyle(document.querySelector('#welcome-dialog'), '::backdrop').backdropFilter")
            page.screenshot(path=str(screenshots / "welcome-desktop.png"))
            page.set_viewport_size({"width":390,"height":844})
            page.screenshot(path=str(screenshots / "welcome-mobile.png"))
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.keyboard.press("Escape")
            assert not page.locator("#welcome-dialog").is_visible()
            page.reload()
            assert not page.locator("#welcome-dialog").is_visible()
            page.locator("#welcome-reopen").click()
            assert page.locator("#welcome-dialog").is_visible()
            page.locator("#welcome-dialog").get_by_role("link", name="Create a private planner", exact=True).click()
            assert page.url.endswith("/register")
            assert page.locator("input[name=username]").count() == 0
            page.locator("input[name=understood]").check()
            page.get_by_role("button", name="Create my private planner").click()
            code = page.locator("#private-code").input_value()
            assert len(code) == 46
            assert code not in page.url
            assert code not in str(context.cookies())
            assert code not in page.evaluate("JSON.stringify(localStorage)")
            with page.expect_download() as downloaded:
                page.locator("#download-code").click()
            assert code in Path(downloaded.value.path()).read_text()
            page.get_by_role("button", name="Continue to my planner").click()
            assert page.url.endswith("/access/create")  # save acknowledgment required
            page.locator("input[type=checkbox]").check()
            page.get_by_role("button", name="Continue to my planner").click()
            assert "/dashboard" in page.url
            assert "private-code planner" in page.locator("main").inner_text()
            page.goto(origin + "/onboarding")
            assert page.locator("input[name=first_name]").count() == 0
            page.goto(origin + "/settings")
            assert page.get_by_role("button", name="Replace private code").is_visible()
            # A separate browser profile reopens the same account using only the code.
            other_context = browser.new_context()
            other = other_context.new_page()
            other.goto(origin + "/login")
            other.locator("#welcome-close").click()
            other.locator("#access-code").fill(code)
            other.get_by_role("button", name="Open with a code").click()
            assert "/dashboard" in other.url
            # Rotation shows a new code and expires other sessions.
            page.locator("form[action='/access/replace'] input[name=access_code]").fill(code)
            page.get_by_role("button", name="Replace private code").click()
            new_code = page.locator("#private-code").input_value()
            assert new_code != code
            other.reload()
            assert "/login" in other.url
            other.locator("#access-code").fill(new_code)
            other.get_by_role("button", name="Open with a code").click()
            assert "/dashboard" in other.url
            # Fresh visitors can enter the prepopulated demo directly from the card.
            demo_context = browser.new_context()
            demo = demo_context.new_page()
            demo.goto(origin)
            demo.locator("#welcome-dialog").get_by_role("button", name="Try the fictional demo").click()
            assert "Fictional demo workspace" in demo.locator("main").inner_text()
            assert not errors, errors
            browser.close()
        print("Browser checks passed: blurred first-visit dialog, mobile, keyboard dismissal, remembered choice, private code creation/download, save acknowledgment, cross-device login, replacement/session revocation, fictional demo.")
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
