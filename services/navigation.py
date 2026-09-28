"""Explicit, tab-independent return trails. Never redirect to an arbitrary referrer."""
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit, unquote

from flask import current_app, g, request, url_for
from itsdangerous import BadData, URLSafeSerializer
from werkzeug.exceptions import HTTPException

PAGES = {
    "colleges.browse": "college directory", "terms.edit": "college course editor",
    "tasks.import_calendar": "calendar import",
    "terms.plan": "term plan",
    "main.home": "home", "main.dashboard": "dashboard",
    "main.local_planner": "browser planner", "main.updates": "updates",
    "courses.course_explorer": "course explorer", "courses.course_plan": "four-year plan",
    "courses.course_compare": "comparison", "courses.course_detail": "course details",
    "tasks.task_detail": "task details", "tasks.tasks": "tasks", "tasks.edit_task": "task editor",
    "profile.profile_view": "profile", "profile.onboarding": "planning preferences",
    "settings.settings": "settings", "auth.login": "sign in", "auth.register": "planner creation",
}


def safe_page(value):
    if not isinstance(value, str) or len(value) > 12000:
        return None
    decoded = unquote(value)
    if not value.startswith("/") or decoded.startswith("//") or "\\" in decoded or any(ord(c) < 32 for c in decoded):
        return None
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc:
        return None
    try:
        endpoint, _ = current_app.url_map.bind_to_environ(request.environ).match(parsed.path, method="GET")
    except HTTPException:
        return None
    return value if endpoint in PAGES else None


def _serializer():
    return URLSafeSerializer(current_app.secret_key, salt="navigation-v1")


def _without_trail(value):
    parsed = urlsplit(value)
    pairs = [(key, val) for key, val in parse_qsl(parsed.query, keep_blank_values=True) if key != "nav"]
    return urlunsplit(("", "", parsed.path, urlencode(pairs), parsed.fragment))


def trail():
    token = request.form.get("_nav") or request.args.get("nav", "")
    if not token or len(token) > 10000:
        return []
    try:
        items = _serializer().loads(token)
        if not isinstance(items, list) or len(items) > 8:
            return []
        return [item for item in items if safe_page(item) and item == _without_trail(item)]
    except (BadData, ValueError, TypeError):
        return []


def with_trail(url, items):
    parsed = urlsplit(_without_trail(url))
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    if items:
        pairs.append(("nav", _serializer().dumps(items[-8:])))
    return urlunsplit(("", "", parsed.path, urlencode(pairs), parsed.fragment))


def current_url():
    return with_trail(getattr(g, "navigation_url", request.full_path.rstrip("?")), trail())


def nav_url(endpoint, **values):
    if endpoint in {"courses.course_plan", "courses.course_explorer"} and getattr(g, "current_user", None) and g.current_user.settings and g.current_user.settings.academic_context == "college":
        endpoint = "terms.plan"
        values = {}
    destination = url_for(endpoint, **values)
    if endpoint not in PAGES or endpoint in {"main.dashboard", "main.home"}:
        return destination
    items = trail()
    # Explicit links to an earlier page unwind the trail instead of creating loops.
    for index, item in enumerate(items):
        if urlsplit(item).path == urlsplit(destination).path:
            return with_trail(destination, items[:index])
    source = _without_trail(current_url())
    if endpoint == "tasks.edit_task" and request.endpoint == "tasks.tasks":
        source += "#task-" + str(values["task_id"])
    if safe_page(source) and urlsplit(source).path != urlsplit(destination).path:
        items.append(source)
    return with_trail(destination, items)


def same_page(endpoint, **values):
    return with_trail(url_for(endpoint, **values), trail())


def back_url(endpoint="main.dashboard", **values):
    items = trail()
    return with_trail(items[-1], items[:-1]) if items else url_for(endpoint, **values)


def back_label(endpoint="main.dashboard"):
    items = trail()
    if items:
        endpoint, _ = current_app.url_map.bind_to_environ(request.environ).match(urlsplit(items[-1]).path, method="GET")
    return "Back to " + PAGES.get(endpoint, "dashboard")


def ancestor_url(endpoint, **values):
    for index, item in reversed(list(enumerate(trail()))):
        matched, _ = current_app.url_map.bind_to_environ(request.environ).match(urlsplit(item).path, method="GET")
        if matched == endpoint:
            parsed = urlsplit(item)
            pairs = [(k, v) for k, v in parse_qsl(parsed.query) if k not in values]
            pairs.extend((k, v) for k, value in values.items() for v in (value if isinstance(value, list) else [value]))
            return with_trail(urlunsplit(("", "", parsed.path, urlencode(pairs), "")), trail()[:index])
    return nav_url(endpoint, **values)


def return_url(endpoint, **values):
    return safe_page(request.form.get("_return_to")) or same_page(endpoint, **values)


def template_context():
    return dict(nav_url=nav_url, nav_back_url=back_url, nav_back_label=back_label,
                nav_ancestor=ancestor_url, nav_same=same_page,
                navigation_current=current_url(),
                navigation_resume=safe_page(request.values.get("next")) or "",
                navigation_token=_serializer().dumps(trail()) if trail() else "",
                navigation_child_token=_serializer().dumps((trail() + [_without_trail(current_url())])[-8:]))
