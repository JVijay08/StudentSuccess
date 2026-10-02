import secrets
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
    if request.content_length and request.content_length > 16384:
        abort(413)


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
    task = owned_task(draft.task_id, lock=request.method == "POST")
    errors, rows = [], draft.steps
    if request.method == "POST":
        verify_csrf()
        if request.form.get("action") == "discard":
            db.session.delete(draft)
            db.session.commit()
            return redirect(url_for("tasks.task_detail", task_id=task.id))
        if not eligible(task) or ai.snapshot(task) != draft.snapshot:
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
        if request.form.get("nonpersonal_confirmed") != "yes":
            errors.append("Confirm the steps exclude personal identifiers and sensitive details.")
        if not errors:
            claimed = db.session.execute(update(AIDraft).where(
                AIDraft.id == draft.id, AIDraft.consumed.is_(False)).values(consumed=True))
            if claimed.rowcount != 1:
                db.session.rollback()
                flash("This draft has already been applied.", "warning")
                return redirect(url_for("tasks.task_detail", task_id=task.id))
            for step in rows:
                db.session.add(Task(student_profile_id=task.student_profile_id,
                    parent_task_id=task.id, title=step["title"], estimated_minutes=step["minutes"],
                    subject=task.subject, task_type=task.task_type, due_at=task.due_at,
                    difficulty=task.difficulty, interest_level=task.interest_level,
                    reminder_enabled=task.reminder_enabled))
            # Erase draft content immediately after applying; retain a replay guard until expiry.
            draft.steps = []
            db.session.commit()
            flash("Your reviewed steps were added. All share the assignment deadline; set planned starts when you are ready.", "success")
            return redirect(url_for("tasks.task_detail", task_id=task.id))
        db.session.rollback()
        # Preserve every submitted edit and selection when correcting a validation error.
        rows = [{"title":request.form.get(f"title_{i}", step["title"]),
                 "minutes":request.form.get(f"minutes_{i}", step["minutes"])}
                for i, step in enumerate(draft.steps)]
    selected = request.form.getlist("selected") if request.method == "POST" else [str(i) for i in range(len(rows))]
    return render_template("ai_review.html", task=task, draft=draft, rows=rows, selected=selected, errors=errors)
