"""Refresh the public history during deployment, including this deployment's commit."""
import json
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.update_history import ROOT, SNAPSHOT, collect_updates

def complete_checkout_history(root=ROOT):
    """Deployment clones may contain only HEAD; expand them before publishing."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-shallow-repository"], cwd=root,
            capture_output=True, text=True, check=True, timeout=10,
        )
        if result.stdout.strip() == "true":
            subprocess.run(
                ["git", "fetch", "--unshallow", "--no-tags", "origin"],
                cwd=root, capture_output=True, check=True, timeout=120,
            )
    except (OSError, subprocess.SubprocessError):
        # Do not expose remote credentials from Git errors in build logs.
        print("Full Git history unavailable; keeping the bundled update history.")


if __name__ == "__main__":
    complete_checkout_history()
    entries = collect_updates()
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Published {len(entries)} update titles.")
