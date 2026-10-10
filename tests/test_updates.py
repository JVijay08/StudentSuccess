import re
import json
import subprocess

from services import update_history


def test_updates_from_signed_in_workspace(authed_client):
    dashboard = authed_client.get('/dashboard')
    link = re.search(rb'href="(/updates[^\"]*)"', dashboard.data)
    assert link
    from html import unescape
    response = authed_client.get(unescape(link.group(1).decode()))
    assert response.status_code == 200
    assert b'Workspace navigation' in response.data
    assert b'Back to dashboard' in response.data


def test_history_preserves_snapshot_with_shallow_checkout(tmp_path, monkeypatch):
    snapshot = tmp_path / "updates.json"
    old = {"hash": "a" * 40, "timestamp": 1, "date": "2026-09-18", "title": "Older update"}
    snapshot.write_text(json.dumps([old]), encoding="utf-8")
    result = subprocess.CompletedProcess([], 0, f"{'b' * 40}\x1f2\x1f2026-09-19\x1fNew update\n")
    monkeypatch.setattr(update_history.subprocess, "run", lambda *a, **k: result)
    entries = update_history.collect_updates(tmp_path, snapshot)
    assert [entry["title"] for entry in entries] == ["New update", "Older update"]


def test_history_works_without_git(tmp_path, monkeypatch):
    snapshot = tmp_path / "updates.json"
    entries = [{"hash": "a" * 40, "timestamp": 1, "date": "2026-09-18", "title": "Saved update"}]
    snapshot.write_text(json.dumps(entries), encoding="utf-8")
    def missing_git(*args, **kwargs):
        raise FileNotFoundError("git")
    monkeypatch.setattr(update_history.subprocess, "run", missing_git)
    assert update_history.collect_updates(tmp_path, snapshot) == entries


def test_updates_public_and_titles_escaped(app, monkeypatch):
    from routes import main_routes
    monkeypatch.setattr(main_routes, "get_updates", lambda: [
        {"hash": "a" * 40, "date": "2026-09-19", "title": "<script>alert(1)</script>"}
    ])
    client = app.test_client()
    response = client.get("/updates")
    assert response.status_code == 200
    assert b"&lt;script&gt;alert(1)&lt;/script&gt;" in response.data
    assert b"Revision aaaaaaa" in response.data
    assert re.search(rb'href="/updates(?:\?[^"]*)?"', client.get('/').data)


def test_updates_feature_latest_and_collapse_older_months(app, monkeypatch):
    from routes import main_routes
    monkeypatch.setattr(main_routes, "get_updates", lambda: [
        {"hash": "a" * 40, "date": "2026-10-10", "title": "Latest planner improvement"},
        {"hash": "b" * 40, "date": "2026-10-05", "title": "Another October improvement"},
        {"hash": "d" * 40, "date": "2026-10-03", "title": "October task improvements"},
        {"hash": "e" * 40, "date": "2026-10-01", "title": "October course improvements"},
        {"hash": "c" * 40, "date": "2026-09-30", "title": "September improvement"},
    ])

    response = app.test_client().get("/updates")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Latest update" in body
    assert "Latest planner improvement" in body
    assert "Another October improvement" in body
    assert "October task improvements" in body
    assert "October course improvements" in body
    assert "More from October 2026" in body
    assert "September 2026" in body
    assert 'data-update-archive' in body
    assert '<details class="update-archive update-month" data-update-archive>' in body


def test_updates_spotlight_uses_student_facing_release_copy(app, monkeypatch):
    from routes import main_routes
    monkeypatch.setattr(main_routes, "get_updates", lambda: [
        {"hash": "a" * 40, "date": "2026-10-10", "title": "Refine catalog and update history"},
        {"hash": "b" * 40, "date": "2026-10-05", "title": "Restore complete update history and expand shallow deployment clones"},
        {"hash": "c" * 40, "date": "2026-10-01", "title": "Redesign landing page with notebook previews and developer section"},
    ])

    response = app.test_client().get("/updates")
    body = response.get_data(as_text=True)

    assert "Find courses and updates faster" in body
    assert "Course filters stay in the page flow" in body
    assert "Catch up on recent improvements" in body
    assert "A clearer introduction to StudentSuccess" in body
    assert "shallow deployment clones" not in body


def test_current_layout_release_has_feature_summary(app, monkeypatch):
    from routes import main_routes
    monkeypatch.setattr(main_routes, "get_updates", lambda: [
        {"hash": "a" * 40, "date": "2026-10-10", "title": "Align planner pages with layout references"},
    ])

    response = app.test_client().get("/updates")
    body = response.get_data(as_text=True)

    assert "A clearer layout across your planner" in body
    assert "The next task is easier to spot" in body
    assert "Scan compact task rows" in body


def test_build_expands_shallow_history(monkeypatch, tmp_path):
    from scripts.build_updates import complete_checkout_history
    calls = []
    def run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "true\n")
    monkeypatch.setattr(subprocess, "run", run)
    complete_checkout_history(tmp_path)
    assert calls[-1] == ["git", "fetch", "--unshallow", "--no-tags", "origin"]


def test_build_full_checkout_needs_no_network(monkeypatch, tmp_path):
    from scripts.build_updates import complete_checkout_history
    calls = []
    def run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "false\n")
    monkeypatch.setattr(subprocess, "run", run)
    complete_checkout_history(tmp_path)
    assert len(calls) == 1


def test_build_keeps_snapshot_when_fetch_fails(monkeypatch, tmp_path, capsys):
    from scripts.build_updates import complete_checkout_history
    def run(command, **kwargs):
        if command[1] == "fetch":
            raise subprocess.CalledProcessError(1, command, stderr="private remote details")
        return subprocess.CompletedProcess(command, 0, "true\n")
    monkeypatch.setattr(subprocess, "run", run)
    complete_checkout_history(tmp_path)
    output = capsys.readouterr().out
    assert "keeping the bundled update history" in output
    assert "private remote details" not in output
