from extensions import db
from models import StudentProfile, Task, User
from services.auth_service import SESSION_TIMEOUT_MINUTES


def test_public_home_explains_prototype_and_offers_fictional_demo(app):
    response = app.test_client().get("/")

    assert response.status_code == 200
    assert b"Plan less." in response.data
    assert b"Try the fictional demo" in response.data
    assert b"Use fictional data only" in response.data
    assert b"high-school students" in response.data
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
    assert b"Fictional demo workspace" in response.data
    assert b"QUICK DEMO TOUR" in response.data
    assert b"Finish algebra problem set" in response.data
    assert b"Moderate estimate" in response.data
    with app.app_context():
        assert User.query.filter(User.username.startswith("demo-")).count() == 1
        assert Task.query.count() == 7


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
    assert response.headers["Location"].endswith("/login")


def test_onboarding_saves_and_updates_profile(app, authed_client):
    data = {
        "nonpersonal_confirmed": "yes",
        "first_name": "Jayesh",
        "grade_level": "11",
        "graduation_year": "2027",
        "current_gpa": "4.16",
        "target_gpa": "5.0",
        "study_hours_per_week": "42",
        "career_interest": "Engineering",
        "course_rigor_preference": "Challenging",
    }

    response = authed_client.post("/onboarding", data=data)
    assert response.status_code == 302

    data["first_name"] = "J"
    data["career_interest"] = "Computer Science"
    response = authed_client.post("/onboarding", data=data)
    assert response.status_code == 302

    with app.app_context():
        profiles = StudentProfile.query.all()

    assert len(profiles) == 1
    assert profiles[0].first_name == "J"
    assert profiles[0].grade == 11
    assert profiles[0].career_goals == "Computer Science"
    assert profiles[0].course_rigor == "Challenging"


def test_onboarding_backend_limits_match_form(authed_client):
    response = authed_client.post(
        "/onboarding",
        data={
            "nonpersonal_confirmed": "yes",
            "first_name": "Alex",
            "grade_level": "11",
            "graduation_year": "2036",
            "current_gpa": "3.5",
            "target_gpa": "4.0",
            "study_hours_per_week": "81",
            "career_interest": "",
            "course_rigor_preference": "Balanced",
        },
    )

    assert response.status_code == 200
    assert b"Graduation year must be between 2026 and 2035." in response.data
    assert b"Study hours must be between 0 and 80 per week." in response.data
