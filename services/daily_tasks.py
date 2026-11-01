"""Partition active leaf tasks using the planner's local calendar day."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from services.task_policy import utc


def daily_task_rows(rows, timezone_name, now=None):
    now = utc(now or datetime.now(timezone.utc))
    zone = ZoneInfo(timezone_name)
    today = now.astimezone(zone).date()
    due_today, overdue = [], []
    for row in rows:
        task = row["task"]
        if task.status == "completed" or task.children:
            continue
        if utc(task.due_at) < now:
            overdue.append(row)
        elif (utc(task.due_at).astimezone(zone).date() == today
              or (task.planned_start_at and utc(task.planned_start_at).astimezone(zone).date() == today)):
            due_today.append(row)
    return due_today, overdue
