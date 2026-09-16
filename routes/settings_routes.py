import json
from datetime import datetime, timezone
from zoneinfo import available_timezones

from flask import (
    Blueprint,
    Response,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from extensions import db
from models import StudentProfile, Task
from services.auth_service import check_password, hash_password, login_required
from services.settings_service import get_or_create_settings
from services.access_service import matches_code, verify_csrf


settings_bp = Blueprint("settings", __name__)

THEMES = {"system", "light", "dark", "high-contrast"}
TEXT_SCALES = {100, 125, 150, 200}
FONTS = {"system", "sans", "serif"}
DASHBOARD_MODES = {"standard", "focus"}
DENSITIES = {"comfortable", "compact"}
TONES = {"neutral", "direct", "encouraging"}
TIME_FORMATS = {"12-hour", "24-hour"}
WEEK_STARTS = {"Sunday", "Monday"}
DATE_FORMATS = {"month-first", "day-first", "year-first"}
SESSION_TIMEOUTS = {30, 60, 120, 480}
CARD_NAMES = {"overdue", "courses", "profile", "completion", "delay", "estimates", "history"}


def _choice(form, name, allowed, current):
    value = form.get(name, current)
    return value if value in allowed else current


def _integer_choice(form, name, allowed, current):
    try:
        value = int(form.get(name, current))
    except (TypeError, ValueError):
        return current
    return value if value in allowed else current


@settings_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    preferences = get_or_create_settings(g.current_user)
    if request.method == "POST":
        preferences.theme = _choice(request.form, "theme", THEMES, preferences.theme)
        preferences.text_scale = _integer_choice(request.form, "text_scale", TEXT_SCALES, preferences.text_scale)
        preferences.comfortable_spacing = "comfortable_spacing" in request.form
        preferences.reduce_motion = "reduce_motion" in request.form
        preferences.font_choice = _choice(request.form, "font_choice", FONTS, preferences.font_choice)
        preferences.dashboard_mode = _choice(request.form, "dashboard_mode", DASHBOARD_MODES, preferences.dashboard_mode)
        hidden_cards = sorted(set(request.form.getlist("hidden_cards")) & CARD_NAMES)
        preferences.hidden_dashboard_cards = ",".join(hidden_cards)
        preferences.card_density = _choice(request.form, "card_density", DENSITIES, preferences.card_density)
        preferences.default_task_minutes = _integer_choice(request.form, "default_task_minutes", {15, 25, 30, 45, 60, 90, 120}, preferences.default_task_minutes)
        preferences.work_session_minutes = _integer_choice(request.form, "work_session_minutes", {15, 20, 25, 30, 45, 50, 60}, preferences.work_session_minutes)
        preferences.start_buffer_days = _integer_choice(request.form, "start_buffer_days", {0, 1, 2, 3, 5, 7}, preferences.start_buffer_days)
        preferences.suggest_breakdown = "suggest_breakdown" in request.form
        preferences.recommendation_count = _integer_choice(request.form, "recommendation_count", {1, 2, 3, 5}, preferences.recommendation_count)
        preferences.recommendation_tone = _choice(request.form, "recommendation_tone", TONES, preferences.recommendation_tone)
        preferences.reminders_enabled = "reminders_enabled" in request.form
        preferences.reminder_lead_hours = _integer_choice(request.form, "reminder_lead_hours", {1, 3, 6, 12, 24, 48, 72}, preferences.reminder_lead_hours)
        preferences.quiet_start = request.form.get("quiet_start", preferences.quiet_start)[:5]
        preferences.quiet_end = request.form.get("quiet_end", preferences.quiet_end)[:5]
        preferences.snooze_minutes = _integer_choice(request.form, "snooze_minutes", {10, 15, 30, 60, 120, 1440}, preferences.snooze_minutes)
        preferences.calendar_export_enabled = "calendar_export_enabled" in request.form
        timezone_name = request.form.get("timezone_name", preferences.timezone_name)
        if timezone_name in available_timezones():
            preferences.timezone_name = timezone_name
        preferences.time_format = _choice(request.form, "time_format", TIME_FORMATS, preferences.time_format)
        preferences.week_start = _choice(request.form, "week_start", WEEK_STARTS, preferences.week_start)
        preferences.date_format = _choice(request.form, "date_format", DATE_FORMATS, preferences.date_format)
        preferences.relative_dates = "relative_dates" in request.form
        preferences.session_timeout_minutes = _integer_choice(request.form, "session_timeout_minutes", SESSION_TIMEOUTS, preferences.session_timeout_minutes)
        db.session.commit()
        flash("Settings saved.", "success")
        return redirect(url_for("settings.settings"))

    return render_template(
        "settings.html",
        settings=preferences,
        timezones=sorted(available_timezones()),
        card_names=sorted(CARD_NAMES),
    )


@settings_bp.post("/settings/password")
@login_required
def change_password():
    if g.current_user.access_credential is not None:
        flash("Use Replace private code to change access to this planner.", "warning")
        return redirect(url_for("settings.settings"))
    if session.get("demo_mode"):
        flash("The fictional demo account does not have a reusable password.", "warning")
        return redirect(url_for("settings.settings"))
    current = request.form.get("current_password", "")
    new = request.form.get("new_password", "")
    if not check_password(current, g.current_user.password_hash):
        flash("Current password is incorrect.", "error")
    elif len(new) < 8:
        flash("New password must be at least 8 characters.", "error")
    else:
        g.current_user.password_hash = hash_password(new)
        db.session.commit()
        flash("Password changed.", "success")
    return redirect(url_for("settings.settings"))


@settings_bp.post("/session/extend")
@login_required
def extend_session():
    session["_last_active"] = datetime.now(timezone.utc).isoformat()
    return {"status": "extended"}


@settings_bp.get("/settings/export")
@login_required
def export_data():
    profile = StudentProfile.query.filter_by(user_id=g.current_user.id).first()
    payload = {
        "username": g.current_user.username,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "profile": None,
        "tasks": [],
        "planned_courses": [],
    }
    if profile is not None:
        payload["profile"] = {
            "first_name": profile.first_name,
            "grade": profile.grade,
            "graduation_year": profile.graduation_year,
            "current_gpa": profile.current_gpa,
            "target_gpa": profile.target_gpa,
            "study_hours_per_week": profile.study_hours_per_week,
            "career_goals": profile.career_goals,
            "course_rigor": profile.course_rigor,
        }
        payload["tasks"] = [
            {
                "title": task.title,
                "subject": task.subject,
                "task_type": task.task_type,
                "due_at": task.due_at.isoformat(),
                "planned_start_at": task.planned_start_at.isoformat() if task.planned_start_at else None,
                "estimated_minutes": task.estimated_minutes,
                "status": task.status,
            }
            for task in profile.tasks
        ]
        payload["planned_courses"] = [
            {
                "catalog_id": item.catalog_id,
                "course_id": item.course_id,
                "school_year": item.school_year,
                "term": item.term,
                "status": item.status,
            }
            for item in profile.planned_courses
        ]
    return Response(
        json.dumps(payload, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=studentsuccess-data.json"},
    )


def _ics_escape(value):
    return str(value).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


@settings_bp.get("/settings/calendar.ics")
@login_required
def export_calendar():
    preferences = get_or_create_settings(g.current_user)
    if not preferences.calendar_export_enabled:
        abort(404)
    profile = StudentProfile.query.filter_by(user_id=g.current_user.id).first()
    tasks = [] if profile is None else Task.query.filter(Task.student_profile_id == profile.id, Task.status != "completed").order_by(Task.due_at).all()
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//StudentSuccess//Task Calendar//EN", "CALSCALE:GREGORIAN"]
    for task in tasks:
        due = task.due_at
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:task-{task.id}@studentsuccess",
            f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART:{due.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
            f"SUMMARY:{_ics_escape(task.title)} due",
            "END:VEVENT",
        ])
    lines.append("END:VCALENDAR")
    return Response("\r\n".join(lines) + "\r\n", mimetype="text/calendar", headers={"Content-Disposition": "attachment; filename=studentsuccess-tasks.ics"})


@settings_bp.post("/settings/clear-history")
@login_required
def clear_history():
    profile = StudentProfile.query.filter_by(user_id=g.current_user.id).first()
    if profile is not None:
        completed = Task.query.filter_by(
            student_profile_id=profile.id, status="completed"
        ).all()
        completed_ids = [task.id for task in completed]
        if completed_ids:
            Task.query.filter(Task.prep_for_id.in_(completed_ids)).update(
                {Task.prep_for_id: None}, synchronize_session=False
            )
        for task in completed:
            db.session.delete(task)
        db.session.commit()
    flash("Completed-task history cleared.", "success")
    return redirect(url_for("settings.settings"))


@settings_bp.post("/settings/delete-account")
@login_required
def delete_account():
    password = request.form.get("password", "")
    if g.current_user.access_credential is not None:
        verify_csrf()
        if not matches_code(request.form.get("access_code", ""), g.current_user.access_credential):
            flash("Enter your current private code to delete this planner.", "error")
            return redirect(url_for("settings.settings"))
    elif not session.get("demo_mode") and not check_password(password, g.current_user.password_hash):
        flash("Enter your current password to delete the account.", "error")
        return redirect(url_for("settings.settings"))
    user = g.current_user
    session.clear()
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for("main.home"))
