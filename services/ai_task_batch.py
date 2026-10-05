"""Bounded multi-task drafting. Persist only through the explicit review route."""
import json
from datetime import datetime
from services import ai_planning as ai

FORMATS = {'auto': 'Let AI choose', 'single': 'One standalone task',
           'project': 'One project with subtasks', 'multiple': 'Separate tasks',
           'mixed': 'Tasks and projects'}
STYLES = {'concise': 'Few broad steps', 'detailed': 'Smaller, specific steps', 'practice': 'Study sessions and self-checks'}


def options(form):
    result = {'format': form.get('output_format', 'auto'), 'style': form.get('detail_style', 'concise')}
    try:
        result['limit'] = int(form.get('task_limit', '5'))
        result['budget'] = int(form['total_budget']) if form.get('total_budget', '').strip() else None
    except (ValueError, TypeError):
        raise ValueError('Enter whole numbers for the task limit and optional total minutes.') from None
    if result['format'] not in FORMATS or result['style'] not in STYLES or not 1 <= result['limit'] <= 8:
        raise ValueError('Choose a task format, detail level, and a limit of 1 to 8 tasks.')
    if result['budget'] is not None and not 1 <= result['budget'] <= 10080:
        raise ValueError('Total focused minutes must be between 1 and 10080.')
    return result


def plain(value, maximum):
    if not isinstance(value, str) or len(value) > maximum or any(ord(c) < 32 for c in value):
        raise ValueError('Invalid text')
    if value:
        ai.validate_steps([dict(title=value, minutes=1)], 1)
    return value.strip()


def local_date(value):
    if not value:
        return ''
    if not isinstance(value, str) or len(value) != 16:
        raise ValueError('Invalid local date')
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is not None:
        raise ValueError('Expected local time')
    return value


def validate(value, opts):
    if not isinstance(value, list) or not 1 <= len(value) <= opts['limit']:
        raise ValueError('Invalid task count')
    if opts['format'] in {'single', 'project'} and len(value) != 1:
        raise ValueError('Expected one task')
    rows, count = [], 0
    for item in value:
        if not isinstance(item, dict):
            raise ValueError('Invalid task')
        title = plain(item.get('title'), 160)
        minutes = item.get('estimated_minutes')
        if not title or type(minutes) is not int or not 1 <= minutes <= 10080:
            raise ValueError('Invalid title or estimate')
        steps = item.get('steps', [])
        if not isinstance(steps, list):
            raise ValueError('Invalid steps')
        steps = ai.validate_steps(steps, minutes) if steps else []
        if opts['format'] in {'single', 'multiple'} and steps:
            raise ValueError('Standalone tasks cannot contain steps')
        if opts['format'] == 'project' and not steps:
            raise ValueError('Project needs steps')
        count += 1 + len(steps)
        if count > 32:
            raise ValueError('Too many task rows')
        rule = item.get('repeat_rule') or ''
        until = item.get('repeat_until') or ''
        if rule not in {'', 'daily', 'weekly', 'biweekly', 'monthly'}:
            raise ValueError('Invalid repeat rule')
        if until:
            if not isinstance(until,str) or len(until)!=10:
                raise ValueError('Invalid repeat end')
            datetime.strptime(until,'%Y-%m-%d')
        rows.append(dict(title=title, subject=plain(item.get('subject', ''),80),
            due_at=local_date(item.get('due_at')), estimated_minutes=minutes, steps=steps,
            task_type=plain(item.get('task_type', ''),40), difficulty='medium', interest_level='medium',
            planned_start_at=local_date(item.get('planned_start_at')), repeat_rule=rule, repeat_until=until, save_as='project'))
    if opts['budget'] is not None and sum(r['estimated_minutes'] for r in rows) > opts['budget']:
        raise ValueError('Draft exceeds total budget')
    return rows


def generate(description, today, opts):
    instruction = (
        ' Replace the single-assignment response schema for this request. Return JSON '
        '{"tasks":[{"title":"action or project","subject":"course or empty","due_at":"YYYY-MM-DDTHH:MM or null",'
        '"estimated_minutes":30,"task_type":"Homework or empty","planned_start_at":null,"repeat_rule":"","repeat_until":null,"steps":[{"title":"action","minutes":15}]}]}.'
        ' Each tasks entry is an independent task or project with its own deadline and subject.'
        ' Obey selected format: single means exactly one task with empty steps; project means one project with steps;'
        ' multiple means independent tasks with empty steps; mixed and auto allow both.'
        ' limit is a maximum, not a target; do not invent extra work. Maximum 8 steps per project and 32 total rows.'
        ' Interpret relative dates using local_today. If no deadline is stated return null; never invent one.'
        ' Use 23:59 for dates without times. Estimate realistic focused minutes, not the maximum budget.'
        ' Sum project steps within its estimate; budget, when set, caps the sum of top-level estimates.'
        ' Follow style, using checkpoints for practice. For recurring work draft one task per activity; due_at is the first occurrence.'
        ' Extract repeat_rule as daily, weekly, biweekly, monthly, or empty and repeat_until as YYYY-MM-DD or null.'
        ' Only include planned_start_at, recurrence, or repeat end if explicitly requested; do not invent availability or end dates.'
        ' No saved changes or tools.'
    )
    try:
        result = ai._request(json.dumps(dict(note=description, local_today=today, **opts)),
                             opts['budget'] or 10080, instruction, max_tokens=4500)
        return validate(result['tasks'], opts)
    except (ValueError, KeyError, TypeError):
        raise ai.AIUnavailable('AI could not produce a draft matching those options. Try fewer tasks or a simpler prompt.') from None
