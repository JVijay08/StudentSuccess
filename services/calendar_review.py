"""Describe and apply explicit calendar refresh changes without overwriting stale previews."""
import hashlib
from datetime import datetime
from services.task_policy import utc


def fingerprint(task):
    return hashlib.sha256(f'{task.id}|{task.title}|{utc(task.due_at).isoformat()}|{task.status}'.encode()).hexdigest()


def review_events(events, tasks):
    existing = {t.external_uid: t for t in tasks if t.external_uid}
    seen = set()
    result = []
    for event in events:
        if event['uid'] in seen:
            continue
        seen.add(event['uid'])
        row = dict(event, action='add', previous=None, baseline=None)
        task = existing.get(event['uid'])
        if task:
            row['baseline'] = fingerprint(task)
            row['previous'] = dict(title=task.title, due_at=utc(task.due_at).isoformat())
            row['action'] = ('skip' if task.status == 'completed' or
                             (task.title == event['title'] and utc(task.due_at) == datetime.fromisoformat(event['due_at']))
                             else 'update')
        result.append(row)
    return result
