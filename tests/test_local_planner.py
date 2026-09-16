from models import StudentProfile, Task, User


def test_optional_browser_planner_works_without_creating_records(app):
    client = app.test_client()
    response = client.get("/planner")
    assert response.status_code == 200
    assert b'Your four-year plan' in response.data
    assert b'FULL COURSE CATALOG' in response.data
    with client.session_transaction() as session:
        assert "user_id" not in session
    with app.app_context():
        assert User.query.count() == 0
        assert StudentProfile.query.count() == 0
        assert Task.query.count() == 0


def test_home_offers_full_workspace_and_no_reduced_planner(app):
    response = app.test_client().get("/")
    assert b'Create a private planner' in response.data
    assert b'href="/register"' in response.data
    assert b'href="/planner"' not in response.data
    assert b'full course catalog' in response.data
    assert b'workspaces save information on the server' in response.data
    assert b'View source on GitHub' not in response.data


def test_browser_option_is_only_offered_beneath_code_creation(app, authed_client):
    response = app.test_client().get("/register")
    assert b'Use the browser-only planner' in response.data
    assert b'href="/planner"' in response.data
    assert b'href="/planner"' not in authed_client.get("/dashboard").data


def test_browser_catalog_bundle_is_public_and_contains_full_catalogs(app):
    response = app.test_client().get("/planner/catalogs.json")
    assert response.status_code == 200
    catalogs = response.json["catalogs"]
    assert {"national", "ap", "ib", "forsyth-ga"} <= {c["id"] for c in catalogs}
    assert sum(len(c["courses"]) for c in catalogs) > 100
