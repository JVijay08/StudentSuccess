"""Pure recurrence date-math and field builders for recurring session tasks.

This module is intentionally pure: it performs no database writes and is
importable without a Flask application context. It uses only the standard
library (``datetime``, ``calendar.monthrange``, and ``zoneinfo`` via
``services.datetime_util.EASTERN``). The route/commit layer is responsible for
constructing ``Task`` rows, binding ``student_profile_id`` / ``prep_for_id``,
and committing.
"""

from calendar import monthrange
from datetime import datetime, timedelta, timezone

from services.datetime_util import EASTERN


ALLOWED_RULES = {"daily", "weekly", "biweekly", "monthly"}
DEFAULT_LEAD_TIME = timedelta(hours=24)

_DAY_DELTAS = {
    "daily": timedelta(days=1),
    "weekly": timedelta(days=7),
    "biweekly": timedelta(days=14),
}


def _as_utc(value: datetime) -> datetime:
    """Normalize a datetime to timezone-aware UTC.

    SQLite may return naive datetimes even for ``DateTime(timezone=True)``
    columns, so treat any naive value as UTC before arithmetic. Mirrors the
    ``_as_utc`` helpers in the other services so recurrence math is robust to
    naive reads from the database.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def advance(dt: datetime, rule: str) -> datetime:
    """Advance a tz-aware UTC datetime by one Recurrence_Interval, DST-safe.

    Strategy: convert to Eastern local wall-clock, perform the calendar step in
    local time (so the local time-of-day is preserved across DST), then convert
    back to UTC.

    - daily/weekly/biweekly: add 1 / 7 / 14 days to the LOCAL datetime.
    - monthly: advance to the same day-of-month in the next calendar month,
      clamping to the last valid day of the target month (Jan 31 -> Feb 28/29).

    Args:
        dt: A timezone-aware UTC datetime.
        rule: One of ``daily``/``weekly``/``biweekly``/``monthly``.

    Returns:
        A timezone-aware UTC datetime advanced by one interval.

    Raises:
        ValueError: If ``rule`` is not one of the four presets.
    """
    if rule not in ALLOWED_RULES:
        raise ValueError(f"Unknown recurrence rule: {rule!r}")

    local = _as_utc(dt).astimezone(EASTERN)

    if rule in _DAY_DELTAS:
        advanced_local = local + _DAY_DELTAS[rule]
    else:  # monthly
        year = local.year + (1 if local.month == 12 else 0)
        month = 1 if local.month == 12 else local.month + 1
        last_day = monthrange(year, month)[1]  # 28/29/30/31
        day = min(local.day, last_day)  # clamp Jan 31 -> Feb 28/29
        advanced_local = local.replace(year=year, month=month, day=day)

    return advanced_local.astimezone(timezone.utc)


def next_occurrence_fields(session_task) -> dict:
    """Pure field-value dict for the next Occurrence of a recurring session.

    Copies identity/attribute fields, advances datetimes by the rule, and resets
    the lifecycle. The route constructs the ``Task`` and sets
    ``student_profile_id``.
    """
    rule = session_task.recurrence_rule
    planned = session_task.planned_start_at
    return {
        "title": session_task.title,
        "subject": session_task.subject,
        "task_type": session_task.task_type,
        "estimated_minutes": session_task.estimated_minutes,
        "difficulty": session_task.difficulty,
        "interest_level": session_task.interest_level,
        "recurrence_rule": rule,  # copied forward
        "due_at": advance(session_task.due_at, rule),
        "planned_start_at": advance(planned, rule) if planned else None,
        "status": "not_started",
        "started_at": None,
        "completed_at": None,
    }


def prep_task_fields(session_task, lead_time: timedelta = DEFAULT_LEAD_TIME) -> dict:
    """Pure field-value dict for a Prep_Task for the given session task.

    The route sets ``student_profile_id`` and ``prep_for_id`` (= the session
    task's id, known only after the session is committed).
    """
    title = f"Prep: {session_task.title}"[:160]  # truncate to <=160
    return {
        "title": title,
        "subject": session_task.subject,
        "task_type": "Lesson prep",
        "due_at": _as_utc(session_task.due_at) - lead_time,  # Lead_Time before session
        "planned_start_at": None,
        "estimated_minutes": 30,
        "difficulty": "medium",
        "interest_level": "medium",
        "status": "not_started",
        "started_at": None,
        "completed_at": None,
        "recurrence_rule": None,  # prep never recurs
    }
