"""Shared task limits, deterministic ordering, and exact work blocks."""
from datetime import datetime, timezone

MAX_TASK_MINUTES = 10080


def subject_key(value):
    return " ".join((value or "").split()).casefold()


def utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def tier(task, now=None):
    now = utc(now or datetime.now(timezone.utc))
    if task.status == "completed":
        return 5
    if task.status == "in_progress":
        return 0
    if utc(task.due_at) < now:
        return 1
    if task.planned_start_at and utc(task.planned_start_at) <= now:
        return 2
    if (utc(task.due_at) - now).total_seconds() <= 86400:
        return 3
    return 4


def ranking_key(row, now=None):
    task = row["task"]
    return (tier(task, now), -row["score"], utc(task.due_at),
            utc(task.planned_start_at) if task.planned_start_at else datetime.max.replace(tzinfo=timezone.utc),
            getattr(task, "id", 0) or 0, getattr(task, "title", ""))


def split_minutes(total, block):
    if not 1 <= total <= MAX_TASK_MINUTES or not 1 <= block <= MAX_TASK_MINUTES:
        raise ValueError("Invalid work duration")
    full, remainder = divmod(total, block)
    return [block] * full + ([remainder] if remainder else [])
