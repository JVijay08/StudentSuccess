from datetime import datetime, timezone

from flask import Blueprint, redirect, render_template, request, url_for

from extensions import db
from models import StudentProfile, Task
from services.procrastination_service import explain_procrastination_risk


task_bp = Blueprint("tasks", __name__)


def _parse_datetime(value):
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


@task_bp.route("/tasks", methods=["GET", "POST"])
def tasks():
    profile = StudentProfile.query.first()
    if profile is None:
        return redirect(url_for("profile.onboarding"))

    errors = []
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        subject = request.form.get("subject", "").strip()
        task_type = request.form.get("task_type", "").strip()
        due_at_text = request.form.get("due_at", "").strip()
        planned_start_text = request.form.get("planned_start_at", "").strip()
        estimated_minutes_text = request.form.get(
            "estimated_minutes", ""
        ).strip()
        difficulty = request.form.get("difficulty", "").strip().lower()
        interest_level = request.form.get(
            "interest_level", ""
        ).strip().lower()

        if not title:
            errors.append("Title is required.")
        elif len(title) > 160:
            errors.append("Title must be 160 characters or fewer.")

        try:
            due_at = _parse_datetime(due_at_text)
        except ValueError:
            due_at = None
            errors.append("Enter a valid due date and time.")

        try:
            planned_start_at = (
                _parse_datetime(planned_start_text)
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
            errors.append("Select a valid difficulty.")
        if interest_level not in {"low", "medium", "high"}:
            errors.append("Select a valid interest level.")

        if not errors:
            task = Task(
                student_profile_id=profile.id,
                title=title,
                subject=subject or None,
                task_type=task_type or None,
                due_at=due_at,
                planned_start_at=planned_start_at,
                estimated_minutes=estimated_minutes,
                difficulty=difficulty,
                interest_level=interest_level,
            )
            db.session.add(task)
            db.session.commit()
            return redirect(url_for("tasks.tasks"))

    task_list = Task.query.filter_by(student_profile_id=profile.id).order_by(
        Task.due_at
    )
    task_rows = [
        (task, explain_procrastination_risk(task)) for task in task_list
    ]
    return render_template(
        "tasks.html",
        profile=profile,
        task_rows=task_rows,
        errors=errors,
        form_data=request.form,
    )


@task_bp.post("/tasks/<int:task_id>/start")
def start_task(task_id):
    task = db.get_or_404(Task, task_id)
    if task.started_at is None:
        task.started_at = datetime.now(timezone.utc)
    task.status = "in_progress"
    db.session.commit()
    return redirect(url_for("tasks.tasks"))


@task_bp.post("/tasks/<int:task_id>/complete")
def complete_task(task_id):
    task = db.get_or_404(Task, task_id)
    now = datetime.now(timezone.utc)
    if task.started_at is None:
        task.started_at = now
    task.completed_at = now
    task.status = "completed"
    db.session.commit()
    return redirect(url_for("tasks.tasks"))
