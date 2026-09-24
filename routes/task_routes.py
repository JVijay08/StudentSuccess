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
from services.task_policy import MAX_TASK_MINUTES, split_minutes, subject_key, utc
from services.task_workspace import course_outline
from models.term_course import TermCourse
from services.auth_service import login_required
from services.settings_service import get_or_create_settings
from services.privacy_service import confirmation_errors
from services.navigation import return_url, back_url, nav_url


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
    if len(due_at_text) == 10:
        due_at_text += "T" + (form.get("due_time", "").strip() or "23:59")
    planned_start_text = form.get("planned_start_at", "").strip()
    estimated_minutes_text = form.get("estimated_minutes", "").strip()
    difficulty = form.get("difficulty", "medium").strip().lower()
    interest_level = form.get("interest_level", "medium").strip().lower()
    reminder_enabled = "reminder_enabled" in form

    if not title:
        errors.append("Title is required.")
    elif len(title) > 160:
        errors.append("Title must be 160 characters or fewer.")

    if len(subject) > 80 or len(task_type) > 40:
        errors.append("Subject must be at most 80 characters and task type at most 40.")

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
        if estimated_minutes < 1 or estimated_minutes > MAX_TASK_MINUTES:
            errors.append(
                f"Estimated time must be between 1 and {MAX_TASK_MINUTES} minutes."
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
        return redirect(nav_url("profile.onboarding"))
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
                blocks = split_minutes(task.estimated_minutes, settings.work_session_minutes)
                flash(f"Suggested work blocks: {len(blocks)} sessions, {sum(blocks)} minutes total; final block {blocks[-1]} minutes.", "warning")
            if request.form.get("_return_to"):
                flash("Task added to your queue.", "success")
                return redirect(return_url("tasks.tasks").split("#", 1)[0] + f"#task-{task.id}")
            return redirect(return_url("tasks.tasks"))

    task_list = Task.query.filter_by(student_profile_id=profile.id).order_by(
        Task.due_at
    )
    all_tasks = list(task_list)
    completed_tasks = sorted((t for t in all_tasks if t.status == "completed"), key=lambda t: (utc(t.completed_at or t.updated_at), t.id), reverse=True)
    task_rows = suggestion_service.get_suggested_tasks(all_tasks)
    sort = request.args.get("sort", "recommended")
    if sort in {"due", "planned", "subject", "status"}:
        task_rows.sort(key=lambda row: ((utc(row["task"].due_at).isoformat() if sort == "due" else utc(row["task"].planned_start_at).isoformat() if sort == "planned" and row["task"].planned_start_at else "9999" if sort == "planned" else subject_key(row["task"].subject) if sort == "subject" else row["task"].status), row["task"].id))
    for row in task_rows:
        row["due_at_display"] = datetime_util.format_local(
            row["task"].due_at,
            settings.timezone_name,
            settings.time_format,
            settings.date_format,
            settings.relative_dates,
        )
    course_names = [course.title[:80] for course in TermCourse.query.filter_by(user_id=g.current_user.id).all()]
    from services.course_service import load_courses
    catalogs = {planned.catalog_id: {course["course_id"]: course for course in load_courses(planned.catalog_id)}
                for planned in profile.planned_courses}
    for planned in profile.planned_courses:
        course = catalogs.get(planned.catalog_id, {}).get(planned.course_id)
        if course:
            course_names.append(course["course_name"][:80])
    outline = course_outline(all_tasks, task_rows, course_names)
    selected_course = request.args.get("course", "")[:80].strip()
    if selected_course:
        outline = [group for group in outline if subject_key(group["name"]) == subject_key(selected_course)]
    return render_template(
        "tasks.html",
        course_groups=outline,
        selected_course=selected_course,
        task_view="courses" if request.args.get("view") == "courses" else "queue",
        profile=profile,
        task_rows=task_rows,
        completed_tasks=completed_tasks,
        projects=[t for t in all_tasks if t.children and t.status != "completed"],
        subject_suggestions=sorted(set(course_names) | {t.subject for t in all_tasks if t.subject} | {"Math", "Science", "English", "History", "Computer Science"}),
        sort=sort,
        errors=errors,
        form_data=request.form or {"estimated_minutes": settings.default_task_minutes, "subject": request.args.get("subject", selected_course)[:80]},
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
        if task.children and cleaned.get("estimated_minutes") and cleaned["estimated_minutes"] < sum(c.estimated_minutes for c in task.children):
            errors.append("The project estimate cannot be less than its subtask total.")
        if (task.children or task.parent_task_id) and cleaned.get("recurrence_rule"):
            errors.append("Repeating tasks cannot be combined with subtasks.")
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
            flash("Task changes saved.", "success")
            return redirect(back_url("tasks.tasks"))

    if request.method == "POST":
        # Preserve the user's submitted edits when re-rendering with errors.
        form_data = {
            "title": request.form.get("title", ""),
            "subject": request.form.get("subject", ""),
            "task_type": request.form.get("task_type", ""),
            "due_at": request.form.get("due_at", ""),
            "planned_start_at": request.form.get("planned_start_at", ""),
            "estimated_minutes": request.form.get("estimated_minutes", ""),
            "difficulty": request.form.get("difficulty", "medium").strip().lower(),
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
    if task.children:
        flash("Start an unfinished subtask from the queue.", "warning")
        return redirect(return_url("tasks.tasks"))
    if task.status == "completed":
        message = "This task is already completed."
        message += " Find the next recurring session in the task queue." if task.recurrence_rule else " Use Undo completion in the task queue if you need to reopen it."
        flash(message, "warning")
        return redirect(return_url("main.dashboard" if request.form.get("redirect_to") == "dashboard" else "tasks.tasks"))
    if task.started_at is None:
        task.started_at = datetime.now(timezone.utc)
    task.status = "in_progress"
    _sync_parent(task)
    db.session.commit()
    if request.form.get("redirect_to") == "dashboard":
        return redirect(return_url("main.dashboard"))
    return redirect(return_url("tasks.tasks"))


@task_bp.post("/tasks/<int:task_id>/reschedule")
@login_required
def reschedule_task(task_id):
    task = db.get_or_404(Task, task_id)
    if task.student_profile.user_id != g.current_user.id:
        abort(404)
    raw = request.form.get("planned_start_at", "").strip()
    if not raw:
        flash("Enter a new planned start date and time to reschedule.", "error")
        return redirect(return_url("main.dashboard"))
    try:
        settings = get_or_create_settings(g.current_user)
        new_planned = datetime_util.to_utc(raw, settings.timezone_name)
    except ValueError:
        flash("Enter a valid planned start date and time.", "error")
        return redirect(return_url("main.dashboard"))
    if new_planned <= datetime.now(timezone.utc):
        flash("Pick a planned start in the future.", "warning")
        return redirect(return_url("main.dashboard"))
    task.planned_start_at = new_planned
    db.session.commit()
    return redirect(return_url("main.dashboard"))


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
    return redirect(return_url("main.dashboard"))


@task_bp.post("/tasks/<int:task_id>/complete")
@login_required
def complete_task(task_id):
    task = db.get_or_404(Task, task_id)
    if task.student_profile.user_id != g.current_user.id:
        abort(404)
    if task.status == "completed":
        flash("This task is already completed.", "success")
        return redirect(return_url("tasks.tasks"))
    if any(child.status != "completed" for child in task.children):
        flash("Complete the remaining subtasks first.", "warning")
        return redirect(return_url("tasks.tasks"))
    actual_minutes_raw = request.form.get("actual_minutes", "").strip()
    if actual_minutes_raw:
        try:
            actual_minutes = int(actual_minutes_raw)
        except ValueError:
            actual_minutes = 0
        if actual_minutes < 1 or actual_minutes > MAX_TASK_MINUTES:
            flash(f"Actual time must be between 1 and {MAX_TASK_MINUTES} minutes.", "error")
            return redirect(return_url("tasks.tasks"))
        task.actual_minutes = actual_minutes
    now = datetime.now(timezone.utc)
    if task.started_at is None:
        task.started_at = now
    task.completed_at = now
    task.status = "completed"
    _sync_parent(task)
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
    return redirect(return_url("tasks.tasks"))


@task_bp.post("/tasks/<int:task_id>/undo-complete")
@login_required
def undo_complete_task(task_id):
    task = db.get_or_404(Task, task_id)
    if task.student_profile.user_id != g.current_user.id:
        abort(404)
    if task.status != "completed":
        flash("That task is not completed.", "warning")
        return redirect(return_url("tasks.tasks"))
    if task.children:
        flash("Reopen a completed subtask to reopen this project.", "warning")
        return redirect(return_url("tasks.tasks"))
    if task.recurrence_rule is not None:
        flash("Recurring completions cannot be undone because the next session was already created.", "warning")
        return redirect(return_url("tasks.tasks"))
    task.status = "in_progress" if task.started_at is not None else "not_started"
    task.completed_at = None
    task.actual_minutes = None
    _sync_parent(task)
    db.session.commit()
    flash("Completion undone. You can correct the task and complete it again.", "success")
    return redirect(return_url("tasks.tasks"))


@task_bp.post("/tasks/<int:task_id>/delete")
@login_required
def delete_task(task_id):
    task = db.get_or_404(Task, task_id)
    if task.student_profile.user_id != g.current_user.id:
        abort(404)
    if task.children:
        flash("Remove or finish subtasks individually before deleting the project. History is preserved.", "warning")
        return redirect(return_url("tasks.tasks"))
    linked_preps = Task.query.filter_by(
        prep_for_id=task.id, student_profile_id=task.student_profile_id
    ).all()
    for prep in linked_preps:
        if prep.status != "completed":
            db.session.delete(prep)
    parent = task.parent
    if parent:
        parent.children.remove(task)
    db.session.delete(task)
    if parent and parent.children:
        _sync_parent(parent.children[0])
    db.session.commit()
    if request.form.get("_return_to"):
        flash("Task deleted.", "success")
        return redirect(return_url("tasks.tasks").split("#", 1)[0] + "#task-queue")
    return redirect(return_url("tasks.tasks"))


def _sync_parent(task):
    parent = task.parent
    if parent is None:
        return
    children = parent.children
    parent.status = "completed" if all(c.status == "completed" for c in children) else "in_progress" if any(c.started_at for c in children) else "not_started"
    parent.completed_at = max((utc(c.completed_at) for c in children if c.completed_at), default=None) if parent.status == "completed" else None
    parent.started_at = min((utc(c.started_at) for c in children if c.started_at), default=None)
    total = sum(c.actual_minutes or 0 for c in children)
    parent.actual_minutes = total if parent.status == "completed" and 0 < total <= MAX_TASK_MINUTES else None


@task_bp.post("/tasks/<int:task_id>/subtasks")
@login_required
def add_subtask(task_id):
    parent = db.get_or_404(Task, task_id)
    if parent.student_profile.user_id != g.current_user.id:
        abort(404)
    if parent.parent_task_id or parent.status == "completed" or parent.recurrence_rule:
        flash("Subtasks need an unfinished, non-recurring top-level task.", "error")
        return redirect(url_for("tasks.edit_task", task_id=task_id))
    settings = get_or_create_settings(g.current_user)
    values = request.form.to_dict()
    for key in ("subject", "task_type", "difficulty", "interest_level"):
        if not values.get(key):
            values[key] = getattr(parent, key) or ""
    if not values.get("due_at"):
        values["due_at"] = _to_local_input(parent.due_at, settings.timezone_name)
    cleaned, errors = _validate_task_form(values, settings.timezone_name)
    if errors:
        for error in errors:
            flash(error, "error")
    elif cleaned.get("recurrence_rule"):
        flash("Subtasks cannot repeat independently.", "error")
    elif sum(c.estimated_minutes for c in parent.children) + cleaned["estimated_minutes"] > parent.estimated_minutes:
        flash("Subtask estimates exceed the project total. Increase the project estimate first.", "error")
    else:
        child = Task(student_profile_id=parent.student_profile_id, parent=parent, **cleaned)
        db.session.add(child)
        _sync_parent(child)
        db.session.commit()
        flash("Subtask added.", "success")
    return redirect(url_for("tasks.edit_task", task_id=task_id))


@task_bp.post("/tasks/<int:task_id>/split")
@login_required
def split_task(task_id):
    parent = db.get_or_404(Task, task_id)
    if parent.student_profile.user_id != g.current_user.id:
        abort(404)
    if parent.parent_task_id or parent.children or parent.status != "not_started" or parent.recurrence_rule:
        flash("Split an unstarted, non-recurring task with no existing subtasks.", "error")
    else:
        settings = get_or_create_settings(g.current_user)
        for index, minutes in enumerate(split_minutes(parent.estimated_minutes, settings.work_session_minutes), 1):
            db.session.add(Task(student_profile_id=parent.student_profile_id, parent=parent,
                title=f"Work block {index}", subject=parent.subject, task_type=parent.task_type,
                due_at=parent.due_at, estimated_minutes=minutes, difficulty=parent.difficulty,
                interest_level=parent.interest_level, reminder_enabled=parent.reminder_enabled))
        db.session.commit()
        flash("Work blocks created. Their minutes exactly match the project estimate.", "success")
    return redirect(url_for("tasks.edit_task", task_id=task_id))


@task_bp.route("/tasks/import", methods=["GET", "POST"])
@login_required
def import_calendar():
    from flask import current_app
    from itsdangerous import URLSafeTimedSerializer, BadData
    from services.calendar_import import parse_calendar
    profile = g.current_user.profile
    if profile is None:
        return redirect(url_for("profile.onboarding"))
    signer = URLSafeTimedSerializer(current_app.secret_key, salt="calendar-preview")
    error, events, preview = None, [], None
    if request.method == "POST":
        try:
            errors = confirmation_errors(request.form)
            if errors:
                raise ValueError(errors[0])
            if request.form.get("confirm"):
                payload = signer.loads(request.form.get("preview", ""), max_age=1800)
                if payload["user"] != g.current_user.id:
                    abort(404)
                minutes = int(request.form.get("estimated_minutes", "60"))
                if not 1 <= minutes <= MAX_TASK_MINUTES:
                    raise ValueError("Enter a valid duration.")
                selected = {int(i) for i in request.form.getlist("selected")}
                existing = {t.external_uid for t in profile.tasks if t.external_uid}
                count = 0
                for index, event in enumerate(payload["events"]):
                    if index not in selected or event["uid"] in existing:
                        continue
                    db.session.add(Task(student_profile_id=profile.id, title=event["title"],
                        due_at=datetime.fromisoformat(event["due_at"]), estimated_minutes=minutes,
                        difficulty="medium", interest_level="medium", external_uid=event["uid"]))
                    existing.add(event["uid"])
                    count += 1
                db.session.commit()
                flash(f"Imported {count} assignments. Previously imported events were skipped.", "success")
                return redirect(url_for("tasks.tasks"))
            upload = request.files.get("calendar")
            if not upload:
                raise ValueError("Choose an .ics file.")
            events = parse_calendar(upload.read(1024 * 1024 + 1), get_or_create_settings(g.current_user).timezone_name)
            preview = signer.dumps({"user": g.current_user.id, "events": events})
        except (ValueError, UnicodeError, BadData):
            error = "Could not import this calendar. Confirm fictional data, use valid dates and durations, and keep the file below 1 MB and 200 events. Expired previews must be uploaded again."
    return render_template("calendar_import.html", events=events, preview=preview, error=error)
