"""Refresh the public history during deployment, including this deployment's commit."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.update_history import SNAPSHOT, collect_updates

if __name__ == "__main__":
    entries = collect_updates()
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Published {len(entries)} update titles.")
