import re
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
    assert b'Create an account' in response.data
    assert re.search(rb'href="/register(?:\?[^"]*)?"', response.data)
    assert b'href="/planner"' not in response.data
    assert b'course plans' in response.data
    assert b'View source on GitHub' not in response.data


def test_registration_has_one_account_method(app, authed_client):
    response = app.test_client().get('/register')
    assert b'name="username"' in response.data
    assert b'name="email"' not in response.data
    assert b'name="access_code"' not in response.data
    assert b'href="/planner"' not in response.data
    assert b'href="/planner"' not in authed_client.get('/dashboard').data


def test_browser_catalog_bundle_is_public_and_contains_full_catalogs(app):
    response = app.test_client().get("/planner/catalogs.json")
    assert response.status_code == 200
    catalogs = response.json["catalogs"]
    assert {"national", "ap", "ib", "ga"} <= {c["id"] for c in catalogs}
    assert sum(len(c["courses"]) for c in catalogs) > 100
