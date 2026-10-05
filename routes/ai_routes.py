import secrets
import json
from zoneinfo import ZoneInfo
from services.datetime_util import to_utc
from datetime import datetime, timedelta, timezone
from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, session, url_for
from sqlalchemy import update
from extensions import db
from models import Task
from models.ai_planning import AIDraft
from services.auth_service import login_required
from services.access_service import verify_csrf
from services import ai_planning as ai

ai_bp = Blueprint("ai", __name__)


def owned_task(task_id, lock=False):
    query = Task.query.filter_by(id=task_id)
    if lock:
        query = query.with_for_update()
    task = query.first_or_404()
    if task.student_profile.user_id != g.current_user.id:
        abort(404)
    return task


def eligible(task):
    return not task.parent_task_id and not task.children and not task.recurrence_rule and task.status == "not_started"


@ai_bp.before_request
def bounded_request():
    # Review can contain 32 edited Unicode titles plus their form fields.
    limit = 128 * 1024 if request.endpoint == "ai.review" else 16384
    if request.content_length and request.content_length > limit:
        abort(413)


@ai_bp.route("/tasks/ai/new", methods=["GET", "POST"])
@login_required
def new_assignment():
    from routes.task_routes import _validate_task_form
    from services.settings_service import get_or_create_settings
    settings = get_or_create_settings(g.current_user)
    available = ai.configured() and not session.get("demo_mode")
    if request.method == 'POST' and 'output_format' in request.form:
        from routes.ai_batch_review import generate_batch
        return generate_batch(settings, available)
    values = request.form.to_dict() if request.method == "POST" else {
        "estimated_minutes": settings.default_task_minutes, "autofill": "yes"}
    errors = []
    if request.method == "POST":
        verify_csrf()
        description = request.form.get("description", "").strip()
        fields = dict(title=(description.splitlines()[0][:160] if description else ""),
            subject=request.form.get("subject", ""), due_at=request.form.get("due_at", ""),
            estimated_minutes=request.form.get("estimated_minutes", ""))
        autofill = request.form.get("autofill") == "yes"
        cleaned, errors = _validate_task_form(fields, settings.timezone_name) if not autofill else ({}, [])
        if not 1 <= len(description) <= 2000:
            errors.append("Describe the assignment in 1 to 2,000 characters.")
        if request.form.get("consent") != "yes":
            errors.append("Confirm the sharing notice before requesting AI suggestions.")
        if not available:
            errors.append("AI drafting is unavailable right now. You can add a task manually.")
        if not errors:
            try:
                ai.reserve(g.current_user.id)
                if autofill:
                    suggestion = ai.generate_assignment(description, datetime.now(ZoneInfo(settings.timezone_name)).date().isoformat())
                    steps = suggestion.pop('steps')
                    cleaned = suggestion
                    cleaned['due_at'] = to_utc(suggestion['due_at'], settings.timezone_name) if suggestion['due_at'] else None
                else:
                    steps = ai.generate(description, cleaned["estimated_minutes"])
            except ai.AIUnavailable as exc:
                errors.append(str(exc))
            else:
                parent = dict(title=cleaned["title"], subject=cleaned["subject"],
                    due_at=cleaned["due_at"].isoformat() if cleaned["due_at"] else None,
                    estimated_minutes=cleaned["estimated_minutes"])
                draft = AIDraft(id=secrets.token_urlsafe(24), user_id=g.current_user.id,
                    task_id=0, snapshot=json.dumps(parent), steps=steps,
                    expires_at=datetime.now(timezone.utc)+timedelta(minutes=30))
                db.session.add(draft); db.session.commit()
                return redirect(url_for("ai.review", draft_id=draft.id))
    return render_template("ai_new_legacy.html" if request.args.get("classic") == "1" else "ai_new.html", values=values, errors=errors, available=available)


