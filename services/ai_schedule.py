"""Local, bounded scheduling of reviewed AI steps. No calendar data leaves the server."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


def utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def busy_intervals(tasks):
    return [(utc(t.planned_start_at), utc(t.planned_start_at) + timedelta(minutes=t.estimated_minutes))
            for t in tasks if t.status != 'completed' and t.planned_start_at and not t.children]


def spread(steps, first, daily_minutes, deadline, tasks, zone):
    now = datetime.now(timezone.utc)
    if first < now or not deadline or first >= utc(deadline):
        raise ValueError('Choose a future study start before the deadline.')
    if not 10 <= daily_minutes <= 480:
        raise ValueError('Choose 10 to 480 focused minutes per day.')
    # Break long steps into sessions; keep titles and the total workload intact.
    sessions = []
    for step in steps:
        remaining = step['minutes']
        part = 1
        while remaining:
            if len(sessions) >= 8:
                raise ValueError('This plan needs more than eight sessions. Increase daily minutes or reduce the work.')
            minutes = min(remaining, daily_minutes)
            title = step['title'] if step['minutes'] <= daily_minutes else step['title'][:140] + f' (session {part})'
            sessions.append(dict(title=title, minutes=minutes))
            remaining -= minutes
            part += 1
    busy = busy_intervals(tasks)
    local_first = first.astimezone(ZoneInfo(zone))
    day, used, cursor = 0, 0, first
    for step in sessions:
        duration = timedelta(minutes=step['minutes'])
        while True:
            if day > 365:
                raise ValueError('Choose a study window within the next year.')
            if used + step['minutes'] > daily_minutes:
                day += 1
                used = 0
                cursor = (local_first + timedelta(days=day)).astimezone(timezone.utc)
            end = cursor + duration
            collision = next(((a,b) for a,b in sorted(busy) if cursor < b and end > a), None)
            if collision:
                cursor = collision[1]
                if cursor.astimezone(ZoneInfo(zone)).date() != (local_first + timedelta(days=day)).date():
                    day += 1
                    used = 0
                    cursor = (local_first + timedelta(days=day)).astimezone(timezone.utc)
                continue
            if end > utc(deadline):
                raise ValueError('The work does not fit before the deadline. Increase daily time, reduce the work, or review the deadline.')
            step['planned_start_at'] = cursor.isoformat()
            busy.append((cursor, end))
            cursor = end + timedelta(minutes=10)
            used += step['minutes']
            break
    return sessions
