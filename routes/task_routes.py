from datetime import datetime, timezone

from flask import (
    Blueprint,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)

from extensions import db
from models import StudentProfile, Task
from services import (
    datetime_util,
    delay_service,
    priority_service,
    recurrence_service,
    suggestion_service,
)
from services.auth_service import login_required
from services.settings_service import get_or_create_settings
from services.privacy_service import confirmation_errors


def _flash_realism_warning(profile, task):
    """Flash a non-blocking realism warning for ``task`` when appropriate.

    Computes per-group averages from the profile's completed tasks and asks
    ``suggestion_service`` whether the task's deadline looks tight given the
    user's typical start delay. Never blocks the save; only flashes a message
    when a warning string is returned.
    """
    completed = Task.query.filter_by(
        student_profile_id=profile.id, status="completed"
    ).all()
    averages = delay_service.average_start_delay_by_group(completed)
    warning = suggestion_service.realism_warning(task, averages)
    if warning:
        flash(warning, "warning")


def _to_local_input(value, timezone_name="America/New_York"):
    """Format a stored UTC datetime as an Eastern ``datetime-local`` string.

    Returns an empty string when ``value`` is ``None`` so optional fields
    render as blank inputs.
    """
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    from zoneinfo import ZoneInfo
    return value.astimezone(ZoneInfo(timezone_name)).strftime("%Y-%m-%dT%H:%M")


def _validate_task_form(form, timezone_name="America/New_York"):
    """Validate task form input using the same rules as task creation.

    Returns a tuple of ``(cleaned, errors)`` where ``cleaned`` is a dict of
    parsed field values (only meaningful when ``errors`` is empty).
    """
    errors = confirmation_errors(form)

    title = form.get("title", "").strip()
    subject = form.get("subject", "").strip()
    task_type = form.get("task_type", "").strip()
    due_at_text = form.get("due_at", "").strip()
    planned_start_text = form.get("planned_start_at", "").strip()
    estimated_minutes_text = form.get("estimated_minutes", "").strip()
    difficulty = form.get("difficulty", "").strip().lower()
    interest_level = form.get("interest_level", "").strip().lower()
    reminder_enabled = "reminder_enabled" in form

    if not title:
        errors.append("Title is required.")
    elif len(title) > 160:
        errors.append("Title must be 160 characters or fewer.")

    try:
        due_at = datetime_util.to_utc(due_at_text, timezone_name)
    except ValueError:
        due_at = None
        errors.append("Enter a valid due date and time.")

    try:
        planned_start_at = (
            datetime_util.to_utc(planned_start_text, timezone_name)
            if planned_start_text
            else None
        )
    except ValueError:
        planned_start_at = None
        errors.append("Enter a valid planned start date and time.")

    try:
        estimated_minutes = int(estimated_minutes_text)
        if estimated_minutes < 1 or estimated_minutes > 1440:
            errors.append(
                "Estimated time must be between 1 and 1440 minutes."
            )
    except ValueError:
        estimated_minutes = None
        errors.append("Enter a valid estimated time.")

    if difficulty not in {"low", "medium", "high"}:
        errors.append("Choose how challenging this task is.")
    if interest_level not in {"low", "medium", "high"}:
        errors.append("Select a valid interest level.")

    recurrence_raw = (form.get("recurrence_rule") or "").strip()
    if recurrence_raw == "":
        recurrence_rule = None
    elif recurrence_raw in recurrence_service.ALLOWED_RULES:
        recurrence_rule = recurrence_raw
    else:
        errors.append("Select a valid recurrence option.")
        recurrence_rule = None

    cleaned = {
        "title": title,
        "subject": subject or None,
        "task_type": task_type or None,
        "due_at": due_at,
        "planned_start_at": planned_start_at,
        "estimated_minutes": estimated_minutes,
        "difficulty": difficulty,
        "interest_level": interest_level,
        "recurrence_rule": recurrence_rule,
        "reminder_enabled": reminder_enabled,
    }
    return cleaned, errors


task_bp = Blueprint("tasks", __name__)


