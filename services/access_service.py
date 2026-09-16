import hashlib
import re
import secrets

from flask import abort, request, session


def create_code():
    # 32 cryptographically random bytes (256 bits); never put this in a URL or cookie.
    return "SS-" + secrets.token_urlsafe(32)


def code_digest(code):
    return hashlib.sha256(code.encode("ascii")).hexdigest()


def normalize_code(value):
    value = value.strip()
    return value if re.fullmatch(r"SS-[A-Za-z0-9_-]{43}", value) else None


def matches_code(value, credential):
    code = normalize_code(value)
    return bool(code and credential and secrets.compare_digest(code_digest(code), credential.digest))


def csrf_token():
    if "access_csrf" not in session:
        session["access_csrf"] = secrets.token_urlsafe(32)
    return session["access_csrf"]


def verify_csrf():
    submitted = request.form.get("csrf_token", "")
    expected = session.get("access_csrf", "")
    if not expected or not secrets.compare_digest(submitted.encode("utf-8"), expected.encode("utf-8")):
        abort(400, "This form expired. Reload the page and try again.")
