"""Verified email delivery and bounded authentication requests."""
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import re
import secrets
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from flask import current_app, request

from extensions import db
from models.account_request import AccountRequest, AuthAttempt


def ready():
    config = current_app.config
    if config.get('TESTING') and config.get('EMAIL_TEST_DELIVERY'):
        return True
    origin = urlsplit(config.get('PUBLIC_BASE_URL', ''))
    return bool(config.get('RESEND_API_KEY') and config.get('EMAIL_FROM') and
                origin.scheme == 'https' and origin.netloc and not origin.username and
                origin.path in ('', '/') and not origin.query and not origin.fragment)


def normalize_email(value):
    value = value.strip().lower()
    if len(value) > 254 or not re.fullmatch(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,63}", value):
        raise ValueError('Enter a valid email address.')
    local, domain = value.rsplit('@', 1)
    if len(local) > 64 or '..' in value or local.startswith('.') or local.endswith('.') or any(part.startswith('-') or part.endswith('-') for part in domain.split('.')):
        raise ValueError('Enter a valid email address.')
    return value


def password_errors(password, confirmation):
    if not 12 <= len(password) <= 128:
        return ['Use a password between 12 and 128 characters. A few unrelated words work well.']
    if password != confirmation:
        return ['The passwords do not match.']
    return []


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def allow_attempt(identifier, action, limit=5):
    """Shared database limits; no raw email or IP address in the throttle table."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=1)
    AuthAttempt.query.filter(AuthAttempt.created_at < cutoff).delete()
    AccountRequest.query.filter(AccountRequest.expires_at < now).delete()
    secret = current_app.config['SECRET_KEY'].encode()
    keys = [(hmac.new(secret, f'{action}:email:{identifier}'.encode(), hashlib.sha256).hexdigest(), limit),
            (hmac.new(secret, f'{action}:ip:{request.remote_addr}'.encode(), hashlib.sha256).hexdigest(), 30)]
    for key, maximum in keys:
        if AuthAttempt.query.filter(AuthAttempt.key == key, AuthAttempt.created_at >= cutoff).count() >= maximum:
            db.session.commit()
            return False
    for key, _ in keys:
        db.session.add(AuthAttempt(key=key, created_at=now))
    db.session.commit()
    return True


def send_action(email, purpose, user=None, password_hash=None):
    token = secrets.token_urlsafe(32)
    record = AccountRequest(digest=digest(token), email=email, purpose=purpose,
        user_id=user.id if user else None, auth_version=user.auth_version if user else 0,
        password_hash=password_hash, expires_at=datetime.now(timezone.utc)+timedelta(minutes=30))
    db.session.add(record)
    db.session.commit()
    origin = current_app.config.get('PUBLIC_BASE_URL', '').rstrip('/')
    link = origin + '/account/confirm/' + token
    action = 'reset your password' if purpose == 'reset' else 'confirm your email and finish setting up email sign-in'
    message = dict(to=[email], subject='Your StudentSuccess account link',
        text=f'Use this link to {action}:\n\n{link}\n\nThis link expires in 30 minutes and works once. Only continue if you requested this. Otherwise ignore this email. Never share this link.\n\nStudentSuccess')
    try:
        if current_app.config.get('TESTING') and current_app.config.get('EMAIL_TEST_DELIVERY'):
            current_app.config['EMAIL_TEST_DELIVERY'](message)
        else:
            message['from'] = current_app.config['EMAIL_FROM']
            headers = {'Authorization': 'Bearer '+current_app.config['RESEND_API_KEY'],
                       'Content-Type': 'application/json', 'User-Agent': 'StudentSuccess/1.0',
                       'Idempotency-Key': record.digest}
            with urlopen(Request('https://api.resend.com/emails', data=json.dumps(message).encode(), headers=headers), timeout=10) as response:
                if response.status not in (200, 201, 202):
                    raise RuntimeError('Email delivery unavailable')
    except Exception:
        db.session.delete(record)
        db.session.commit()
        # Provider responses may contain private data; never log response bodies/tokens.
        current_app.logger.warning('Account email delivery failed')
        raise RuntimeError('Email could not be sent. Please try again later.') from None
