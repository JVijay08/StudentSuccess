"""Timestamp-derived timing charts; projects do not double-count their children."""
from statistics import mean, median
from services.delay_service import start_delay, format_start_delay
from services.burn_rate_service import is_measurable, actual_duration_minutes
from services.task_policy import subject_key, utc
from datetime import timedelta


def minutes_label(value):
    return f"{value / 60:.1f} hr" if abs(value) >= 60 else f"{value:.0f} min"


def timing_summary(tasks):
    completed = sorted((t for t in tasks if t.status == "completed" and not getattr(t, "children", [])),
                       key=lambda t: (utc(t.completed_at or t.due_at), t.id or 0))
    delays, durations, groups = [], [], {}
    for task in completed:
        delay = start_delay(task)
        if delay is not None:
            minutes = delay.total_seconds() / 60
            delays.append(dict(title=task.title, value=minutes, label=format_start_delay(delay), date=task.completed_at))
            key = subject_key(task.subject) or "No subject"
            groups.setdefault(key, []).append(minutes)
        if is_measurable(task):
            actual = actual_duration_minutes(task)
            if actual > 0:
                durations.append(dict(title=task.title, estimated=task.estimated_minutes, actual=actual,
                                      label=f"Estimated {minutes_label(task.estimated_minutes)}; actual {minutes_label(actual)}"))
    values = [r["value"] for r in delays]
    subjects = [dict(title=k, value=mean(v), label=format_start_delay(timedelta(minutes=mean(v)))) for k, v in sorted(groups.items()) if len(v) >= 2]
    for rows in (delays, subjects):
        scale = max((abs(r["value"]) for r in rows), default=1) or 1
        for row in rows:
            row["width"] = round(abs(row["value"]) / scale * 48, 2)
    scale = max((max(r["estimated"], r["actual"]) for r in durations), default=1)
    for row in durations:
        row["estimated_width"] = round(row["estimated"] / scale * 100, 2)
        row["actual_width"] = round(row["actual"] / scale * 100, 2)
    return dict(on_time_count=sum(v <= 0 for v in values),
                average_lateness=format_start_delay(timedelta(minutes=mean(max(0, v) for v in values))) if values else "No data yet",
                median_lateness=format_start_delay(timedelta(minutes=median(max(0, v) for v in values))) if values else "No data yet",
                count=len(values), average=format_start_delay(timedelta(minutes=mean(values))) if values else "—",
                median=format_start_delay(timedelta(minutes=median(values))) if values else "—",
                on_time=round(sum(v <= 0 for v in values) / len(values) * 100) if values else None,
                delays=delays[-20:], subjects=subjects, durations=durations[-20:])
