from unittest.mock import patch

from extensions import db
from models import Task
from tests.test_access_codes import create


def task_data(**extra):
    return {"title":"Sample algebra", "subject":"Math", "task_type":"Practice",
        "due_at":"2027-06-15T15:00", "estimated_minutes":"30",
        "difficulty":"medium", "interest_level":"medium", **extra}


def test_task_create_and_edit_require_fresh_confirmation(app):
    client = app.test_client()
    create(client)
    response = client.post("/tasks", data=task_data())
    assert b"Confirm that these entries" in response.data
    with app.app_context():
        assert Task.query.count() == 0
    assert client.post("/tasks", data=task_data(nonpersonal_confirmed="yes")).status_code == 302
    with app.app_context():
        task_id = Task.query.one().id
    response = client.post(f"/tasks/{task_id}/edit", data=task_data(title="Edited sample"))
    assert b"Confirm that these entries" in response.data
    with app.app_context():
        assert db.session.get(Task, task_id).title == "Sample algebra"
    assert client.post(f"/tasks/{task_id}/edit", data=task_data(title="Edited sample", nonpersonal_confirmed="yes")).status_code == 302
    with app.app_context():
        assert db.session.get(Task, task_id).title == "Edited sample"
    # Starting/completing tasks does not add arbitrary text or need another acknowledgment.
    assert client.post(f"/tasks/{task_id}/start").status_code == 302


def test_catalog_keeps_filters_and_blocks_unconfirmed_free_text(app):
    client = app.test_client()
    create(client)
    assert client.post("/courses", data={"subject":"Math", "course_type":"AP"}).status_code == 200
    with patch("routes.course_routes.course_service.filter_courses", return_value=[]) as search:
        response = client.post("/courses", data={"q":"sample identifying text"})
        assert response.status_code == 400
        assert search.call_args.kwargs["query"] is None
        assert b"Confirm that these entries" in response.data
    response = client.post("/courses", data={"q":"Calculus", "nonpersonal_confirmed":"yes"})
    assert response.status_code == 200
    assert b"Calculus" in response.data
    assert b"Biology" not in response.data
    assert client.get("/courses?q=unconfirmed").status_code == 400


def test_legacy_profile_requires_nonpersonal_confirmation(authed_client):
    response = authed_client.post("/onboarding", data={"first_name":"Sample learner"})
    assert b"Confirm that these entries" in response.data


def test_full_workspace_retains_catalog_comparison_and_plan(app):
    client = app.test_client()
    create(client)
    dashboard = client.get("/dashboard", follow_redirects=True)
    assert b"WHAT TO WORK ON NOW" in dashboard.data
    assert b"Course catalog" in dashboard.data
    assert b"Browser-only planner" not in dashboard.data
    for path in ("/courses", "/courses/plan", "/courses/compare?id=SCI_AP_CHEMISTRY&id=SCI_AP_BIOLOGY", "/tasks", "/settings"):
        assert client.get(path).status_code == 200
