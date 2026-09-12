"""
scripts/migrate_existing_data.py
---------------------------------
One-shot migration script for the student-login-task-organizer feature.

What it does
~~~~~~~~~~~~
1. Calls ``db.create_all()`` to materialise the new ``users`` table and the
   ``user_id`` column on ``student_profiles`` without touching existing data.
2. Detects any ``StudentProfile`` rows where ``user_id IS NULL`` (orphaned
   records that predate the multi-user feature).
3. If orphaned profiles are found, creates exactly one default User
   (username ``"default_student"``, a securely-generated random password
   hash, ``created_at`` = now UTC) and links every orphaned profile to it.
4. Prints a summary of every action taken and exits cleanly when there is
   nothing to migrate.

Safety guarantees
~~~~~~~~~~~~~~~~~
- No existing row is deleted or overwritten.
- The script is idempotent: running it a second time when all profiles
  already have a ``user_id`` is a no-op.
- The random password for the default user cannot be guessed; the hash is
  generated via ``werkzeug.security.generate_password_hash``.

Usage
~~~~~
    cd <project-root>
    python scripts/migrate_existing_data.py
"""

import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Make sure the project root is on sys.path so that ``from extensions import
# db`` (and the rest of the app imports) resolve correctly regardless of
# the directory from which this script is invoked.
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from werkzeug.security import generate_password_hash  # bundled with Flask

from sqlalchemy import text as sa_text

from app import create_app
from extensions import db
from models import StudentProfile, User


def _ensure_user_id_column_exists(engine) -> bool:
    """
    Add the ``user_id`` column to ``student_profiles`` if it is missing.

    ``db.create_all()`` only creates absent *tables*; it does not ALTER
    existing tables to add new columns.  We therefore inspect the live
    schema and emit an ``ALTER TABLE`` statement when needed.

    Returns ``True`` if the column was added, ``False`` if it already existed.
    """
    with engine.connect() as conn:
        # PRAGMA table_info returns one row per column: (cid, name, type, …)
        result = conn.execute(sa_text("PRAGMA table_info(student_profiles)"))
        columns = {row[1] for row in result}  # row[1] is the column name

    if "user_id" not in columns:
        with engine.begin() as conn:
            conn.execute(
                sa_text(
                    "ALTER TABLE student_profiles "
                    "ADD COLUMN user_id INTEGER REFERENCES users(id)"
                )
            )
        print(
            "[migrate] Added missing column 'user_id' to table "
            "'student_profiles' via ALTER TABLE."
        )
        return True

    print("[migrate] Column 'user_id' already exists on 'student_profiles'.")
    return False


def run_migration() -> None:
    """Run the migration inside an application context."""
    app = create_app()

    with app.app_context():
        # ------------------------------------------------------------------
        # Step 1: Materialise any new tables (creates `users` if absent)
        # ------------------------------------------------------------------
        db.create_all()
        print("[migrate] db.create_all() completed — new tables materialised.")

        # ------------------------------------------------------------------
        # Step 1b: Ensure user_id column exists on student_profiles
        #          (db.create_all does NOT alter existing tables)
        # ------------------------------------------------------------------
        _ensure_user_id_column_exists(db.engine)

        # ------------------------------------------------------------------
        # Step 2: Detect orphaned StudentProfile records
        # ------------------------------------------------------------------
        orphaned_profiles = StudentProfile.query.filter(
            StudentProfile.user_id.is_(None)
        ).all()

        if not orphaned_profiles:
            print("[migrate] No orphaned StudentProfile records found. Nothing to do.")
            return

        print(
            f"[migrate] Found {len(orphaned_profiles)} orphaned StudentProfile "
            f"record(s) with user_id = NULL."
        )

        # ------------------------------------------------------------------
        # Step 3: Create the default user (only if it doesn't already exist)
        # ------------------------------------------------------------------
        default_username = "default_student"
        existing_default = User.query.filter_by(username=default_username).first()

        if existing_default:
            default_user = existing_default
            print(
                f"[migrate] Default user '{default_username}' already exists "
                f"(id={default_user.id}). Re-using it."
            )
        else:
            # Generate a cryptographically random 32-byte token as the
            # "password" so this account cannot be brute-forced via the login
            # form.  The plaintext is never persisted; only the hash is stored.
            random_password = secrets.token_urlsafe(32)
            password_hash = generate_password_hash(random_password)

            default_user = User(
                username=default_username,
                password_hash=password_hash,
                created_at=datetime.now(timezone.utc),
            )
            db.session.add(default_user)
            # Flush to obtain the auto-generated primary key before we
            # reference it on the profile rows.
            db.session.flush()
            print(
                f"[migrate] Created default user '{default_username}' "
                f"(id={default_user.id}) with a randomly-generated password hash."
            )

        # ------------------------------------------------------------------
        # Step 4: Link every orphaned profile to the default user
        # ------------------------------------------------------------------
        for profile in orphaned_profiles:
            profile.user_id = default_user.id
            print(
                f"[migrate]   → Linked StudentProfile id={profile.id} "
                f"('{profile.first_name}') to user id={default_user.id}."
            )

        # ------------------------------------------------------------------
        # Step 5: Commit all changes atomically
        # ------------------------------------------------------------------
        db.session.commit()
        print(
            f"[migrate] Migration complete. "
            f"{len(orphaned_profiles)} profile(s) linked to '{default_username}'."
        )


if __name__ == "__main__":
    run_migration()
