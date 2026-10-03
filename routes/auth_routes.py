from services.navigation import safe_page
from datetime import datetime, timedelta, timezone
import secrets

from flask import Blueprint, abort, g, redirect, render_template, request, session, url_for

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
        onboarding_completed=True,
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


def _sign_in(user):
    from services.access_service import csrf_token
    session.clear()
    session['user_id'] = user.id
    session['auth_version'] = user.auth_version
    session['_last_active'] = datetime.now(timezone.utc).isoformat()
    session.permanent = True
    csrf_token()


@auth_bp.before_request
def bound_auth_requests():
    if request.content_length and request.content_length > 16384:
        abort(413)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    from sqlalchemy.exc import IntegrityError
    from services.access_service import verify_csrf
    from services.account_policy import credential_errors, allow_attempt
    errors = []
    if session.get('user_id') and not session.get('demo_mode'):
        return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        verify_csrf()
        username = request.form.get('username', '').strip().lower()
        if not allow_attempt(username[:80], 'register'):
            return render_template('register.html', errors=['Too many attempts. Try again in 15 minutes.']), 429
        password = request.form.get('password', '')
        errors = credential_errors(username, password, request.form.get('confirm_password', ''))
        if request.form.get('understood') != 'yes':
            errors.append('Confirm that you are at least 13 and agree to the Terms of service.')
        if not errors:
            user = User(username=username, password_hash=hash_password(password))
            user.profile = StudentProfile(first_name='Planner', grade=9,
                graduation_year=datetime.now().year+4, current_gpa=0, target_gpa=0,
                study_hours_per_week=10, course_rigor='Balanced')
            db.session.add(user)
            from models.account_agreement import AccountAgreement
            db.session.add(AccountAgreement(user=user, version="2026-10-03"))
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                errors.append('That username is unavailable. Choose another.')
            else:
                _sign_in(user)
                return redirect(url_for('profile.onboarding'))
    return render_template('register.html', errors=errors), (400 if errors else 200)


_DUMMY_HASH = hash_password(secrets.token_urlsafe(24))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    from services.access_service import verify_csrf
    from services.account_policy import allow_attempt
    errors = []
    if request.method == 'POST':
        verify_csrf()
        supplied_username = request.form.get('username', '').strip()[:80]
        username = supplied_username.lower()
        if not allow_attempt(username, 'login'):
            return render_template('login.html', errors=['Too many attempts. Try again in 15 minutes.']), 429
        password = request.form.get('password', '')
        user = User.query.filter_by(username=supplied_username).first() or User.query.filter_by(username=username).first()
        valid = len(password) <= 128 and check_password(password, user.password_hash if user else _DUMMY_HASH)
        if not user or user.access_credential is not None or user.email is not None or not valid or user.username.startswith('demo-'):
            errors.append('Username or password was not recognized.')
        else:
            destination = safe_page(request.form.get('next')) or url_for('main.dashboard')
            _sign_in(user)
            return redirect(destination if user.onboarding_completed else url_for('profile.onboarding'))
    return render_template('login.html', errors=errors), (400 if errors else 200)


@auth_bp.route('/transfer-planner', methods=['GET', 'POST'])
def transfer():
    """One-time ownership transfer; the old credential cannot open the workspace."""
    from sqlalchemy.exc import IntegrityError
    from models import AccessCredential
    from services.access_service import code_digest, normalize_code, matches_code, verify_csrf
    from services.account_policy import credential_errors, allow_attempt
    errors = []
    existing = getattr(g, 'current_user', None)
    if existing and not (existing.access_credential or existing.email):
        return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        verify_csrf()
        username = request.form.get('username', '').strip().lower()
        if not allow_attempt(username[:80], 'transfer'):
            return render_template('transfer_planner.html', errors=['Too many attempts. Try again in 15 minutes.']), 429
        proof = request.form.get('previous_access', '')
        code = normalize_code(proof)
        credential = AccessCredential.query.filter_by(digest=code_digest(code)).first() if code else None
        user = existing or (credential.user if credential else None)
        valid = bool(user and (matches_code(proof, user.access_credential) if user.access_credential else check_password(proof, user.password_hash)))
        errors = credential_errors(username, request.form.get('password',''), request.form.get('confirm_password',''))
        if not valid:
            errors.append('Your previous account credential was not recognized.')
        if not errors:
            try:
                version = user.auth_version
                changed = User.query.filter_by(id=user.id, auth_version=version).update(dict(
                    username=username, password_hash=hash_password(request.form['password']), email=None,
                    auth_version=version+1, onboarding_completed=False), synchronize_session='fetch')
                if changed != 1:
                    db.session.rollback()
                    errors.append('This account changed. Reload and try again.')
                else:
                    if user.access_credential:
                        db.session.delete(user.access_credential)
                    db.session.commit()
                    _sign_in(user)
                    return redirect(url_for('profile.onboarding'))
            except IntegrityError:
                db.session.rollback()
                errors.append('That username is unavailable. Choose another.')
    return render_template('transfer_planner.html', errors=errors), (400 if errors else 200)


@auth_bp.post('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
