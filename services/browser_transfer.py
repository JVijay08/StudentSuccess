"""Validate and merge browser backups without replacing existing account records."""
import hashlib
import json
import math
from datetime import datetime, timezone

from extensions import db
from models import Task, PlannedCourse, TermCourse
from services.course_service import get_course_by_id, planned_course_details

MAX_BYTES = 1024 * 1024


def source_key(identifier):
    return 'browser:' + hashlib.sha256(identifier.encode()).hexdigest()


def _text(value, limit, label, required=False):
    if not isinstance(value, str) or len(value) > limit or (required and not value.strip()) or any(ord(c) < 32 for c in value):
        raise ValueError(f'Invalid {label}; use {1 if required else 0}–{limit} characters without control characters.')
    try:
        value.encode('utf-8')
    except UnicodeError:
        raise ValueError(f'Invalid characters in {label}.') from None
    return value.strip()


def _number(value, maximum, label, minimum=0, integer=False):
    if (type(value) not in (int, float) or not minimum <= value <= maximum or not math.isfinite(value)
            or (integer and int(value) != value)):
        raise ValueError(f'Invalid {label}; use a number from {minimum} to {maximum}.')
    return int(value) if integer else value


def _date(value):
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > 40:
        raise ValueError('Invalid task date.')
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if result.tzinfo is None:
            raise ValueError
        return result.astimezone(timezone.utc).isoformat()
    except (ValueError, OverflowError):
        raise ValueError('Task dates must include a timezone. Export a fresh browser backup.') from None


def validate_backup(raw):
    if len(raw) > MAX_BYTES:
        raise ValueError('Transfer backups up to 1 MB. Your browser plan has not changed.')
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeError, RecursionError):
        raise ValueError('Choose a valid StudentSuccess JSON backup.') from None
    if (not isinstance(data, dict) or data.get('version') != 1 or not isinstance(data.get('tasks'), list)
            or not isinstance(data.get('courses'), list) or len(data['tasks']) > 2000 or len(data['courses']) > 200):
        raise ValueError('Use a version 1 browser backup with up to 2,000 tasks and 200 courses.')
    context = data.get('context', 'high_school')
    if context not in {'high_school', 'college'}:
        raise ValueError('Invalid academic context.')
    budget = data.get('budget')
    if budget is not None:
        _number(budget, 168, 'study budget')
    tasks, courses, identifiers = [], [], set()
    for raw_task in data['tasks']:
        if not isinstance(raw_task, dict):
            raise ValueError('Invalid task.')
        identifier = _text(raw_task.get('id'), 100, 'task ID', True)
        if identifier in identifiers:
            raise ValueError('The backup has duplicate IDs.')
        identifiers.add(identifier)
        status = raw_task.get('status')
        if status not in {'not_started', 'in_progress', 'completed'}:
            raise ValueError('Invalid task status.')
        row = dict(id=identifier, title=_text(raw_task.get('title'), 160, 'task title', True),
                   subject=_text(raw_task.get('subject'), 80, 'subject'), status=status,
                   minutes=_number(raw_task.get('minutes'), 10080, 'task minutes', 1, True),
                   parent=raw_task.get('parent') or None)
        for field in ('due', 'planned', 'started', 'completed'):
            row[field] = _date(raw_task.get(field))
        if row['due'] is None:
            raise ValueError('Every task needs a due date.')
        row['actual'] = raw_task.get('actual')
        if row['actual'] is not None:
            _number(row['actual'], 10080, 'actual minutes', 1, True)
        for field in ('challenge', 'interest'):
            row[field] = raw_task.get(field, 'medium')
            if row[field] not in {'low', 'medium', 'high'}:
                raise ValueError('Invalid task rating.')
        tasks.append(row)
    by_id = {t['id']: t for t in tasks}
    for task in tasks:
        parent = task['parent']
        if parent is not None:
            if not isinstance(parent, str) or parent not in by_id or parent == task['id'] or by_id[parent]['parent']:
                raise ValueError('Subtasks must belong to one top-level assignment in the backup.')
            if by_id[parent]['status'] == 'completed' and task['status'] != 'completed':
                raise ValueError('A completed assignment has unfinished subtasks. Reopen it in the browser first.')
    for raw_course in data['courses']:
        if not isinstance(raw_course, dict):
            raise ValueError('Invalid course.')
        identifier = _text(raw_course.get('id'), 100, 'course ID', True)
        if identifier in identifiers:
            raise ValueError('The backup has duplicate IDs.')
        identifiers.add(identifier)
        course = dict(id=identifier, title=_text(raw_course.get('title'), 120 if context == 'college' else 2000, 'course title', True),
                      hours=_number(raw_course.get('hours'), 168, 'weekly course hours'),
                      year=raw_course.get('year', 9), term=_text(raw_course.get('term', 'Unassigned term'), 60, 'term'),
                      catalog=_text(raw_course.get('catalog', ''), 80, 'catalog'),
                      courseId=_text(raw_course.get('courseId', ''), 200, 'catalog course ID'),
                      depth=_text(raw_course.get('depth', 'Not rated'), 80, 'course depth'),
                      workload=raw_course.get('workload', 'Medium'))
        if type(course['year']) is not int or course['year'] not in (9, 10, 11, 12) or course['workload'] not in {'Low', 'Medium', 'High'}:
            raise ValueError('Invalid course year or workload.')
        courses.append(course)
    return dict(version=1, tasks=tasks, courses=courses, context=context, budget=budget)


