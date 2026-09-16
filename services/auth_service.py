from datetime import datetime, timezone, timedelta
from functools import wraps

from flask import session, g, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash as _check_hash

from extensions import db

SESSION_TIMEOUT_MINUTES = 30


def hash_password(plaintext: str) -> str:
    """Hash a plaintext password using werkzeug's secure hashing."""
    return generate_password_hash(plaintext)


def check_password(plaintext: str, stored_hash: str) -> bool:
    """Verify a plaintext password against a stored hash."""
    return _check_hash(stored_hash, plaintext)


def login_required(f):
    """
    Decorator that protects a route by requiring an authenticated session.

    Checks:
    1. session['user_id'] is present.
    2. The user_id corresponds to a real User record in the database.
    3. The session has not been inactive for more than SESSION_TIMEOUT_MINUTES.

    On success: sets flask.g.current_user and updates session['_last_active'].
    On failure: clears the session and redirects to auth.login.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Import here to avoid circular imports at module load time
        from models import User

        user_id = session.get("user_id")

        # No user_id in session — not logged in
        if user_id is None:
            session.clear()
            return redirect(url_for("auth.login"))

        # Validate the user_id corresponds to a real user before loading preferences.
        user = db.session.get(User, user_id)
        if user is None:
            session.clear()
            return redirect(url_for("auth.login"))

        if user.access_credential is not None and session.get("access_version") != user.access_credential.version:
            session.clear()
            return redirect(url_for("auth.login"))

        timeout_minutes = (
            user.settings.session_timeout_minutes
            if user.settings is not None
            else SESSION_TIMEOUT_MINUTES
        )

        # Check session inactivity timeout
        last_active_str = session.get("_last_active")
        if last_active_str is not None:
            try:
                last_active = datetime.fromisoformat(last_active_str)
                # Ensure it's timezone-aware (UTC)
                if last_active.tzinfo is None:
                    last_active = last_active.replace(tzinfo=timezone.utc)
                elapsed = datetime.now(timezone.utc) - last_active
                if elapsed > timedelta(minutes=timeout_minutes):
                    session.clear()
                    return redirect(url_for("auth.login"))
            except (ValueError, TypeError):
                # Malformed timestamp — treat as expired
                session.clear()
                return redirect(url_for("auth.login"))

        # All checks passed — attach user to request context and refresh timestamp
        g.current_user = user
        session["_last_active"] = datetime.now(timezone.utc).isoformat()

        return f(*args, **kwargs)

    return decorated_function
