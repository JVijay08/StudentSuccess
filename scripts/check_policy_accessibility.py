"""Local, synthetic-data audit. Supply a local axe-core JS file; never shipped to visitors."""
from browser_test_support import start_demo
import json, logging, sys, threading
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright, expect
from audit_responsive import BOUNDS


def main():
    axe = Path(sys.argv[1] if len(sys.argv) > 1 else '.test-policy-audit/axe.min.js')
    if not axe.exists():
        raise SystemExit('Pass the path to a downloaded axe-core 4.10.3 axe.min.js file.')
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite://',
                      'SECRET_KEY': 'local-audit', 'GROQ_API_KEY': 'stub', 'AI_ENABLED': True})
    from extensions import db
    from models import User
    from services.auth_service import hash_password
    client = app.test_client()
    start_demo(client)
    with app.app_context():
        user = User.query.one()
        user.username = 'policy-preview'
        user.password_hash = hash_password('sample-policy-password')
        db.session.commit()
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    server = make_server('127.0.0.1', 0, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    out = Path('.test-policy-audit'); out.mkdir(exist_ok=True)
    issues, errors, external = [], [], set()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel='chrome')
            page = browser.new_page(viewport={'width': 1440, 'height': 960})
            page.emulate_media(reduced_motion='reduce')
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('request', lambda r: external.add(r.url) if not r.url.startswith(origin) else None)
            def audit(route):
                page.goto(origin + route)
                expect(page.locator('.legal-footer')).to_be_visible()
                for theme in ['light', 'dark', 'high-contrast']:
                    page.evaluate('(t)=>document.documentElement.dataset.theme=t', theme)
                    page.add_script_tag(path=str(axe))
                    violations = page.evaluate("""async()=> (await axe.run(document, {
                      runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}
                    })).violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}))""")
                    if violations: issues.append({'route': route, 'theme': theme, 'violations': violations})
                page.set_viewport_size({'width': 320, 'height': 960})
                bounds = page.evaluate(BOUNDS)
                if bounds: issues.append({'route': route, 'bounds': bounds})
                page.set_viewport_size({'width': 1440, 'height': 960})
            for route in ['/', '/login', '/register', '/privacy', '/terms-of-service', '/cookies', '/data-deletion', '/accessibility']:
                audit(route)
            page.goto(origin + '/login')
            page.locator('[name=username]').fill('policy-preview')
            page.locator('[name=password]').fill('sample-policy-password')
            page.locator('button[type=submit]').click()
            page.wait_for_url('**/dashboard')
            for route in ['/dashboard', '/tasks', '/courses', '/settings', '/tasks/ai/new', '/calendar', '/planner']:
                audit(route)
            (out / 'results.json').write_text(json.dumps({'issues': issues, 'errors': errors}, indent=2), encoding='utf-8')
            # A disclosure can be operated and dismissed without a pointer.
            page.goto(origin + '/tasks')
            menu = page.locator('.task-menu').first
            menu.locator(':scope > summary').focus(); page.keyboard.press('Enter')
            expect(menu).to_have_attribute('open', '')
            page.keyboard.press('Tab'); page.keyboard.press('Escape')
            expect(menu).not_to_have_attribute('open', '')
            expect(menu.locator(':scope > summary')).to_be_focused()
            # Selecting a sort does not cause an unexpected context change.
            select = page.locator('[name=sort]')
            select.select_option('due')
            assert 'sort=due' not in page.url
            page.get_by_role('button', name='Sort', exact=True).click()
            assert 'sort=due' in page.url
            page.goto(origin + '/settings')
            summary = page.locator('.settings-group').first.locator(':scope > summary')
            summary.focus(); page.keyboard.press('Enter')
            expect(summary.locator('..')).to_have_attribute('open', '')
            page.goto(origin + '/privacy')
            page.keyboard.press('Tab')
            expect(page.locator('.skip-link')).to_be_focused()
            page.keyboard.press('Enter')
            assert page.url.endswith('#main-content')
            page.screenshot(path=str(out / 'privacy.png'), animations='disabled')
            cookies = browser.contexts[0].cookies()
            assert {c['name'] for c in cookies} <= {'session'}, cookies
            assert not external, external
            browser.close()
        (out / 'results.json').write_text(json.dumps({'issues': issues, 'errors': errors, 'external': sorted(external)}, indent=2), encoding='utf-8')
        print(f'Audited 15 pages in 3 themes; {len(issues)} issue groups; {len(errors)} JS errors. Keyboard and cookie checks passed.')
        if issues or errors: raise SystemExit(1)
    finally:
        server.shutdown()


if __name__ == '__main__':
    main()
