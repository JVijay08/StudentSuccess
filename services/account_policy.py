"""Username/password validation and database-backed request limits."""
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import re

from flask import current_app, request
from extensions import db
from models.account_request import AuthAttempt


def credential_errors(username, password, confirmation):
    errors = []
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{2,29}', username) or username.startswith(('demo-', 'private-', 'email-')):
        errors.append('Choose a username with 3–30 letters, numbers, underscores, or hyphens. Start with a letter or number.')
    if not 15 <= len(password) <= 128:
        errors.append('Use a password with 15–128 characters. A few unrelated words are easier to remember.')
    if password != confirmation:
        errors.append('The passwords do not match.')
    return errors


def allow_attempt(identifier, action, limit=10):
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=15)
    AuthAttempt.query.filter(AuthAttempt.created_at < cutoff).delete()
    secret = current_app.secret_key.encode()
    keys = [(f'{action}:username:{identifier}', limit), (f'{action}:ip:{request.remote_addr}', 100)]
    for raw, maximum in keys:
        key = hmac.new(secret, raw.encode(), hashlib.sha256).hexdigest()
        if AuthAttempt.query.filter(AuthAttempt.key == key, AuthAttempt.created_at >= cutoff).count() >= maximum:
            db.session.commit()
            from services.security_events import security_event
            security_event('account_rate_limit')
            return False
    for raw, _ in keys:
        key = hmac.new(secret, raw.encode(), hashlib.sha256).hexdigest()
        db.session.add(AuthAttempt(key=key, created_at=now))
    db.session.commit()
    return True
