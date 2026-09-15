from datetime import datetime, timedelta, timezone
import secrets

from flask import Blueprint, redirect, render_template, request, session, url_for

from extensions import db
from models import PlannedCourse, StudentProfile, Task, User
from services.auth_service import check_password, hash_password


auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/demo")
def start_demo():
    """Create an isolated fictional workspace for a public demo visitor."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=1)
    stale_demo_users = User.query.filter(
        User.username.startswith("demo-"), User.created_at < cutoff
    ).all()
    for stale_user in stale_demo_users:
        db.session.delete(stale_user)

    user = User(
        username=f"demo-{secrets.token_hex(6)}",
        password_hash=hash_password(secrets.token_urlsafe(24)),
    )
    db.session.add(user)
    db.session.flush()

    profile = StudentProfile(
        first_name="Alex",
        grade=11,
        graduation_year=datetime.now().year + 1,
        current_gpa=3.7,
        target_gpa=3.9,
        study_hours_per_week=12,
        career_goals="Engineering",
        course_rigor="Balanced",
        user_id=user.id,
    )
    db.session.add(profile)
    db.session.flush()

    now = datetime.now(timezone.utc)
    tasks = [
        Task(
            student_profile_id=profile.id,
            title="Finish algebra problem set",
            subject="Math",
            task_type="Homework",
            due_at=now + timedelta(hours=8),
            planned_start_at=now - timedelta(hours=1),
            estimated_minutes=50,
            difficulty="medium",
            interest_level="medium",
            status="not_started",
        ),
        Task(
            student_profile_id=profile.id,
            title="Draft biology lab conclusion",
            subject="Science",
            task_type="Project",
            due_at=now + timedelta(days=2),
            planned_start_at=now + timedelta(hours=4),
            estimated_minutes=75,
            difficulty="high",
            interest_level="high",
            status="not_started",
        ),
        Task(
            student_profile_id=profile.id,
            title="Outline history essay",
            subject="Social Studies",
            task_type="Essay",
            due_at=now + timedelta(days=4),
            planned_start_at=now + timedelta(days=1),
            estimated_minutes=45,
            difficulty="medium",
            interest_level="low",
            status="not_started",
        ),
    ]
    for index, delay_hours in enumerate((2, 1, -1, 0)):
        completed_at = now - timedelta(days=index + 1)
        planned_start = completed_at - timedelta(hours=3)
        tasks.append(
            Task(
                student_profile_id=profile.id,
                title=f"Completed practice set {index + 1}",
                subject="Math",
                task_type="Practice",
                due_at=completed_at,
                planned_start_at=planned_start,
                started_at=planned_start + timedelta(hours=delay_hours),
                completed_at=completed_at,
                estimated_minutes=60,
                difficulty="medium",
                interest_level="medium",
                status="completed",
            )
        )
    db.session.add_all(tasks)

    for course_id in (
        "NATIONAL_AP_ENGLISH_LANGUAGE",
        "MATH_AP_CALC_AB",
        "NATIONAL_CHEMISTRY",
        "NATIONAL_US_HISTORY",
        "NATIONAL_SPANISH_III",
    ):
        db.session.add(
            PlannedCourse(
                student_profile_id=profile.id,
                catalog_id="national",
                course_id=course_id,
                school_year=11,
                term="Full year",
                status="planned",
            )
        )

    db.session.commit()
    session.clear()
    session["user_id"] = user.id
    session["demo_mode"] = True
    session.permanent = True
    session["_last_active"] = now.isoformat()
    return redirect(url_for("main.dashboard"))


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
