from datetime import timezone

from flask import Blueprint, g, redirect, render_template, url_for

from models import StudentProfile, Task
from services import (
    burn_rate_service,
    datetime_util,
    delay_service,
    nudge_service,
    suggestion_service,
)
from services.auth_service import login_required


main_bp = Blueprint("main", __name__)


def _as_utc(value):
    """Normalize a datetime to timezone-aware UTC.

    SQLite may return naive datetimes even for ``DateTime(timezone=True)``
    columns, so treat any naive value as UTC before arithmetic. Mirrors the
    helper used in ``services/priority_service.py``.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _build_success_rate(profile):
    """Return completion stats for every task owned by ``profile``."""
    total = Task.query.filter_by(student_profile_id=profile.id).count()
    completed = Task.query.filter_by(
        student_profile_id=profile.id, status="completed"
    ).count()
    percent = round(completed / total * 100, 1) if total else None
    return {"completed": completed, "total": total, "percent": percent}


def _build_start_delay_summary(profile):
    """Summarize mean start delay per subject for completed tasks.

    Only completed tasks that have both ``planned_start_at`` and ``started_at``
    are eligible. The delay is ``started_at - planned_start_at`` measured in
    hours. Results are grouped by subject (``"No subject"`` when missing).
    """
    eligible_tasks = Task.query.filter(
        Task.student_profile_id == profile.id,
        Task.status == "completed",
        Task.planned_start_at.isnot(None),
        Task.started_at.isnot(None),
    ).all()

    grouped = {}
    for task in eligible_tasks:
        subject = task.subject if task.subject else "No subject"
        delta = _as_utc(task.started_at) - _as_utc(task.planned_start_at)
        grouped.setdefault(subject, []).append(delta.total_seconds() / 3600)

    summary = []
    for subject, delays in grouped.items():
        mean_hours = round(sum(delays) / len(delays), 1)
        if mean_hours > 0:
            label = "started late on average"
        elif mean_hours < 0:
            label = "started early on average"
        else:
            label = "on time on average"
        summary.append(
            {
                "subject": subject,
                "mean_delay_hours": mean_hours,
                "label": label,
            }
        )

    return summary


@main_bp.get("/")
def home():
    return redirect(url_for("main.dashboard"))


def _build_start_history(profile):
    """Return the profile's most recent completed tasks as display rows.

    Ordered by ``completed_at`` descending, limited to 10. Each row carries the
    title, group label (subject, else task_type, else "ungrouped"), a
    human-readable start delay, and the Eastern-local completion date. An empty
    list is returned when the profile has no completed tasks.
    """
    completed_tasks = (
        Task.query.filter_by(
            student_profile_id=profile.id, status="completed"
        )
        .order_by(Task.completed_at.desc())
        .limit(10)
        .all()
    )

    history = []
    for task in completed_tasks:
        completed_at_display = ""
        if task.completed_at is not None:
            completed_at_display = (
                _as_utc(task.completed_at)
                .astimezone(datetime_util.EASTERN)
                .strftime("%b %d, %Y")
            )
        history.append(
            {
                "title": task.title,
                "group_label": delay_service.group_key(task),
                "delay_display": delay_service.format_start_delay(
                    delay_service.start_delay(task)
                ),
                "completed_at_display": completed_at_display,
            }
        )
    return history


@main_bp.get("/dashboard")
@login_required
def dashboard():
    profile = StudentProfile.query.filter_by(user_id=g.current_user.id).first()
    active_task_count = 0
    prioritized_tasks = []
    success_rate = {"completed": 0, "total": 0, "percent": None}
    start_delay_summary = []
    start_history = []
    overdue_tasks = []
    estimate_accuracy = {"groups": [], "overall": None}

    if profile is not None:
        all_tasks = Task.query.filter_by(
            student_profile_id=profile.id
        ).all()
        active_task_count = sum(
            1 for task in all_tasks if task.status != "completed"
        )
        prioritized_tasks = suggestion_service.get_suggested_tasks(all_tasks)
        success_rate = _build_success_rate(profile)
        start_delay_summary = _build_start_delay_summary(profile)
        start_history = _build_start_history(profile)
        estimate_accuracy = {
            "groups": burn_rate_service.group_burn_rates(all_tasks),
            "overall": burn_rate_service.overall_burn_rate(all_tasks),
        }

        for row in nudge_service.overdue_to_start(all_tasks):
            task = row["task"]
            overdue_tasks.append(
                {
                    "task_id": task.id,
                    "title": task.title,
                    "group_label": task.subject
                    or task.task_type
                    or "ungrouped",
                    "due_at_display": _as_utc(task.due_at)
                    .astimezone(datetime_util.EASTERN)
                    .strftime("%b %d, %Y, %I:%M %p"),
                    "overdue_display": nudge_service.format_overdue_amount(
                        row["overdue_amount"]
                    ),
                }
            )

    return render_template(
        "dashboard.html",
        profile=profile,
        active_task_count=active_task_count,
        prioritized_tasks=prioritized_tasks,
        success_rate=success_rate,
        start_delay_summary=start_delay_summary,
        start_history=start_history,
        overdue_tasks=overdue_tasks,
        estimate_accuracy=estimate_accuracy,
    )
