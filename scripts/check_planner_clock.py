"""Browser regression checks for planner time and demo-tour dismissal."""
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite://"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server
from app import create_app
from extensions import db
from models import UserSettings


def main():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://"})
    server = make_server("127.0.0.1", 0, app)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f"http://127.0.0.1:{server.server_port}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True)
            for width in (390, 1440):
                context = browser.new_context(viewport={"width": width, "height": 900})
                response = context.request.get(origin + "/time")
                assert response.status == 200
                assert response.headers['cache-control'] == 'no-store'
                server_now = datetime.fromisoformat(response.json()['utc'])
                assert abs((datetime.now(timezone.utc) - server_now).total_seconds()) < 5
                context.request.post(origin + "/demo")
                page = context.new_page()
                page.add_init_script("Date.now = () => 0")
                stamp = {"utc": "2026-07-16T18:30:00+00:00"}
                page.route("**/time", lambda route: route.fulfill(json=stamp))
                page.goto(origin + "/dashboard")
                clock = page.locator("[data-planner-clock] time")
                page.wait_for_function("document.querySelector('[data-planner-clock] time').textContent.includes('02:30:')")
                assert "Jul 16, 2026" in clock.inner_text()
                assert "EDT" in clock.inner_text()
                assert page.locator('.task-deadline').count() > 0
                before = clock.get_attribute('datetime')
                page.wait_for_function("before => document.querySelector('[data-planner-clock] time').dateTime !== before", arg=before)
                tour = page.locator('#demo-checklist')
                if width == 390:
                    tour.locator('summary').click()
                page.locator('#dismiss-demo-checklist').click()
                assert not tour.is_visible()
                page.reload()
                assert not tour.is_visible()
                page.goto(origin + '/tasks')
                assert page.locator('[data-planner-clock]').is_visible()
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                with app.app_context():
                    UserSettings.query.update({"timezone_name": "America/Los_Angeles", "date_format": "year-first", "time_format": "24-hour"})
                    db.session.commit()
                stamp['utc'] = '2026-01-01T02:30:00+00:00'
                page.reload()
                page.wait_for_function("document.querySelector('[data-planner-clock] time').textContent.includes('2025-12-31')")
                assert '18:30:' in clock.inner_text()
                assert 'PST' in clock.inner_text()
                print(f'PASS: {width}px, live clock, server time, time-zone date rollover, formats, tour click and reload')
                context.close()
            browser.close()
    finally:
        server.shutdown()


if __name__ == '__main__':
    main()