@ai_bp.route("/tasks/<int:task_id>/ai", methods=["GET", "POST"])
@login_required
def plan(task_id):
    task = owned_task(task_id)
    errors = []
    description = request.form.get("description", task.title).strip()
    available = ai.configured() and not session.get("demo_mode")
    if request.method == "POST":
        verify_csrf()
        if not eligible(task):
            errors.append("AI steps need an unstarted assignment with no subtasks or repeating schedule.")
        if not available:
            errors.append("AI is not available in this workspace. You can add steps manually.")
        if not 1 <= len(description) <= 2000:
            errors.append("Describe the assignment in 1 to 2,000 characters.")
        if request.form.get("consent") != "yes":
            errors.append("Confirm the sharing notice before requesting AI suggestions.")
        if not errors:
            baseline = ai.snapshot(task)
            try:
                ai.reserve(g.current_user.id)
                steps = ai.generate(description, task.estimated_minutes)
            except ai.AIUnavailable as exc:
                errors.append(str(exc))
            else:
                draft = AIDraft(id=secrets.token_urlsafe(24), user_id=g.current_user.id,
                    task_id=task.id, snapshot=baseline, steps=steps,
                    expires_at=datetime.now(timezone.utc)+timedelta(minutes=30))
                db.session.add(draft)
                db.session.commit()
                return redirect(url_for("ai.review", draft_id=draft.id))
    return render_template("ai_plan.html", task=task, errors=errors,
                           description=description, available=available, eligible=eligible(task))


