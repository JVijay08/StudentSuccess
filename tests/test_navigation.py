from html import unescape
import re
from urllib.parse import parse_qs, urlsplit

import pytest

from services.navigation import nav_url, safe_page, trail, with_trail
from tests.test_course_routes import complete_profile
from tests.test_nonpersonal_confirmation import task_data


def link(response, label):
    for href, text in re.findall(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', response.get_data(as_text=True), re.S):
        if label in re.sub(r"<[^>]+>", "", unescape(text)):
            return unescape(href)
    raise AssertionError(f"Missing link: {label}")


def fields(response):
    return {name: unescape(value) for name, value in re.findall(
        r'<input type="hidden" name="([^"]+)" value="([^"]*)"', response.get_data(as_text=True)
    )}


@pytest.mark.parametrize("target", ["https://evil.test", "//evil.test", "/%2fevil.test", "/\\evil.test", "/logout", "/settings/export", "/static/js/updates.js", "/missing", "/\n/evil.test"])
def test_returns_reject_external_or_non_page_destinations(app, target):
    with app.test_request_context("/"):
        assert safe_page(target) is None


def test_plan_detail_returns_to_plan_with_no_referrer(authed_client):
    complete_profile(authed_client)
    authed_client.post("/courses/plan/add/MATH_AP_STATISTICS", data={"school_year": "11"})
    plan_url = link(authed_client.get("/dashboard"), "Course load")
    detail_url = link(authed_client.get(plan_url), "AP Statistics")
    detail = authed_client.get(detail_url)
    assert link(detail, "Back to four-year plan") == plan_url
    assert link(authed_client.get(plan_url), "Back to dashboard") == "/dashboard"


def test_search_comparison_detail_and_add_preserve_context(authed_client):
    complete_profile(authed_client)
    response = authed_client.post("/courses", data={"q": "AP", "subject": "Science", "nonpersonal_confirmed": "yes"})
    assert response.status_code == 302
    explorer_url = response.location
    assert "q=" not in explorer_url
    explorer = authed_client.get(explorer_url)
    comparison_url = link(explorer, "vs.")
    comparison = authed_client.get(comparison_url)
    detail_url = link(comparison, "Full course details")
    detail = authed_client.get(detail_url)
    assert link(detail, "Back to comparison") == comparison_url
    assert parse_qs(urlsplit(link(comparison, "Back to course explorer")).query)["view"] == parse_qs(urlsplit(explorer_url).query)["view"]
    form = fields(detail)
    form["school_year"] = "11"
    course_id = urlsplit(detail_url).path.split("/")[-1]
    response = authed_client.post(f"/courses/plan/add/{course_id}", data=form)
    assert response.location == detail_url
    assert b"added to your plan" in authed_client.get(response.location).data
    restored = authed_client.get(link(comparison, "Change selection"))
    assert b'value="AP"' in restored.data
    assert b'value="Science" selected' in restored.data
    assert restored.data.count(b'checked data-course-name') >= 2


def test_settings_save_keeps_profile_parent(authed_client):
    complete_profile(authed_client)
    profile_url = link(authed_client.get("/dashboard"), "Profile")
    profile = authed_client.get(profile_url)
    settings_url = link(profile, "Accessibility and settings")
    settings = authed_client.get(settings_url)
    assert link(settings, "Back to profile") == profile_url
    response = authed_client.post(settings_url, data={**fields(settings), "theme": "dark"})
    assert response.location == settings_url
    assert link(authed_client.get(response.location), "Back to profile") == profile_url


def test_task_edit_validation_save_and_cancel_keep_task_parent(app, authed_client):
    from models import Task
    complete_profile(authed_client)
    authed_client.post("/tasks", data=task_data(nonpersonal_confirmed="yes"))
    with app.app_context():
        task_id = Task.query.one().id
    tasks_url = link(authed_client.get("/courses/plan"), "Open task planner")
    edit_url = link(authed_client.get(tasks_url), "Edit")
    edit = authed_client.get(edit_url)
    parent = tasks_url.split("#", 1)[0] + f"#task-{task_id}"
    assert link(edit, "Cancel") == parent
    invalid = authed_client.post(f"/tasks/{task_id}/edit", data=fields(edit))
    assert link(invalid, "Cancel") == parent
    response = authed_client.post(f"/tasks/{task_id}/edit", data={**fields(invalid), **task_data(nonpersonal_confirmed="yes")})
    assert response.location == parent
    assert link(authed_client.get(parent), "Back to four-year plan") == "/courses/plan"


def test_trails_are_bounded_tamper_resistant_and_unwind(app):
    with app.test_request_context("/courses/compare"):
        url = with_trail("/courses/compare", ["/dashboard", "/courses/plan", "/courses?subject=Math"])
    with app.test_request_context(url):
        result = nav_url("courses.course_plan")
    with app.test_request_context(result):
        assert trail() == ["/dashboard"]
    with app.test_request_context("/courses?nav=invalid"):
        assert trail() == []


def test_return_does_not_trust_external_referrer(authed_client):
    complete_profile(authed_client)
    response = authed_client.post("/courses/plan/add/MATH_AP_STATISTICS", data={"school_year": "11", "_return_to": "//evil.test"}, headers={"Referer": "https://evil.test"})
    assert response.location == "/courses/plan"


def test_sign_in_resumes_requested_page(app):
    from tests.test_access_codes import create, csrf
    client = app.test_client()
    code, _ = create(client)
    client.post("/logout")
    response = client.get("/courses/plan")
    assert parse_qs(urlsplit(response.location).query)["next"] == ["/courses/plan"]
    login = client.get(response.location)
    response = client.post("/access/open", data={**fields(login), "csrf_token": csrf(client), "access_code": code})
    assert response.location == "/courses/plan"


def test_settings_and_updates_are_secondary_workspace_controls(authed_client):
    complete_profile(authed_client)
    dashboard = authed_client.get("/dashboard").get_data(as_text=True)
    sidebar = dashboard.split('<nav aria-label="Workspace navigation">', 1)[1].split('</nav>', 1)[0]
    assert 'href="/settings' not in sidebar
    assert 'href="/updates' not in sidebar
    assert 'aria-label="Settings menu"' in dashboard
    assert 'class="utility-panel"' in dashboard
    assert 'href="/settings' in dashboard
    assert 'href="/updates' in dashboard


def test_direct_comparison_change_selection_retains_catalog(authed_client):
    complete_profile(authed_client)
    response = authed_client.get('/courses/compare?catalog=ap&id=AP_CALCULUS_AB&id=AP_STATISTICS')
    for label in ('Change selection', 'Back to course explorer'):
        target = link(response, label)
        assert parse_qs(urlsplit(target).query)['catalog'] == ['ap']


def test_profile_cancel_returns_to_profile(authed_client):
    complete_profile(authed_client)
    profile = authed_client.get('/profile')
    edit = authed_client.get(link(profile, 'Edit profile'))
    assert link(edit, 'Cancel') == '/profile'


def test_repeated_complete_and_stale_start_do_not_repeat_recurring_work(app, authed_client):
    from models import Task
    complete_profile(authed_client)
    authed_client.post('/tasks', data=task_data(nonpersonal_confirmed='yes', recurrence_rule='daily'))
    with app.app_context():
        task_id = Task.query.filter_by(prep_for_id=None).one().id
    assert authed_client.post(f'/tasks/{task_id}/complete', data={'actual_minutes': '35'}).status_code == 302
    with app.app_context():
        count = Task.query.count()
    authed_client.post(f'/tasks/{task_id}/complete', data={'actual_minutes': '35'})
    authed_client.post(f'/tasks/{task_id}/start')
    with app.app_context():
        assert Task.query.count() == count
        assert app.extensions['sqlalchemy'].session.get(Task, task_id).status == 'completed'
