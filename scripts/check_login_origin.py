"""Exercise native browser form submission: HTTP clients miss Origin:null regressions."""
import logging
import sys
import threading
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from extensions import db
from models import User
from services.auth_service import hash_password
from playwright.sync_api import sync_playwright, expect
from werkzeug.serving import make_server


def main():
    app = create_app({'TESTING': True, 'SECRET_KEY': 'isolated-login-check',
                      'SQLALCHEMY_DATABASE_URI': 'sqlite://', 'SESSION_COOKIE_SECURE': False})
    with app.app_context():
        db.session.add(User(username='login-check', password_hash=hash_password('sample-login-password'),
                            onboarding_completed=True))
        db.session.commit()
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    server = make_server('127.0.0.1', 0, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    posts = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel='chrome')
            page = browser.new_page()
            page.on('request', lambda r: posts.append(r.headers.get('origin'))
                    if r.method == 'POST' and r.url.endswith('/login') else None)
            response = page.goto(origin + '/login')
            assert response.headers['referrer-policy'] == 'same-origin'
            page.locator('[name=username]').fill('login-check')
            page.locator('[name=password]').fill('wrong-password')
            page.locator('button[type=submit]').click()
            expect(page.get_by_text('Username or password was not recognized.')).to_be_visible()
            page.locator('[name=password]').fill('sample-login-password')
            page.locator('button[type=submit]').click()
            page.wait_for_url('**/dashboard')
            assert posts == [origin, origin], posts
            browser.close()
        print('Native browser login passed: invalid credentials stay on form; valid credentials open dashboard; Origin preserved.')
    finally:
        server.shutdown()


if __name__ == '__main__':
    main()
