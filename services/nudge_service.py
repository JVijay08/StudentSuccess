"""Pure overdue-to-start detection for the dashboard nudge.

This module is intentionally pure: it performs no database writes and persists
no derived value. Overdue_To_Start membership and Overdue_Amount are computed on
the fly from existing Task fields. It is importable without a Flask app context.
"""

from datetime import datetime, timedelta, timezone


def _as_utc(value: datetime) -> datetime:
    """Normalize a datetime to timezone-aware UTC.

    SQLite may return naive datetimes even for timezone-aware columns, so treat
    naive values as UTC before comparison/arithmetic. Mirrors the ``_as_utc``
    helpers in ``services/delay_service.py`` and ``services/priority_service.py``.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def overdue_to_start(tasks, now=None) -> "list[dict]":
    """Return Overdue_To_Start tasks with their Overdue_Amount.

    ``now`` defaults to ``datetime.now(timezone.utc)`` and is resolved once so a
    single consistent instant governs the whole computation. A naive ``now`` is
    normalized to UTC via ``_as_utc``.

    A task is Overdue_To_Start when ALL hold (all datetimes normalized to UTC):
        - ``task.planned_start_at`` is not None
        - ``_as_utc(task.planned_start_at) < now``  (STRICTLY earlier; equal excluded)
        - ``task.started_at`` is None
        - ``task.status != "completed"``

    For each match, ``overdue_amount = now - _as_utc(task.planned_start_at)``
    (a positive ``timedelta``).

    Returns a list of dicts shaped as
    ``[{"task": task, "overdue_amount": timedelta}, ...]`` sorted by
    ``overdue_amount`` DESCENDING, ties broken by earlier ``due_at`` ASCENDING.
    Performs NO database writes, persists nothing, and does not mutate the input
    tasks.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    else:
        now = _as_utc(now)

    matches = []
    for task in tasks:
        if task.planned_start_at is None:
            continue
        if task.started_at is not None:
            continue
        if task.status == "completed":
            continue

        planned_utc = _as_utc(task.planned_start_at)
        if not (planned_utc < now):
            continue

        matches.append({"task": task, "overdue_amount": now - planned_utc})

    matches.sort(
        key=lambda row: (-row["overdue_amount"].total_seconds(), _as_utc(row["task"].due_at))
    )
    return matches


def format_overdue_amount(delta: timedelta) -> str:
    """Human-readable "how long ago the planned start was".

    Mirrors ``delay_service.format_start_delay`` unit conventions (hour/minute
    split at 3600 seconds):

        - magnitude >= 60 minutes -> "planned <hours, 1 dp> hr ago"
          (e.g. ``timedelta(hours=3)`` -> "planned 3.0 hr ago")
        - magnitude  < 60 minutes -> "planned <minutes rounded> min ago"
          (e.g. ``timedelta(minutes=25)`` -> "planned 25 min ago")

    Hours use one decimal place (``round(seconds / 3600, 1)``); minutes are
    rounded to the nearest whole minute (``round(seconds / 60)``). Phrasing is
    calm and non-shaming. ``delta`` is expected non-negative (Overdue_Amount is
    always positive for returned tasks).
    """
    magnitude = delta.total_seconds()

    if magnitude >= 3600:
        hours = round(magnitude / 3600.0, 1)
        return f"planned {hours} hr ago"

    minutes = round(magnitude / 60.0)
    return f"planned {minutes} min ago"
