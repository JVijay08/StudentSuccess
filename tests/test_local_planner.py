from models import StudentProfile, Task, User


def test_browser_planner_needs_no_account_and_creates_no_records(app):
    client = app.test_client()
    response = client.get("/planner")
    assert response.status_code == 200
    assert b"No name, email, or GPA required" in response.data
    assert b"local_planner.js" in response.data
    assert b"Restore backup" in response.data
    with client.session_transaction() as session:
        assert "user_id" not in session
    with app.app_context():
        assert User.query.count() == 0
        assert StudentProfile.query.count() == 0
        assert Task.query.count() == 0


def test_home_prioritizes_browser_planner_and_explains_server_demo(app):
    response = app.test_client().get("/")
    assert b'Start planning' in response.data
    assert b'href="/planner"' in response.data
    assert b'Task and course details are not uploaded' in response.data
    assert b'workspaces save information on the server' in response.data
    assert b'View source on GitHub' not in response.data
