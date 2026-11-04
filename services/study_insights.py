"""Small, accessible summaries of actual planner records, without inferred work time."""
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from services.task_policy import utc, subject_key


def study_insights(tasks, settings, budget, now=None):
    zone = ZoneInfo(settings.timezone_name)
    today = utc(now or datetime.now(timezone.utc)).astimezone(zone).date()
    first = 6 if settings.week_start == 'Sunday' else 0
    start = today - timedelta(days=(today.weekday() - first) % 7)
    counts = Counter()
    groups = defaultdict(lambda: dict(completed=0, active=0, estimated=0, actual=0, measured=0))
    weekly_minutes = measured = 0
    for task in tasks:
        if task.children:
            continue
        counts[task.status] += 1
        name = subject_key(task.subject) or 'No subject'
        group = groups[name]
        group['completed' if task.status == 'completed' else 'active'] += 1
        if (settings.time_tracking_enabled and task.status == 'completed' and not task.timing_excluded
                and task.actual_minutes is not None and task.completed_at is not None):
            group['estimated'] += task.estimated_minutes
            group['actual'] += task.actual_minutes
            group['measured'] += 1
            measured += 1
            date = utc(task.completed_at).astimezone(zone).date()
            if start <= date <= today:
                weekly_minutes += task.actual_minutes
    rows = [dict(name=name, **values) for name, values in sorted(groups.items())]
    scale = max((max(row['actual'], row['estimated']) for row in rows), default=0) or 1
    for row in rows:
        row['actual_width'] = round(row['actual'] / scale * 100, 1)
        row['estimated_width'] = round(row['estimated'] / scale * 100, 1)
    total = sum(counts.values())
    done = counts['completed']
    in_progress = counts['in_progress']
    return dict(total=total, completed=done, in_progress=in_progress, pending=counts['not_started'],
                done_pct=round(done / total * 100, 2) if total else 0,
                active_end_pct=round((done + in_progress) / total * 100, 2) if total else 0,
                courses=rows, measured=measured, weekly_minutes=weekly_minutes,
                weekly_hours=round(weekly_minutes / 60, 1), budget=budget,
                week_start=start.isoformat(), weekly_pct=min(100, round(weekly_minutes / (budget * 60) * 100)) if budget else 0)
