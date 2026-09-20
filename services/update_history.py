"""Public commit titles, with a snapshot for deployments without full Git history."""
import json
import subprocess
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "data" / "updates.json"


def collect_updates(root=ROOT, snapshot=SNAPSHOT):
    entries = {}
    if snapshot.exists():
        for entry in json.loads(snapshot.read_text(encoding="utf-8")):
            entries[entry["hash"]] = entry
    try:
        result = subprocess.run(
            ["git", "log", "HEAD", "--format=%H%x1f%ct%x1f%cs%x1f%s"],
            cwd=root, capture_output=True, text=True, encoding="utf-8",
            check=True, timeout=10,
        )
        for line in result.stdout.splitlines():
            commit, timestamp, date, title = line.split("\x1f", 3)
            entries[commit] = {"hash": commit, "timestamp": int(timestamp),
                               "date": date, "title": title}
    except (OSError, subprocess.SubprocessError):
        # Packaged builds can serve the snapshot without Git installed.
        pass
    return sorted(entries.values(), key=lambda entry: entry["timestamp"], reverse=True)


@lru_cache(maxsize=1)
def get_updates():
    return collect_updates()