@ai_bp.route("/ai/drafts/<draft_id>", methods=["GET", "POST"])
@login_required
def review(draft_id):
    draft = db.get_or_404(AIDraft, draft_id)
    if draft.user_id != g.current_user.id:
        abort(404)
    expires = draft.expires_at.replace(tzinfo=timezone.utc) if draft.expires_at.tzinfo is None else draft.expires_at
    if draft.consumed or expires < datetime.now(timezone.utc):
        flash("This draft was already used or expired. Your saved tasks are unchanged.", "warning")
        return redirect(url_for("tasks.tasks"))
    is_new = draft.task_id == 0
    if is_new:
        values = json.loads(draft.snapshot)
        if values.get('kind') == 'task_batch':
            from routes.ai_batch_review import review_batch
            return review_batch(draft)
        values["due_at"] = datetime.fromisoformat(values["due_at"]) if values["due_at"] else None
        task = Task(student_profile_id=g.current_user.profile.id,
                    status="not_started", **values)
    else:
        task = owned_task(draft.task_id, lock=request.method == "POST")
    from services.settings_service import get_or_create_settings
    settings = get_or_create_settings(g.current_user)
    errors, rows = [], draft.steps
    parent_due = (task.due_at.replace(tzinfo=timezone.utc) if task.due_at and task.due_at.tzinfo is None else task.due_at)
    due_input = parent_due.astimezone(ZoneInfo(settings.timezone_name)).strftime('%Y-%m-%dT%H:%M') if parent_due else ''
    if request.method == "POST":
        verify_csrf()
        if request.form.get("action") == "discard":
            db.session.delete(draft)
            db.session.commit()
            return redirect(url_for("tasks.tasks") if is_new else url_for("tasks.task_detail", task_id=task.id))
        if is_new:
            from routes.task_routes import _validate_task_form
            due_input = request.form.get('parent_due', due_input)
            fields = dict(title=request.form.get('parent_title', task.title),
                subject=request.form.get('parent_subject', task.subject or ''), due_at=due_input,
                estimated_minutes=request.form.get('parent_minutes', str(task.estimated_minutes)))
            cleaned, parent_errors = _validate_task_form(fields, settings.timezone_name)
            errors.extend(parent_errors)
            if not parent_errors:
                for key in ('title', 'subject', 'due_at', 'estimated_minutes'):
                    setattr(task, key, cleaned[key])
        if not is_new and (not eligible(task) or ai.snapshot(task) != draft.snapshot):
            errors.append("This assignment changed after the draft was created. Return to the task and generate a fresh draft.")
        rows = []
        try:
            selected = request.form.getlist("selected")
            if len(selected) != len(set(selected)):
                raise ValueError("Select each step only once.")
            for index in selected:
                if not index.isdigit() or not 0 <= int(index) < len(draft.steps):
                    raise ValueError("Choose steps from this draft.")
                rows.append({"title": request.form.get("title_"+index, ""),
                             "minutes": int(request.form.get("minutes_"+index, ""))})
            rows = ai.validate_steps(rows, task.estimated_minutes)
        except (ValueError, TypeError) as exc:
            errors.append(str(exc) if str(exc).startswith(("Choose", "Each", "Step", "The", "Select")) else "Enter whole minutes for the selected steps.")
        if not errors and request.form.get('action') == 'schedule':
            from services.ai_schedule import spread
            try:
                first = to_utc(request.form.get('first_start', ''), settings.timezone_name)
                others = Task.query.filter(Task.student_profile_id == task.student_profile_id,
                    Task.id != (task.id or 0)).all()
                scheduled = spread(rows, first, int(request.form.get('daily_minutes', '')),
                    task.due_at, others, settings.timezone_name)
            except (ValueError, OverflowError):
                errors.append('The schedule could not fit. Use a future start, 10 to 480 minutes per day, and a deadline with enough room for up to eight sessions. Existing planned work is kept in place.')
            else:
                draft.steps = scheduled
                if is_new:
                    draft.snapshot = json.dumps(dict(title=task.title, subject=task.subject,
                        due_at=task.due_at.isoformat(), estimated_minutes=task.estimated_minutes))
                db.session.commit()
                return redirect(url_for('ai.review', draft_id=draft.id))
        if not errors:
            from services.ai_schedule import utc, busy_intervals
            others = Task.query.filter(Task.student_profile_id == task.student_profile_id,
                Task.id != (task.id or 0)).all()
            busy = busy_intervals(others)
            try:
                for step, index in zip(rows, selected):
                    raw = request.form.get('start_' + index, draft.steps[int(index)].get('planned_start_at', ''))
                    start = to_utc(raw, settings.timezone_name) if raw else None
                    if start:
                        end = start + timedelta(minutes=step['minutes'])
                        if start < datetime.now(timezone.utc) or end > utc(task.due_at) or any(start < b and end > a for a,b in busy):
                            raise ValueError('Invalid study session')
                        busy.append((start,end))
                    step['planned_start_at'] = start
            except (ValueError, OverflowError):
                errors.append('A study session is in the past, overlaps planned work, or finishes after the deadline. Adjust its time or leave it blank.')
        if not errors:
            claimed = db.session.execute(update(AIDraft).where(
                AIDraft.id == draft.id, AIDraft.consumed.is_(False)).values(consumed=True))
            if claimed.rowcount != 1:
                db.session.rollback()
                flash("This draft has already been applied.", "warning")
                return redirect(url_for("tasks.task_detail", task_id=task.id))
            if is_new:
                db.session.add(task)
                db.session.flush()
                draft.task_id = task.id
            for step in rows:
                db.session.add(Task(student_profile_id=task.student_profile_id,
                    parent_task_id=task.id, title=step["title"], estimated_minutes=step["minutes"],
                    planned_start_at=step.get("planned_start_at"),
                    subject=task.subject, task_type=task.task_type, due_at=task.due_at,
                    difficulty=task.difficulty, interest_level=task.interest_level,
                    reminder_enabled=task.reminder_enabled))
            # Erase draft content immediately after applying; retain a replay guard until expiry.
            draft.steps = []
            db.session.commit()
            flash("Your reviewed steps and study times were saved. The assignment deadline is unchanged.", "success")
            return redirect(url_for("tasks.task_detail", task_id=task.id))
        db.session.rollback()
        # Preserve every submitted edit and selection when correcting a validation error.
        rows = [{"title":request.form.get(f"title_{i}", step["title"]),
                 "minutes":request.form.get(f"minutes_{i}", step["minutes"]),
                 "planned_start_at":request.form.get(f"start_{i}", step.get("planned_start_at", ""))}
                for i, step in enumerate(draft.steps)]
    for row in rows:
        start = row.get('planned_start_at')
        if start:
            try:
                row['start_input'] = to_utc(start, settings.timezone_name).astimezone(ZoneInfo(settings.timezone_name)).strftime('%Y-%m-%dT%H:%M')
            except (ValueError, TypeError):
                row['start_input'] = start
    selected = request.form.getlist("selected") if request.method == "POST" else [str(i) for i in range(len(rows))]
    return render_template("ai_review.html", task=task, draft=draft, rows=rows, selected=selected, errors=errors, is_new=is_new, due_input=due_input)
