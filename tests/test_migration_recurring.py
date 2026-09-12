"""Tests for the recurring-sessions migration helper.

These tests only ever touch an isolated temp SQLite DB (via the conftest ``app``
fixture, which binds to ``tmp_path``). They MUST NOT touch the real
``instance/studentsuccess.db``. We test ``_ensure_task_column`` directly against
the fixture's engine inside an app context, rather than calling the top-level
``run_migration`` (which would build the app on the REAL config/DB).
"""

from pathlib import Path

from sqlalchemy import text as sa_text

from extensions import db
from scripts.migrate_recurring_sessions import _ensure_task_column


def _task_columns():
    """Return the set of column names on the ``tasks`` table."""
    with db.engine.connect() as conn:
        result = conn.execute(sa_text("PRAGMA table_info(tasks)"))
        return {row[1] for row in result}


def test_new_columns_present_after_create_all(app):
    # The conftest fixture already ran db.create_all(), which materialises the
    # tasks table WITH the model's new columns.
    with app.app_context():
        columns = _task_columns()
        assert "recurrence_rule" in columns
        assert "prep_for_id" in columns


def test_ensure_task_column_is_idempotent_noop_when_present(app):
    with app.app_context():
        # Columns already exist (created by the model via db.create_all), so the
        # helper detects them and performs no ALTER — returning False both times.
        first = _ensure_task_column(
            db.engine, "recurrence_rule", "recurrence_rule VARCHAR(20)"
        )
        second = _ensure_task_column(
            db.engine, "recurrence_rule", "recurrence_rule VARCHAR(20)"
        )
        assert first is False
        assert second is False

        first_prep = _ensure_task_column(
            db.engine, "prep_for_id", "prep_for_id INTEGER REFERENCES tasks(id)"
        )
        assert first_prep is False

        # Columns still present after the (no-op) helper calls.
        columns = _task_columns()
        assert "recurrence_rule" in columns
        assert "prep_for_id" in columns


def test_ensure_task_column_adds_missing_column(app):
    # Prove the ALTER path: drop a probe column scenario by adding a genuinely
    # new column that the model does not define, then confirm the helper adds it
    # the first time and no-ops the second time.
    with app.app_context():
        assert "probe_marker" not in _task_columns()

        added = _ensure_task_column(
            db.engine, "probe_marker", "probe_marker VARCHAR(8)"
        )
        assert added is True
        assert "probe_marker" in _task_columns()

        # Second call is a no-op now that the column exists.
        again = _ensure_task_column(
            db.engine, "probe_marker", "probe_marker VARCHAR(8)"
        )
        assert again is False


def test_temp_db_file_still_exists_and_real_db_untouched(app):
    with app.app_context():
        db_uri = app.config["SQLALCHEMY_DATABASE_URI"]
        # Fixture always uses an isolated temp DB, never the real instance DB.
        assert "instance" not in db_uri
        db_path = Path(db_uri.replace("sqlite:///", ""))
        _ensure_task_column(db.engine, "recurrence_rule", "recurrence_rule VARCHAR(20)")
        assert db_path.exists()
