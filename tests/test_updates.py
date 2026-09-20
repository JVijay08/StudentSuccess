import re
import json
import subprocess

from services import update_history


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
