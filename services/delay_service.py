"""Pure start-delay computation for history-driven suggestions.

This module is intentionally pure: it performs no database writes and persists
no derived values. Start_Delay and Average_Start_Delay are computed on the fly
from existing Task fields. It is importable without a Flask app context.
"""

from datetime import datetime, timedelta, timezone

# Qualifying_Tasks per Group required before any bonus/warning is produced.
MINIMUM_SAMPLE = 2

# Below this magnitude a delay is reported as "On time".
_ZERO_TOLERANCE = timedelta(seconds=30)


def _as_utc(value: datetime) -> datetime:
    """Normalize a datetime to timezone-aware UTC.

    SQLite may return naive datetimes even for timezone-aware columns, so treat
    naive values as UTC before arithmetic. Mirrors the ``_as_utc`` helper in
    ``services/priority_service.py``.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def start_delay(task) -> "timedelta | None":
    """Return ``started_at - planned_start_at`` for a task.

    Both timestamps are normalized to UTC before subtraction. Positive means
    the student started late; negative means early. Returns ``None`` when either
    timestamp is missing.
    """
    if task.planned_start_at is None or task.started_at is None:
        return None
    return _as_utc(task.started_at) - _as_utc(task.planned_start_at)


def group_key(task) -> str:
    """Return the Group key for a task.

    Precedence: ``subject`` when non-empty, else ``task_type`` when non-empty,
    else the literal ``"ungrouped"``. ``None`` and whitespace-only values count
    as empty.
    """
    subject = task.subject
    if isinstance(subject, str) and subject.strip():
        return subject
    task_type = task.task_type
    if isinstance(task_type, str) and task_type.strip():
        return task_type
    return "ungrouped"


def average_start_delay_by_group(tasks) -> "dict[str, float]":
    """Mean Start_Delay in HOURS per group, from Qualifying_Tasks only.

    Qualifying_Tasks are completed tasks that have both ``planned_start_at`` and
    ``started_at``. Groups with fewer than ``MINIMUM_SAMPLE`` qualifying tasks
    are omitted from the returned dict; their absence is how callers detect
    "insufficient history". Performs no DB writes and persists nothing.
    """
    delays_by_group: "dict[str, list[float]]" = {}
    for task in tasks:
        if task.status != "completed":
            continue
        delay = start_delay(task)
        if delay is None:
            continue
        hours = delay.total_seconds() / 3600.0
        delays_by_group.setdefault(group_key(task), []).append(hours)

    averages: "dict[str, float]" = {}
    for key, hours_list in delays_by_group.items():
        if len(hours_list) < MINIMUM_SAMPLE:
            continue
        averages[key] = sum(hours_list) / len(hours_list)
    return averages


def format_start_delay(delay: "timedelta | None") -> str:
    """Human-readable delay string.

    - ``None`` -> "no start data"
    - within the zero tolerance (< 30s) -> "On time"
    - magnitude >= 60 minutes -> "<hours, 1 dp> hr late/early"
    - magnitude < 60 minutes -> "<minutes rounded> min late/early"

    Sign: positive delay -> "late"; negative -> "early".
    """
    if delay is None:
        return "no start data"

    if abs(delay) < _ZERO_TOLERANCE:
        return "On time"

    suffix = "late" if delay.total_seconds() > 0 else "early"
    magnitude_seconds = abs(delay.total_seconds())

    if magnitude_seconds >= 3600:
        hours = round(magnitude_seconds / 3600.0, 1)
        return f"{hours} hr {suffix}"

    minutes = round(magnitude_seconds / 60.0)
    return f"{minutes} min {suffix}"
