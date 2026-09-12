from datetime import datetime, timezone

from flask import Blueprint, redirect, render_template, request, session, url_for

from extensions import db
from models import User
from services.auth_service import check_password, hash_password


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    errors = []

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # Validate username
        if not username:
            errors.append("Username is required.")
        elif len(username) > 80:
            errors.append("Username must be 80 characters or fewer.")

        # Validate password
        if not password:
            errors.append("Password is required.")
        elif len(password) < 8:
            errors.append("Password must be at least 8 characters.")

        # Check for duplicate username (case-insensitive)
        if not errors:
            existing_user = User.query.filter_by(username=username.lower()).first()
            if existing_user is not None:
                errors.append("That username is already taken.")

        if not errors:
            user = User(
                username=username,
                password_hash=hash_password(password),
            )
            db.session.add(user)
            db.session.commit()

            # Log the new user in immediately
            session.clear()
            session["user_id"] = user.id
            session.permanent = True
            session["_last_active"] = datetime.now(timezone.utc).isoformat()

            return redirect(url_for("profile.onboarding"))

    return render_template(
        "register.html",
        errors=errors,
        form_data=request.form,
    )


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    errors = []

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username.lower()).first()

        if user is None or not check_password(password, user.password_hash):
            errors.append("Invalid username or password.")
        else:
            session.clear()
            session["user_id"] = user.id
            session.permanent = True
            session["_last_active"] = datetime.now(timezone.utc).isoformat()

            return redirect(url_for("main.dashboard"))

    return render_template(
        "login.html",
        errors=errors,
        form_data=request.form,
    )


@auth_bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