@task_bp.route("/tasks", methods=["GET", "POST"])
@login_required
def tasks():
    profile = StudentProfile.query.filter_by(user_id=g.current_user.id).first()
    if profile is None:
        return redirect(url_for("profile.onboarding"))
    settings = get_or_create_settings(g.current_user)

    errors = []
    if request.method == "POST":
        cleaned, errors = _validate_task_form(request.form, settings.timezone_name)

        if not errors:
            task = Task(
                student_profile_id=profile.id,
                title=cleaned["title"],
                subject=cleaned["subject"],
                task_type=cleaned["task_type"],
                due_at=cleaned["due_at"],
                planned_start_at=cleaned["planned_start_at"],
                estimated_minutes=cleaned["estimated_minutes"],
                difficulty=cleaned["difficulty"],
                interest_level=cleaned["interest_level"],
                recurrence_rule=cleaned["recurrence_rule"],
                reminder_enabled=cleaned["reminder_enabled"],
            )
            db.session.add(task)
            db.session.commit()
            if task.recurrence_rule is not None:
                prep = Task(
                    student_profile_id=profile.id,
                    prep_for_id=task.id,
                    **recurrence_service.prep_task_fields(task),
                )
                db.session.add(prep)
                db.session.commit()
            _flash_realism_warning(profile, task)
            if settings.suggest_breakdown and task.estimated_minutes > settings.work_session_minutes:
                sessions = (task.estimated_minutes + settings.work_session_minutes - 1) // settings.work_session_minutes
                flash(f"Consider splitting this into {sessions} sessions of about {settings.work_session_minutes} minutes.", "warning")
            return redirect(url_for("tasks.tasks"))

    task_list = Task.query.filter_by(student_profile_id=profile.id).order_by(
        Task.due_at
    )
    task_rows = priority_service.get_prioritized_tasks(list(task_list))
    for row in task_rows:
        row["due_at_display"] = datetime_util.format_local(
            row["task"].due_at,
            settings.timezone_name,
            settings.time_format,
            settings.date_format,
            settings.relative_dates,
        )
    return render_template(
        "tasks.html",
        profile=profile,
        task_rows=task_rows,
        errors=errors,
        form_data=request.form or {"estimated_minutes": settings.default_task_minutes},
        settings=settings,
    )


@task_bp.route("/tasks/<int:task_id>/edit", methods=["GET", "POST"])
@login_required
def edit_task(task_id):
    task = db.get_or_404(Task, task_id)
    if task.student_profile.user_id != g.current_user.id:
        abort(404)

    profile = task.student_profile
    settings = get_or_create_settings(g.current_user)
    errors = []

    if request.method == "POST":
        cleaned, errors = _validate_task_form(request.form, settings.timezone_name)
        if not errors:
            task.title = cleaned["title"]
            task.subject = cleaned["subject"]
            task.task_type = cleaned["task_type"]
            task.due_at = cleaned["due_at"]
            task.planned_start_at = cleaned["planned_start_at"]
            task.estimated_minutes = cleaned["estimated_minutes"]
            task.difficulty = cleaned["difficulty"]
            task.interest_level = cleaned["interest_level"]
            task.recurrence_rule = cleaned["recurrence_rule"]
            task.reminder_enabled = cleaned["reminder_enabled"]
            db.session.commit()
            _flash_realism_warning(task.student_profile, task)
            return redirect(url_for("tasks.tasks"))

    if request.method == "POST":
        # Preserve the user's submitted edits when re-rendering with errors.
        form_data = {
            "title": request.form.get("title", ""),
            "subject": request.form.get("subject", ""),
            "task_type": request.form.get("task_type", ""),
            "due_at": request.form.get("due_at", ""),
            "planned_start_at": request.form.get("planned_start_at", ""),
            "estimated_minutes": request.form.get("estimated_minutes", ""),
            "difficulty": request.form.get("difficulty", "").strip().lower(),
            "interest_level": request.form.get(
                "interest_level", ""
            ).strip().lower(),
            "recurrence_rule": request.form.get("recurrence_rule", ""),
            "reminder_enabled": "reminder_enabled" in request.form,
        }
    else:
        form_data = {
            "title": task.title,
            "subject": task.subject or "",
            "task_type": task.task_type or "",
            "due_at": _to_local_input(task.due_at, settings.timezone_name),
            "planned_start_at": _to_local_input(task.planned_start_at, settings.timezone_name),
            "estimated_minutes": task.estimated_minutes,
            "difficulty": task.difficulty,
            "interest_level": task.interest_level,
            "recurrence_rule": task.recurrence_rule or "",
            "reminder_enabled": task.reminder_enabled,
        }

    return render_template(
        "task_edit.html",
        task=task,
        profile=profile,
        errors=errors,
        form_data=form_data,
        settings=settings,
    )


