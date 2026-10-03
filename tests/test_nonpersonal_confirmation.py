from tests.account_helpers import csrf
import re
from unittest.mock import patch

from extensions import db
from models import Task
from tests.account_helpers import create


def task_data(**extra):
    return {"title":"Sample algebra", "subject":"Math", "task_type":"Practice",
        "due_at":"2027-06-15T15:00", "estimated_minutes":"30",
        "difficulty":"medium", "interest_level":"medium", **extra}


def test_routine_tasks_and_search_do_not_require_confirmation(app):
    client = app.test_client()
    create(client)
    assert client.post("/tasks", data=task_data()).status_code == 302
    with app.app_context():
        task_id = Task.query.one().id
    assert client.post(f"/tasks/{task_id}/edit", data=task_data(title="Updated")).status_code == 302
    assert client.post("/courses", data={"q":"Calculus"}, follow_redirects=True).status_code == 200
    assert client.get("/courses?q=Calculus").status_code == 200
    for route in ["/tasks", "/courses", "/onboarding"]:
        assert b'name="nonpersonal_confirmed"' not in client.get(route).data


def test_calendar_import_keeps_explicit_confirmation(app):
    from services.privacy_service import confirmation_errors
    assert confirmation_errors({}, required=True)
    assert not confirmation_errors({})
    assert not confirmation_errors({"nonpersonal_confirmed":"yes"}, required=True)


def test_full_workspace_retains_catalog_comparison_and_plan(app):
    client = app.test_client()
    create(client)
    dashboard = client.get("/dashboard", follow_redirects=True)
    assert b'class="focus-card"' in dashboard.data
    assert re.search(rb'href="/courses/plan(?:\?[^"]*)?">Course load</a>', dashboard.data)
    assert b"Course catalog" not in dashboard.data
    plan = client.get("/courses/plan")
    assert re.search(rb'href="/courses(?:\?[^"]*)?">Choose courses</a>', plan.data)
    assert b"Browser-only planner" not in dashboard.data
    for path in ("/courses", "/courses/plan", "/courses/compare?id=SCI_AP_CHEMISTRY&id=SCI_AP_BIOLOGY", "/tasks", "/settings"):
        assert client.get(path).status_code == 200
