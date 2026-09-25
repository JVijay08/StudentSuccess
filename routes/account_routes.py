"""Email accounts activate only when delivery is configured. Legacy plans survive."""
from datetime import datetime, timezone
import secrets

from flask import Blueprint, abort, flash, g, redirect, render_template, request, session, url_for
from sqlalchemy.exc import IntegrityError

from extensions import db
from models import User, StudentProfile
from models.account_request import AccountRequest
from services import email_accounts as email
from services.access_service import matches_code, verify_csrf
from services.auth_service import check_password, hash_password, login_required
from services.navigation import safe_page
from services.task_policy import utc

account_bp = Blueprint('account', __name__)
_DUMMY_HASH = hash_password(secrets.token_urlsafe(24))


@account_bp.before_request
def bound_account_requests():
    if request.content_length and request.content_length > 16384:
        abort(413)


def sign_in(user):
    session.clear()
    session['user_id'] = user.id
    session['auth_version'] = user.auth_version
    session['_last_active'] = datetime.now(timezone.utc).isoformat()
    session.permanent = True


def account_page(mode, errors=None, sent=False, **context):
    return render_template('email_account.html', mode=mode, errors=errors or [], sent=sent, **context)


@account_bp.post('/account/signup')
def signup():
    verify_csrf()
    if not email.ready():
        return account_page('signup', ['Email signup is not available yet. Existing access still works.']), 503
    if session.get('user_id') and not session.get('demo_mode'):
        return redirect(url_for('account.upgrade'))
    try:
        address = email.normalize_email(request.form.get('email', ''))
    except ValueError as error:
        return account_page('signup', [str(error)]), 400
    errors = email.password_errors(request.form.get('password', ''), request.form.get('confirm_password', ''))
    if request.form.get('understood') != 'yes':
        errors.append('Confirm that you will keep personal identifiers and sensitive details out of tasks and course notes.')
    if errors:
        return account_page('signup', errors), 400
    if not email.allow_attempt(address, 'email'):
        return account_page('signup', ['Too many attempts. Try again in an hour.']), 429
    password_hash = hash_password(request.form['password'])
    if not User.query.filter_by(email=address).first():
        try:
            email.send_action(address, 'signup', password_hash=password_hash)
        except RuntimeError as error:
            return account_page('signup', [str(error)]), 503
    return account_page('signup', sent=True)


@account_bp.route('/account/login', methods=['GET','POST'])
def login():
    if request.method == 'GET':
        return account_page('login')
    verify_csrf()
    address = request.form.get('email', '').strip().lower()[:254]
    if not email.allow_attempt(address, 'login', limit=10):
        return account_page('login', ['Too many attempts. Try again in an hour.']), 429
    password = request.form.get('password', '')
    user = User.query.filter_by(email=address).first()
    # Run a password hash even for unknown accounts, without accepting an empty hash.
    stored = user.password_hash if user else _DUMMY_HASH
    valid = len(password) <= 128 and check_password(password, stored)
    if not user or not valid:
        return account_page('login', ['Email or password was not recognized.']), 400
    destination = safe_page(request.form.get('next')) or url_for('main.dashboard')
    sign_in(user)
    return redirect(destination)


@account_bp.route('/account/forgot-password', methods=['GET', 'POST'])
def forgot():
    if request.method == 'POST':
        verify_csrf()
        if not email.ready():
            return account_page('forgot', ['Email recovery is not available yet.']), 503
        address = request.form.get('email', '').strip().lower()[:254]
        if not email.allow_attempt(address, 'email'):
            return account_page('forgot', ['Too many attempts. Try again in an hour.']), 429
        user = User.query.filter_by(email=address).first()
        if user:
            try:
                email.send_action(address, 'reset', user=user)
            except RuntimeError as error:
                return account_page('forgot', [str(error)]), 503
        return account_page('forgot', sent=True)
    return account_page('forgot')


