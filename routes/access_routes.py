from datetime import datetime, timezone
import secrets

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

from extensions import db
from models import AccessCredential, StudentProfile, User
from services.access_service import code_digest, create_code, matches_code, normalize_code, verify_csrf
from services.auth_service import hash_password, login_required


access_bp = Blueprint("access", __name__)


def _sign_in(user):
    session.clear()
    session["user_id"] = user.id
    session["access_version"] = user.access_credential.version
    session["_last_active"] = datetime.now(timezone.utc).isoformat()
    session.permanent = True


@access_bp.post("/access/create")
def create():
    verify_csrf()
    if session.get("user_id") and not session.get("demo_mode"):
        return redirect(url_for("main.dashboard"))
    if request.form.get("understood") != "yes":
        return render_template("register.html", errors=["Confirm that you understand how private codes and fictional data work."]), 400
    code = create_code()
    user = User(username="private-" + secrets.token_hex(16), password_hash=hash_password(secrets.token_urlsafe(32)))
    user.access_credential = AccessCredential(digest=code_digest(code), version=1)
    # Existing planning services require a profile. These are explicit fictional
    # planning defaults, not inferred personal attributes; GPA is unused here.
    user.profile = StudentProfile(first_name="Planner", grade=9,
        graduation_year=datetime.now().year + 4, current_gpa=0, target_gpa=0,
        study_hours_per_week=10, course_rigor="Balanced")
    db.session.add(user)
    db.session.commit()
    _sign_in(user)
    return render_template("access_code_created.html", code=code, replaced=False)


@access_bp.post("/access/open")
def open_planner():
    verify_csrf()
    code = normalize_code(request.form.get("access_code", ""))
    credential = AccessCredential.query.filter_by(digest=code_digest(code)).first() if code else None
    if credential is None:
        return render_template("login.html", errors=["That private code was not recognized. Check your saved copy; codes are case-sensitive."], form_data={}), 400
    _sign_in(credential.user)
    return redirect(url_for("main.dashboard"))


@access_bp.post("/access/replace")
@login_required
def replace():
    verify_csrf()
    credential = g.current_user.access_credential
    if not matches_code(request.form.get("access_code", ""), credential):
        flash("Enter your current private code to replace it.", "error")
        return redirect(url_for("settings.settings"))
    code = create_code()
    changed = AccessCredential.query.filter_by(
        id=credential.id, digest=credential.digest, version=credential.version,
    ).update({"digest": code_digest(code), "version": credential.version + 1}, synchronize_session=False)
    if changed != 1:
        db.session.rollback()
        flash("The code changed in another session. Sign in with the latest code before replacing it.", "error")
        return redirect(url_for("auth.login"))
    db.session.commit()
    _sign_in(g.current_user)
    return render_template("access_code_created.html", code=code, replaced=True)
