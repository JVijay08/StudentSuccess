import re

from extensions import db
from models import AccessCredential, StudentProfile, Task, User
from services.access_service import code_digest


def csrf(client, path="/register"):
    client.get(path)
    with client.session_transaction() as session:
        return session["access_csrf"]


def create(client):
    response = client.post("/access/create", data={"csrf_token": csrf(client), "understood": "yes"})
    assert response.status_code == 200
    code = re.search(rb'value="(SS-[A-Za-z0-9_-]{43})"', response.data).group(1).decode()
    return code, response


def login(client, code):
    return client.post("/access/open", data={"csrf_token": csrf(client, "/login"), "access_code": code})


def test_create_has_no_personal_fields_and_never_persists_plaintext_code(app):
    client = app.test_client()
    code, response = create(client)
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    with client.session_transaction() as session:
        assert code not in str(dict(session))
        assert session["access_version"] == 1
    with app.app_context():
        credential = AccessCredential.query.one()
        assert credential.digest == code_digest(code)
        assert credential.user.username.startswith("private-")
        assert code not in credential.user.password_hash
        assert StudentProfile.query.one().first_name == "Planner"
    assert client.get("/dashboard").status_code == 200
    assert b'Current GPA' not in client.get("/onboarding").data
    assert b'First Name' not in client.get("/onboarding").data


def test_codes_are_distinct_and_reopen_same_plan_on_another_device(app):
    first, second = app.test_client(), app.test_client()
    code, _ = create(first)
    other_code, _ = create(second)
    assert code != other_code
    with first.session_transaction() as session:
        user_id = session["user_id"]
    response = first.post("/tasks", data={"nonpersonal_confirmed":"yes", "title":"Fictional algebra", "due_at":"2027-01-15T18:00",
        "estimated_minutes":"30", "difficulty":"medium", "interest_level":"medium"})
    assert response.status_code == 302
    returning = app.test_client()
    assert login(returning, "  " + code + "  ").status_code == 302
    with returning.session_transaction() as session:
        assert session["user_id"] == user_id
    assert b"Fictional algebra" in returning.get("/tasks").data
    assert b"Fictional algebra" not in second.get("/tasks").data
    with app.app_context():
        task_id = Task.query.one().id
    assert second.post(f"/tasks/{task_id}/start").status_code == 404


def test_auth_requires_csrf_and_create_requires_acknowledgment(app):
    client = app.test_client()
    assert client.post("/register", data={"username":"new", "password":"password123"}).status_code == 405
    assert client.post("/access/create", data={"understood":"yes"}).status_code == 400
    assert client.post("/access/open", data={"access_code":"anything"}).status_code == 400
    token = csrf(client)
    assert client.post("/access/create", data={"csrf_token":token}).status_code == 400
    assert client.post("/access/create", data={"csrf_token":"\u2603"}).status_code == 400
    with app.app_context():
        assert User.query.count() == 0


def test_invalid_code_does_not_sign_in_or_echo_secret(app):
    client = app.test_client()
    invalid = "SS-" + "x" * 43
    response = login(client, invalid)
    assert response.status_code == 400
    assert invalid.encode() not in response.data
    with client.session_transaction() as session:
        assert "user_id" not in session
    assert login(client, "\u2603").status_code == 400


def test_replacing_code_revokes_old_code_and_other_sessions(app):
    first, second = app.test_client(), app.test_client()
    old_code, _ = create(first)
    login(second, old_code)
    token = csrf(first, "/settings")
    # Missing CSRF or wrong current code must not rotate the credential.
    assert first.post("/access/replace", data={"access_code":old_code}).status_code == 400
    first.post("/access/replace", data={"csrf_token":token, "access_code":"wrong"})
    assert second.get("/dashboard").status_code == 200
    response = first.post("/access/replace", data={"csrf_token":token, "access_code":old_code})
    new_code = re.search(rb'value="(SS-[A-Za-z0-9_-]{43})"', response.data).group(1).decode()
    assert new_code != old_code
    assert first.get("/dashboard").status_code == 200
    assert second.get("/dashboard").status_code == 302
    assert login(app.test_client(), old_code).status_code == 400
    assert login(app.test_client(), new_code).status_code == 302


def test_deleting_code_account_requires_code_and_cascades(app):
    client = app.test_client()
    code, _ = create(client)
    token = csrf(client, "/settings")
    client.post("/settings/delete-account", data={"csrf_token":token, "access_code":"wrong"})
    with app.app_context():
        assert User.query.count() == 1
    response = client.post("/settings/delete-account", data={"csrf_token":token, "access_code":code})
    assert response.status_code == 302
    with app.app_context():
        assert User.query.count() == 0
        assert AccessCredential.query.count() == 0
        assert StudentProfile.query.count() == 0
    assert login(app.test_client(), code).status_code == 400


def test_code_accounts_cannot_use_password_login(app):
    client = app.test_client()
    create(client)
    with app.app_context():
        from services.auth_service import hash_password
        user = User.query.one()
        username = user.username
        user.password_hash = hash_password("known-password")
        db.session.commit()
    fresh = app.test_client()
    response = fresh.post("/login", data={"username":username, "password":"known-password"})
    assert b"Invalid username or password" in response.data
    with fresh.session_transaction() as session:
        assert "user_id" not in session


def test_planning_preferences_do_not_request_or_save_identity(app):
    client = app.test_client()
    create(client)
    token = csrf(client, "/onboarding")
    response = client.post("/onboarding", data={"csrf_token":token, "grade":"11", "study_hours":"12", "first_name":"Real name"})
    assert response.status_code == 302
    with app.app_context():
        profile = StudentProfile.query.one()
        assert (profile.grade, profile.study_hours_per_week, profile.first_name) == (11, 12, "Planner")
    assert b"between 0 and 80" in client.post("/onboarding", data={"csrf_token":token, "grade":"11", "study_hours":"nan"}).data


def test_public_entry_points_offer_welcome_dialog(app):
    client = app.test_client()
    for path in ("/", "/register", "/login"):
        page = client.get(path)
        assert b'<dialog id="welcome-dialog"' in page.data
        assert b'Explore with fictional information' in page.data
        assert b'filename=' not in page.data