@task_bp.post("/tasks/<int:task_id>/start")
@login_required
def start_task(task_id):
    task = db.get_or_404(Task, task_id)
    if task.student_profile.user_id != g.current_user.id:
        abort(404)
    if task.started_at is None:
        task.started_at = datetime.now(timezone.utc)
    task.status = "in_progress"
    db.session.commit()
    if request.form.get("redirect_to") == "dashboard":
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("tasks.tasks"))


@task_bp.post("/tasks/<int:task_id>/reschedule")
@login_required
def reschedule_task(task_id):
    task = db.get_or_404(Task, task_id)
    if task.student_profile.user_id != g.current_user.id:
        abort(404)
    raw = request.form.get("planned_start_at", "").strip()
    if not raw:
        flash("Enter a new planned start date and time to reschedule.", "error")
        return redirect(url_for("main.dashboard"))
    try:
        settings = get_or_create_settings(g.current_user)
        new_planned = datetime_util.to_utc(raw, settings.timezone_name)
    except ValueError:
        flash("Enter a valid planned start date and time.", "error")
        return redirect(url_for("main.dashboard"))
    if new_planned <= datetime.now(timezone.utc):
        flash("Pick a planned start in the future.", "warning")
        return redirect(url_for("main.dashboard"))
    task.planned_start_at = new_planned
    db.session.commit()
    return redirect(url_for("main.dashboard"))


@task_bp.post("/tasks/<int:task_id>/snooze-reminder")
@login_required
def snooze_reminder(task_id):
    from datetime import timedelta

    task = db.get_or_404(Task, task_id)
    if task.student_profile.user_id != g.current_user.id:
        abort(404)
    settings = get_or_create_settings(g.current_user)
    task.reminder_snoozed_until = datetime.now(timezone.utc) + timedelta(
        minutes=settings.snooze_minutes
    )
    db.session.commit()
    flash(f"Reminder snoozed for {settings.snooze_minutes} minutes.", "success")
    return redirect(url_for("main.dashboard"))


@task_bp.post("/tasks/<int:task_id>/complete")
@login_required
def complete_task(task_id):
    task = db.get_or_404(Task, task_id)
    if task.student_profile.user_id != g.current_user.id:
        abort(404)
    actual_minutes_raw = request.form.get("actual_minutes", "").strip()
    if actual_minutes_raw:
        try:
            actual_minutes = int(actual_minutes_raw)
        except ValueError:
            actual_minutes = 0
        if actual_minutes < 1 or actual_minutes > 1440:
            flash("Actual time must be between 1 and 1440 minutes.", "error")
            return redirect(url_for("tasks.tasks"))
        task.actual_minutes = actual_minutes
    now = datetime.now(timezone.utc)
    if task.started_at is None:
        task.started_at = now
    task.completed_at = now
    task.status = "completed"
    db.session.commit()
    if task.recurrence_rule is not None:
        next_task = Task(
            student_profile_id=task.student_profile_id,
            **recurrence_service.next_occurrence_fields(task),
        )
        db.session.add(next_task)
        db.session.commit()
        prep = Task(
            student_profile_id=next_task.student_profile_id,
            prep_for_id=next_task.id,
            **recurrence_service.prep_task_fields(next_task),
        )
        db.session.add(prep)
        db.session.commit()
    return redirect(url_for("tasks.tasks"))


@task_bp.post("/tasks/<int:task_id>/undo-complete")
@login_required
def undo_complete_task(task_id):
    task = db.get_or_404(Task, task_id)
    if task.student_profile.user_id != g.current_user.id:
        abort(404)
    if task.status != "completed":
        flash("That task is not completed.", "warning")
        return redirect(url_for("tasks.tasks"))
    if task.recurrence_rule is not None:
        flash("Recurring completions cannot be undone because the next session was already created.", "warning")
        return redirect(url_for("tasks.tasks"))
    task.status = "in_progress" if task.started_at is not None else "not_started"
    task.completed_at = None
    task.actual_minutes = None
    db.session.commit()
    flash("Completion undone. You can correct the task and complete it again.", "success")
    return redirect(url_for("tasks.tasks"))


@task_bp.post("/tasks/<int:task_id>/delete")
@login_required
def delete_task(task_id):
    task = db.get_or_404(Task, task_id)
    if task.student_profile.user_id != g.current_user.id:
        abort(404)
    linked_preps = Task.query.filter_by(
        prep_for_id=task.id, student_profile_id=task.student_profile_id
    ).all()
    for prep in linked_preps:
        if prep.status != "completed":
            db.session.delete(prep)
    db.session.delete(task)
    db.session.commit()
    return redirect(url_for("tasks.tasks"))
