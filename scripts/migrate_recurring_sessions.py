"""
scripts/migrate_recurring_sessions.py
--------------------------------------
One-shot, idempotent, additive migration for the recurring-sessions feature.

What it does
~~~~~~~~~~~~
1. Runs inside ``create_app().app_context()``.
2. Calls ``db.create_all()`` (a no-op for the existing ``tasks`` table;
   ``create_all`` only creates absent tables, it does not ALTER existing ones).
3. Detects each missing column on ``tasks`` via ``PRAGMA table_info(tasks)`` and
   issues an additive ``ALTER TABLE`` only when the column is absent:
     - ``recurrence_rule VARCHAR(20)``
     - ``prep_for_id INTEGER REFERENCES tasks(id)``

Safety guarantees
~~~~~~~~~~~~~~~~~
- No existing table or row is dropped, recreated, or deleted.
- ``instance/studentsuccess.db`` is never deleted.
- Idempotent: a second run detects both columns and is a no-op.
- Existing rows keep ``NULL`` for both new columns.

Usage
~~~~~
    cd <project-root>
    python scripts/migrate_recurring_sessions.py
"""

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Make sure the project root is on sys.path so that ``from extensions import
# db`` (and the rest of the app imports) resolve correctly regardless of the
# directory from which this script is invoked.
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import text as sa_text

from app import create_app
from extensions import db


def _ensure_task_column(engine, column_name, column_ddl) -> bool:
    """
    Add ``column_name`` to the ``tasks`` table via ``ALTER TABLE`` if missing.

    ``db.create_all()`` only creates absent *tables*; it does not ALTER existing
    tables to add new columns. We therefore inspect the live schema and emit an
    ``ALTER TABLE`` statement when needed.

    Returns ``True`` if the column was added, ``False`` if it already existed.
    """
    with engine.connect() as conn:
        # PRAGMA table_info returns one row per column: (cid, name, type, …)
        result = conn.execute(sa_text("PRAGMA table_info(tasks)"))
        columns = {row[1] for row in result}  # row[1] is the column name

    if column_name not in columns:
        with engine.begin() as conn:
            conn.execute(sa_text(f"ALTER TABLE tasks ADD COLUMN {column_ddl}"))
        print(f"[migrate] Added column '{column_name}' to 'tasks'.")
        return True

    print(f"[migrate] Column '{column_name}' already exists on 'tasks'.")
    return False


def run_migration() -> None:
    """Run the migration inside an application context."""
    app = create_app()

    with app.app_context():
        # Materialise any absent tables (no-op for the existing 'tasks' table).
        db.create_all()

        _ensure_task_column(db.engine, "recurrence_rule", "recurrence_rule VARCHAR(20)")
        _ensure_task_column(
            db.engine, "prep_for_id", "prep_for_id INTEGER REFERENCES tasks(id)"
        )

        print("[migrate] recurring-sessions migration complete.")


if __name__ == "__main__":
    run_migration()
