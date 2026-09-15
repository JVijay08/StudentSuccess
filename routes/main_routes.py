from datetime import timezone

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from flask import Blueprint, g, redirect, render_template, session, url_for

from models import StudentProfile, Task
from services import (
    burn_rate_service,
    course_service,
    delay_service,
    nudge_service,
    suggestion_service,
)
from services.auth_service import login_required
from services.settings_service import get_or_create_settings


main_bp = Blueprint("main", __name__)


def _build_course_load_summary(profile):
    """Summarize the workload of courses planned for the student's current grade."""
    courses = []

    for planned in profile.planned_courses:
        if planned.school_year != profile.grade:
            continue
        try:
            course = course_service.get_course_by_id(
                planned.course_id, planned.catalog_id
            )
        except ValueError:
            course = None
        if course is not None:
            courses.append(course)

    return course_service.summarize_course_load(courses)


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
    if session.get("user_id") is not None:
        return redirect(url_for("main.dashboard"))
    return render_template("landing.html")


@main_bp.get("/planner")
def local_planner():
    return render_template("local_planner.html")


def _date_time_format(settings, include_time=False):
    date_formats = {
        "month-first": "%b %d, %Y",
        "day-first": "%d %b %Y",
        "year-first": "%Y-%m-%d",
    }
    value = date_formats.get(settings.date_format, "%b %d, %Y")
    if include_time:
        value += ", %H:%M" if settings.time_format == "24-hour" else ", %I:%M %p"
    return value


def _format_local(value, settings, include_time=False):
    local_value = _as_utc(value).astimezone(ZoneInfo(settings.timezone_name))
    if settings.relative_dates:
        today = datetime.now(timezone.utc).astimezone(
            ZoneInfo(settings.timezone_name)
        ).date()
        difference = (local_value.date() - today).days
        relative = {0: "Today", 1: "Tomorrow", -1: "Yesterday"}.get(difference)
        if relative:
            if include_time:
                clock = local_value.strftime(
                    "%H:%M" if settings.time_format == "24-hour" else "%I:%M %p"
                )
                return f"{relative}, {clock}"
            return relative
    return local_value.strftime(_date_time_format(settings, include_time))


def _build_start_history(profile, settings):
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
            completed_at_display = _format_local(task.completed_at, settings)
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
    settings = get_or_create_settings(g.current_user)
    active_task_count = 0
    prioritized_tasks = []
    success_rate = {"completed": 0, "total": 0, "percent": None}
    start_delay_summary = []
    start_history = []
    overdue_tasks = []
    estimate_accuracy = {"groups": [], "overall": None}
    course_load = None
    reminder_tasks = []

    if profile is not None:
        course_load = _build_course_load_summary(profile)
        all_tasks = Task.query.filter_by(
            student_profile_id=profile.id
        ).all()
        active_task_count = sum(
            1 for task in all_tasks if task.status != "completed"
        )
        prioritized_tasks = suggestion_service.get_suggested_tasks(all_tasks)
        success_rate = _build_success_rate(profile)
        start_delay_summary = _build_start_delay_summary(profile)
        start_history = _build_start_history(profile, settings)
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
                    "due_at_display": _format_local(
                        task.due_at, settings, include_time=True
                    ),
                    "overdue_display": nudge_service.format_overdue_amount(
                        row["overdue_amount"]
                    ),
                }
            )

        if settings.reminders_enabled:
            now = datetime.now(timezone.utc)
            local_now = now.astimezone(ZoneInfo(settings.timezone_name))
            current_time = local_now.strftime("%H:%M")
            quiet = (
                settings.quiet_start <= current_time < settings.quiet_end
                if settings.quiet_start < settings.quiet_end
                else current_time >= settings.quiet_start
                or current_time < settings.quiet_end
            )
            if not quiet:
                reminder_limit = now + timedelta(hours=settings.reminder_lead_hours)
                reminder_tasks = [
                    task
                    for task in all_tasks
                    if task.status != "completed"
                    and task.reminder_enabled
                    and _as_utc(task.due_at) <= reminder_limit
                    and (
                        task.reminder_snoozed_until is None
                        or _as_utc(task.reminder_snoozed_until) <= now
                    )
                ]

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
        course_load=course_load,
        reminder_tasks=reminder_tasks,
        settings=settings,
    )