@account_bp.route('/account/upgrade', methods=['GET', 'POST'])
@login_required
def upgrade():
    if session.get('demo_mode'):
        flash('Create an account for your own planner. Demo data stays separate.', 'warning')
        return redirect(url_for('auth.register'))
    if g.current_user.email:
        return redirect(url_for('settings.settings'))
    errors = []
    if request.method == 'POST':
        verify_csrf()
        if not email.ready():
            return account_page('upgrade', ['Email setup is not available yet. Your current access still works.']), 503
        try:
            address = email.normalize_email(request.form.get('email', ''))
        except ValueError as error:
            return account_page('upgrade', [str(error)]), 400
        if not email.allow_attempt(address, 'email'):
            return account_page('upgrade', ['Too many attempts. Try again in an hour.']), 429
        credential = g.current_user.access_credential
        current = request.form.get('current_access', '')
        valid = matches_code(current, credential) if credential else check_password(current, g.current_user.password_hash)
        if not valid:
            errors.append('Your current code or password was not recognized.')
        errors.extend(email.password_errors(request.form.get('password', ''), request.form.get('confirm_password', '')))
        if errors:
            return account_page('upgrade', errors), 400
        if not User.query.filter_by(email=address).first():
            try:
                email.send_action(address, 'upgrade', g.current_user, hash_password(request.form['password']))
            except RuntimeError as error:
                return account_page('upgrade', [str(error)]), 503
        return account_page('upgrade', sent=True)
    return account_page('upgrade')


@account_bp.route('/account/confirm/<token>', methods=['GET', 'POST'])
def confirm(token):
    if len(token) > 100:
        abort(404)
    record = AccountRequest.query.filter_by(digest=email.digest(token)).first()
    if not record or utc(record.expires_at) <= datetime.now(timezone.utc):
        return account_page('expired'), 400
    user = db.session.get(User, record.user_id) if record.user_id else None
    if record.purpose != 'signup' and (not user or user.auth_version != record.auth_version):
        return account_page('expired'), 400
    if request.method == 'GET':
        # Email scanners and link previews must never consume a link.
        return account_page('confirm', purpose=record.purpose)
    verify_csrf()
    if record.purpose == 'reset':
        errors = email.password_errors(request.form.get('password', ''), request.form.get('confirm_password', ''))
        if errors:
            return account_page('confirm', errors, purpose='reset'), 400
        password_hash = hash_password(request.form['password'])
    else:
        password_hash = record.password_hash
    purpose, address, version = record.purpose, record.email, record.auth_version
    consumed = AccountRequest.query.filter_by(id=record.id, digest=record.digest).filter(
        AccountRequest.expires_at > datetime.now(timezone.utc)).delete(synchronize_session=False)
    if consumed != 1:
        db.session.rollback()
        return account_page('expired'), 400
    try:
        if purpose == 'signup':
            if User.query.filter_by(email=address).first():
                db.session.rollback()
                return account_page('expired'), 400
            user = User(username='email-'+secrets.token_hex(16), email=address,
                        password_hash=password_hash, auth_version=1)
            user.profile = StudentProfile(first_name='Planner', grade=9,
                graduation_year=datetime.now().year+4, current_gpa=0, target_gpa=0,
                study_hours_per_week=10, course_rigor='Balanced')
            db.session.add(user)
        else:
            changed = User.query.filter_by(id=user.id, auth_version=version).update(
                {'email': address, 'password_hash': password_hash, 'auth_version': version+1},
                synchronize_session='fetch')
            if changed != 1:
                db.session.rollback()
                return account_page('expired'), 400
            if purpose == 'upgrade' and user.access_credential:
                db.session.delete(user.access_credential)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return account_page('expired'), 400
    if purpose == 'reset':
        # A reset invalidates every old session, then asks for a fresh sign-in.
        session.clear()
        return account_page('reset_done')
    sign_in(user)
    flash('Email sign-in is ready. Your saved plan is here.', 'success')
    return redirect(url_for('main.dashboard'))
