from urllib.parse import urlsplit
from extensions import db
from models import StudentProfile, Task, User
from services.auth_service import SESSION_TIMEOUT_MINUTES


def test_public_home_explains_real_use_and_offers_demo(app):
    response = app.test_client().get("/")

    assert response.status_code == 200
    assert b"Plan less." in response.data
    assert b"Start tutorial" in response.data
    assert b"No signup needed for the tutorial." in response.data
    assert b"Plan your actual courses and tasks" in response.data
    assert b"high-school and college students" in response.data
    assert b'property="og:image"' in response.data
    assert b'name="twitter:card" content="summary_large_image"' in response.data
    assert b"may take up to a minute to wake" in response.data


def test_login_page_can_return_to_public_home(app):
    response = app.test_client().get("/login")

    assert response.status_code == 200
    assert b'href="/"' in response.data
    assert b"Back to home" in response.data


def test_register_page_can_return_to_public_home(app):
    response = app.test_client().get("/register")

    assert response.status_code == 200
    assert b'href="/"' in response.data
    assert b"Back to home" in response.data


def test_one_click_demo_creates_isolated_populated_workspace(app):
    client = app.test_client()

    response = client.post("/demo", follow_redirects=True)

    assert response.status_code == 200
    assert b"Demo workspace" in response.data
    assert b"Start with one assignment" in response.data
    assert b"Finish algebra problem set" in response.data
    assert b"Moderate estimate" in response.data
    with app.app_context():
        assert User.query.filter(User.username.startswith("demo-")).count() == 1
        assert Task.query.count() == 7


def test_tutorial_start_rate_limit_preserves_current_practice_workspace(app):
    from tests.account_helpers import csrf

    app.config["PRACTICE_START_LIMIT"] = 1
    client = app.test_client()
    first = client.post("/tutorial/start", data={"csrf_token": csrf(client)})
    assert first.status_code == 302
    with client.session_transaction() as session:
        practice_user_id = session["user_id"]
        assert session.get("demo_mode") is True

    limited = client.post("/tutorial/start", data={"csrf_token": csrf(client)})
    assert limited.status_code == 429
    assert limited.headers["Retry-After"] == "900"
    with client.session_transaction() as session:
        assert session["user_id"] == practice_user_id
    with app.app_context():
        assert db.session.get(User, practice_user_id) is not None
        assert User.query.filter(User.username.startswith("demo-")).count() == 1


def test_cross_site_post_cannot_start_a_practice_workspace(app):
    response = app.test_client().post(
        "/demo",
        headers={
            "Origin": "https://attacker.example",
            "Sec-Fetch-Site": "cross-site",
        },
    )

    assert response.status_code == 400
    with app.app_context():
        assert User.query.filter(User.username.startswith("demo-")).count() == 0


def test_production_responses_advertise_transport_and_content_policies(app):
    app.config["SESSION_COOKIE_SECURE"] = True
    response = app.test_client().get("/")

    assert response.headers["Strict-Transport-Security"] == "max-age=31536000"
    policy = response.headers["Content-Security-Policy"]
    assert "default-src 'self'" in policy
    assert "frame-ancestors 'none'" in policy


def test_authenticated_home_redirects_to_dashboard(authed_client):
    response = authed_client.get("/")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")


def test_missing_page_has_friendly_recovery(app):
    response = app.test_client().get("/definitely-not-a-page")

    assert response.status_code == 404
    assert b"That page is not here" in response.data
    assert b"Return home" in response.data


def test_server_error_has_friendly_recovery(app):
    app.config["PROPAGATE_EXCEPTIONS"] = False

    @app.get("/_test/error")
    def forced_error():
        raise RuntimeError("forced test error")

    response = app.test_client().get("/_test/error")

    assert response.status_code == 500
    assert b"StudentSuccess hit a snag" in response.data
    assert b"Try again" in response.data


def test_dashboard_and_onboarding_get_work(authed_client):
    assert authed_client.get("/dashboard").status_code == 200
    assert authed_client.get("/onboarding").status_code == 200


def test_authenticated_session_is_permanent_and_refreshes_activity(app, authed_client):
    from datetime import datetime, timedelta, timezone

    with authed_client.session_transaction() as session:
        assert session.permanent is True
        session["_last_active"] = (
            datetime.now(timezone.utc)
            - timedelta(minutes=SESSION_TIMEOUT_MINUTES - 1)
        ).isoformat()

    response = authed_client.get("/dashboard")

    assert response.status_code == 200
    with authed_client.session_transaction() as session:
        refreshed = datetime.fromisoformat(session["_last_active"])
        assert refreshed > datetime.now(timezone.utc) - timedelta(seconds=10)


def test_authenticated_session_expires_after_inactivity(app, authed_client):
    from datetime import datetime, timedelta, timezone

    with authed_client.session_transaction() as session:
        session["_last_active"] = (
            datetime.now(timezone.utc)
            - timedelta(minutes=SESSION_TIMEOUT_MINUTES + 1)
        ).isoformat()

    response = authed_client.get("/dashboard")

    assert response.status_code == 302
    assert urlsplit(response.headers["Location"]).path == "/login"


def test_onboarding_saves_preferences_without_identity(app, authed_client):
    from tests.account_helpers import setup
    assert setup(authed_client, grade='11', study_hours='42').status_code == 302
    assert setup(authed_client, grade='12', study_hours='20').status_code == 302
    with app.app_context():
        profile = StudentProfile.query.one()
        assert profile.first_name == 'Planner'
        assert profile.grade == 12
        assert profile.study_hours_per_week == 20


def test_onboarding_backend_limits_match_form(authed_client):
    from tests.account_helpers import setup
    response = setup(authed_client, study_hours='81')
    assert response.status_code == 200
    assert b'Study hours must be between 0 and 80 per week.' in response.data
