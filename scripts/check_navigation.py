"""Exercise actual clicks and form returns in an isolated fictional workspace."""
from browser_test_support import start_demo
import sys
import threading
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server


def canonical(url):
    parsed = urlsplit(url)
    return parsed.path, sorted(parse_qs(parsed.query).items()), parsed.fragment


def main():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://"})
    server = make_server("127.0.0.1", 0, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f"http://127.0.0.1:{server.server_port}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 1000})
            context.add_init_script("localStorage.setItem('studentsuccess.welcome.v1','seen')")
            start_demo(context.request, origin)
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            def click(label):
                page.get_by_role("link", name=label, exact=True).first.click()
                page.wait_for_load_state("networkidle")
            page.goto(origin + "/dashboard")
            assert page.locator('.sidebar nav a[href^="/settings"], .sidebar nav a[href^="/updates"]').count() == 0
            trigger = page.locator('#workspace-tools summary')
            trigger.focus()
            page.keyboard.press('Enter')
            assert page.locator('.utility-panel').is_visible()
            page.keyboard.press('Escape')
            assert not page.locator('.utility-panel').is_visible()
            assert trigger.evaluate('(element) => element === document.activeElement')
            trigger.click()
            page.locator('.utility-panel a[href^="/settings"]').click()
            page.wait_for_load_state('networkidle')
            page.locator('#workspace-tools summary').click()
            page.locator('.utility-panel a[href^="/updates"]').click()
            page.wait_for_load_state('networkidle')
            click('Back to settings')
            click('Back to dashboard')
            click("Course Load")
            plan_url = page.url
            page.locator('.planned-list a').first.click()
            page.wait_for_load_state("networkidle")
            click("Back to four-year plan")
            assert page.url == plan_url
            click("Explore Courses")
            page.locator('[name="subject"]').select_option("Science")
            page.get_by_role("button", name="Apply filters", exact=True).click()
            page.wait_for_load_state("networkidle")
            search_url = page.url
            assert "view=" in search_url
            boxes = page.locator('[form="compare-form"][name="id"]')
            boxes.nth(0).check()
            boxes.nth(1).check()
            page.get_by_role("button", name="Compare selected courses").click()
            page.wait_for_load_state("networkidle")
            compare_url = page.url
            click("Full course details ↗")
            click("Back to comparison")
            assert urlsplit(page.url).path == urlsplit(compare_url).path
            assert parse_qs(urlsplit(page.url).query) == parse_qs(urlsplit(compare_url).query)
            click("Change selection")
            assert page.locator('[name="subject"]').input_value() == "Science"
            assert page.locator('[form="compare-form"][name="id"]:checked').count() == 2
            page.get_by_role("button", name="Compare selected courses").click()
            page.wait_for_load_state("networkidle")
            add = page.get_by_role("button", name="Add to my plan", exact=True)
            if add.count():
                before = page.url
                add.first.click()
                page.wait_for_load_state("networkidle")
                assert canonical(page.url) == canonical(before)
                assert page.locator('.flash').is_visible()
            page.goto(plan_url)
            click("Open task planner")
            task_url = page.url.split('#')[0]
            click("Edit")
            click("Cancel")
            assert page.url.startswith(task_url + '#task-')
            click("Back to four-year plan")
            assert page.url == plan_url
            page.goto(origin + "/dashboard")
            click("Student profile")
            profile_url = page.url
            click("Accessibility and settings")
            settings_url = page.url
            page.get_by_role("button", name="Save all settings").click()
            page.wait_for_load_state("networkidle")
            assert page.url == settings_url
            click("Back to profile")
            assert page.url == profile_url
            # Browser Back and a second tab do not overwrite the explicit trail.
            click("Accessibility and settings")
            other = context.new_page()
            other.goto(origin + "/courses")
            click("Back to profile")
            assert page.url == profile_url
            page.go_back()
            page.wait_for_load_state("networkidle")
            assert page.get_by_role("link", name="Back to profile").count() == 1
            # All rendered internal links resolve to GET pages or downloadable files.
            audited = set()
            for path in ["/dashboard", "/tasks", "/profile", "/onboarding", "/settings", "/courses", "/courses/plan", "/courses/compare?id=SCI_AP_CHEMISTRY&id=SCI_AP_BIOLOGY", "/courses/SCI_AP_CHEMISTRY", "/updates"]:
                page.goto(origin + path)
                for href in page.locator('a[href]').evaluate_all('(links) => links.map(link => link.href)'):
                    if not href.startswith(origin) or urlsplit(href).fragment or href in audited:
                        continue
                    # Many course cards share a route; test one per path family/catalog.
                    key = urlsplit(href).path
                    if key.startswith('/courses/') and key not in ['/courses/plan', '/courses/compare']:
                        if '/courses/detail-audited' in audited:
                            continue
                        audited.add('/courses/detail-audited')
                    response = context.request.get(href)
                    assert response.status == 200, (href, response.status)
                    audited.add(href)
            assert not errors, errors
            for width in (320, 390, 1440):
                page.set_viewport_size({"width": width, "height": 900})
                for theme in ('light', 'dark', 'high-contrast'):
                    for scale in ('100', '200'):
                        page.evaluate('([theme, scale]) => {document.documentElement.dataset.theme=theme; document.documentElement.dataset.textScale=scale}', [theme, scale])
                        page.locator('#workspace-tools').evaluate('(element) => element.open = true')
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (width, theme, scale)
                        panel = page.locator('.utility-panel').bounding_box()
                        assert panel['x'] >= 0 and panel['x'] + panel['width'] <= width + 1
            page.set_viewport_size({"width": 1440, "height": 1000})
            page.goto(origin + '/dashboard')
            page.locator('#workspace-tools summary').click()
            Path('output').mkdir(exist_ok=True)
            page.screenshot(path='output/navigation-menu-desktop.png')
            page.set_viewport_size({"width": 390, "height": 844})
            page.screenshot(path='output/navigation-menu-mobile.png')
            browser.close()
            print(f"PASS: multistep course/task/profile flows, filters, comparisons, saves, cancel, tabs, browser Back; {len(audited)-1} internal links checked.")
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
