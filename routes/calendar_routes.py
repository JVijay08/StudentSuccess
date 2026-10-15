"""Revocable, read-only calendar subscriptions. Raw tokens are never stored."""
import hashlib
import re
import secrets
from flask import Blueprint, Response, abort, current_app, g, redirect, render_template, session, url_for, flash
from extensions import db
from models import CalendarSubscription, User, StudentProfile, Task
from services.auth_service import login_required
from services.access_service import verify_csrf
from services.settings_service import get_or_create_settings
from services.calendar_export import calendar_file

calendar_bp = Blueprint('calendar_feed', __name__)


@calendar_bp.post('/calendar/subscription')
@login_required
def create():
    verify_csrf()
    preferences = get_or_create_settings(g.current_user)
    if session.get('demo_mode') or session.get('tutorial_mode') or not preferences.calendar_export_enabled:
        abort(403)
    token = secrets.token_urlsafe(32)
    subscription = db.session.get(CalendarSubscription, g.current_user.id)
    if subscription is None:
        subscription = CalendarSubscription(user_id=g.current_user.id)
        db.session.add(subscription)
    subscription.token_hash = hashlib.sha256(token.encode()).hexdigest()
    subscription.auth_version = g.current_user.auth_version
    db.session.commit()
    feed_url = current_app.config['PUBLIC_SITE_URL'].rstrip('/') + url_for('calendar_feed.feed', token=token)
    response = current_app.make_response(render_template('calendar.html', settings=preferences, subscription_active=True, feed_url=feed_url))
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response


@calendar_bp.post('/calendar/subscription/revoke')
@login_required
def revoke():
    verify_csrf()
    subscription = db.session.get(CalendarSubscription, g.current_user.id)
    if subscription:
        db.session.delete(subscription)
        db.session.commit()
    flash('Calendar subscription revoked. Remove the subscribed calendar in your calendar app to clear its saved events.', 'success')
    return redirect(url_for('settings.calendar_help'))


@calendar_bp.get('/calendar/feed/<token>.ics')
def feed(token):
    if not re.fullmatch(r'[A-Za-z0-9_-]{43}', token):
        abort(404)
    subscription = CalendarSubscription.query.filter_by(token_hash=hashlib.sha256(token.encode()).hexdigest()).first()
    user = db.session.get(User, subscription.user_id) if subscription else None
    if not user or user.auth_version != subscription.auth_version or not user.settings or not user.settings.calendar_export_enabled:
        abort(404)
    profile = StudentProfile.query.filter_by(user_id=user.id).first()
    tasks = [] if profile is None else Task.query.filter(Task.student_profile_id == profile.id, Task.status != 'completed').order_by(Task.due_at, Task.id).all()
    return Response(calendar_file(tasks, subscription=True), mimetype='text/calendar', headers={'Cache-Control':'no-store', 'X-Robots-Tag':'noindex, nofollow', 'Referrer-Policy':'no-referrer'})