def review_backup(data, user):
    existing_tasks = {t.external_uid: t for t in user.profile.tasks if t.external_uid}
    planned = user.profile.planned_courses
    terms = user.term_courses
    rows = []
    course_signatures = set()
    course_identities = set()
    for task in data['tasks']:
        key = source_key(task['id'])
        parent = existing_tasks.get(source_key(task['parent'])) if task['parent'] else None
        reason = 'Already transferred; keep account version' if key in existing_tasks else ('Parent is completed in this account' if parent and parent.status == 'completed' else '')
        rows.append(dict(kind='task', key=key, title=task['title'], skip=bool(reason), reason=reason, data=task))
    for course in data['courses']:
        key = source_key(course['id'])
        catalog_course = None
        if data['context'] == 'high_school' and course['catalog'] and course['courseId']:
            try:
                catalog_course = get_course_by_id(course['courseId'], course['catalog'])
            except ValueError:
                pass
        catalog = course['catalog'] if catalog_course else 'browser'
        identifier = course['courseId'] if catalog_course else key
        if data['context'] == 'college':
            signature = ('college', course['title'].casefold(), (course['term'] or 'Unassigned term').casefold())
            exists = any(c.browser_source_key == key or (c.title.casefold() == course['title'].casefold()
                         and c.term.casefold() == (course['term'] or 'Unassigned term').casefold()) for c in terms)
        else:
            signature = ('high_school', course['title'].casefold(), course['year'])
            exists = any((c.imported_details or {}).get('id') == course['id'] or
                         (c.school_year == course['year'] and
                          ((c.catalog_id == catalog and c.course_id == identifier) or
                           ((planned_course_details(c) or {}).get('course_name', '').casefold() == course['title'].casefold()))) for c in planned)
        identity = (data['context'], catalog, identifier, course['year'])
        duplicate = signature in course_signatures or identity in course_identities
        course_signatures.add(signature)
        course_identities.add(identity)
        rows.append(dict(kind='course', key=key, title=course['title'], skip=exists or duplicate,
                         reason='Already in the account plan' if exists else 'Duplicate course in this backup' if duplicate else '', data=course,
                         catalog=catalog, course_id=identifier))
    return rows


def import_backup(data, user, allowed_keys):
    rows = review_backup(data, user)
    tracked = user.settings.time_tracking_enabled
    mapping = {t.external_uid: t for t in user.profile.tasks if t.external_uid}
    count = 0
    # Parents first, including parents that already exist from a prior transfer.
    for row in sorted((r for r in rows if r['kind'] == 'task'), key=lambda r: bool(r['data']['parent'])):
        if row['skip'] or row['key'] not in allowed_keys:
            continue
        t = row['data']
        parent = mapping.get(source_key(t['parent'])) if t['parent'] else None
        if t['parent'] and parent is None:
            continue
        dt = lambda name: datetime.fromisoformat(t[name]) if t[name] else None
        task = Task(student_profile_id=user.profile.id, parent=parent, title=t['title'], subject=t['subject'],
                    due_at=dt('due'), planned_start_at=dt('planned'), estimated_minutes=t['minutes'],
                    started_at=dt('started') if tracked else None, completed_at=dt('completed'),
                    actual_minutes=t['actual'] if tracked else None, status=t['status'],
                    difficulty=t['challenge'], interest_level=t['interest'], external_uid=row['key'],
                    timing_excluded=not tracked or bool(t['started'] or t['completed']))
        db.session.add(task)
        mapping[row['key']] = task
        count += 1
    for row in rows:
        if row['kind'] != 'course' or row['skip'] or row['key'] not in allowed_keys:
            continue
        c = row['data']
        if data['context'] == 'college':
            db.session.add(TermCourse(user_id=user.id, title=c['title'], term=c['term'] or 'Unassigned term',
                                     weekly_hours=c['hours'], browser_source_key=row['key'], status='planned', imported_details=c))
        else:
            db.session.add(PlannedCourse(student_profile_id=user.profile.id, catalog_id=row['catalog'],
                                         course_id=row['course_id'], school_year=c['year'], term='Full year',
                                         status='planned', imported_details=c))
        count += 1
    return count
