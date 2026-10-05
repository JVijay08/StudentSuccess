"""Multi-task AI review, sharing the existing owned, expiring draft endpoint."""
import copy
import json
import secrets
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from flask import request, g, render_template, redirect, url_for, flash
from sqlalchemy import update
from extensions import db
from models import Task
from models.ai_planning import AIDraft
from services import ai_planning as ai, ai_task_batch as batch
from services.access_service import verify_csrf
from services.settings_service import get_or_create_settings
from services.datetime_util import to_utc
from services.recurrence_service import bounded_dates, advance
from services.ai_schedule import busy_intervals


def generate_batch(settings, available):
    verify_csrf()
    values = request.form.to_dict()
    errors = []
    description = request.form.get('description', '').strip()
    try:
        opts = batch.options(request.form)
        subject = batch.plain(request.form.get('default_subject',''),80)
        deadline = batch.local_date(request.form.get('default_due',''))
    except ValueError as exc:
        errors.append(str(exc))
    if not 1 <= len(description) <= 2000:
        errors.append('Describe your tasks in 1 to 2,000 characters.')
    if request.form.get('consent') != 'yes':
        errors.append('Confirm the sharing notice before requesting AI suggestions.')
    if not available:
        errors.append('AI drafting is unavailable. You can still add tasks manually.')
    if not errors:
        try:
            ai.reserve(g.current_user.id)
            rows = batch.generate(description, datetime.now(ZoneInfo(settings.timezone_name)).date().isoformat(),opts)
        except ai.AIUnavailable as exc:
            errors.append(str(exc))
        else:
            for row in rows:
                if subject: row['subject'] = subject
                if deadline: row['due_at'] = deadline
            draft=AIDraft(id=secrets.token_urlsafe(24),user_id=g.current_user.id,task_id=0,
                snapshot=json.dumps(dict(kind='task_batch',options=opts)),steps=rows,
                expires_at=datetime.now(timezone.utc)+timedelta(minutes=30))
            db.session.add(draft);db.session.commit()
            return redirect(url_for('ai.review',draft_id=draft.id))
    return render_template('ai_new.html',values=values,errors=errors,available=available)


def submitted_rows(original):
    rows=copy.deepcopy(original)
    for i,row in enumerate(rows):
        for key in ('title','subject','due_at','estimated_minutes','task_type','difficulty',
                    'interest_level','planned_start_at','repeat_rule','repeat_until','save_as'):
            row[key]=request.form.get(f'{key}_{i}',str(row.get(key,'')))
        for j,step in enumerate(row['steps']):
            step['title']=request.form.get(f'step_title_{i}_{j}',step['title'])
            step['minutes']=request.form.get(f'step_minutes_{i}_{j}',str(step['minutes']))
    return rows


def checked_indices(name, count):
    selected=request.form.getlist(name)
    if len(set(selected)) != len(selected) or any(not i.isdigit() or not 0 <= int(i) < count for i in selected):
        raise ValueError('Choose each item from this draft only once.')
    return [int(i) for i in selected]


def prepare(rows, selected, settings, budget):
    from routes.task_routes import _validate_task_form
    prepared=[]
    busy=busy_intervals(Task.query.filter_by(student_profile_id=g.current_user.profile.id).all())
    total=0
    for i in selected:
        row=rows[i]
        cleaned,errors=_validate_task_form(row,settings.timezone_name)
        if errors: raise ValueError(f'Task {i+1}: '+ ' '.join(errors))
        steps=[]
        for j in checked_indices(f'steps_{i}',len(row['steps'])):
            steps.append(dict(title=row['steps'][j]['title'],minutes=int(row['steps'][j]['minutes'])))
        if steps: steps=ai.validate_steps(steps,cleaned['estimated_minutes'])
        if row.get('save_as','project') not in ('project','separate'):
            raise ValueError('Choose project or separate tasks.')
        separate=row.get('save_as')=='separate' and bool(steps)
        dates=[cleaned['due_at']]
        rule=row.get('repeat_rule','')
        if rule:
            if rule not in {'daily','weekly','biweekly','monthly'}:
                raise ValueError('Choose a supported repeat interval.')
            first=cleaned['due_at'].astimezone(ZoneInfo(settings.timezone_name))
            end=datetime.fromisoformat(row['repeat_until']).date()
            dates=bounded_dates(first.date(),first.replace(year=end.year,month=end.month,day=end.day),rule,settings.timezone_name)
        planned=cleaned['planned_start_at']
        if planned and steps:
            raise ValueError(f'Task {i+1}: leave the planned start blank for a project; schedule its steps after saving.')
        total+=cleaned['estimated_minutes']*len(dates)
        for due in dates:
            if planned:
                finish=planned+timedelta(minutes=cleaned['estimated_minutes'])
                if planned < datetime.now(timezone.utc) or finish>due or any(planned<b and finish>a for a,b in busy):
                    raise ValueError(f'Task {i+1}: the planned time is in the past, overlaps another task, or ends after its deadline.')
                busy.append((planned,finish))
            fields={key:cleaned[key] for key in ('title','subject','estimated_minutes','task_type','difficulty','interest_level')}
            fields.update(due_at=due,planned_start_at=planned,reminder_enabled=settings.reminders_enabled)
            prepared.append((fields,steps,separate))
            if sum((len(s) if independent else 1+len(s)) for _,s,independent in prepared)>100:
                raise ValueError('This selection would create more than 100 tasks. Shorten the repeat range or select fewer items.')
            if planned and rule: planned=advance(planned,rule,settings.timezone_name)
    if budget is not None and total>budget:
        raise ValueError('The selected work, including repetitions, exceeds your total minute budget. Reduce estimates, items, or repetitions.')
    return prepared


def review_batch(draft):
    settings=get_or_create_settings(g.current_user)
    metadata=json.loads(draft.snapshot)
    rows=copy.deepcopy(draft.steps)
    errors=[]
    selected=[str(i) for i in range(len(rows))]
    step_selected={i:[str(j) for j in range(len(row['steps']))] for i,row in enumerate(rows)}
    preview_count=None
    if request.method=='POST':
        verify_csrf()
        if request.form.get('action')=='discard':
            db.session.delete(draft);db.session.commit()
            return redirect(url_for('tasks.tasks'))
        rows=submitted_rows(rows)
        selected=request.form.getlist('selected')
        step_selected={i:request.form.getlist(f'steps_{i}') for i in range(len(rows))}
        try:
            if request.form.get('action') not in ('apply','preview'):
                raise ValueError('Choose Preview or Save.')
            indices=checked_indices('selected',len(rows))
            if not indices: raise ValueError('Select at least one task to save.')
            prepared=prepare(rows,indices,settings,metadata['options'].get('budget'))
        except (ValueError, TypeError, OverflowError) as exc:
            message=str(exc)
            errors.append(message if message.startswith(('Task ', 'Choose ', 'Select ', 'This ', 'The ', 'Each ', 'Step ')) else 'Check dates, repeat-through dates, and whole-minute estimates for the selected tasks.')
        else:
            preview_count=sum(len(steps) if separate else 1+len(steps) for _,steps,separate in prepared)
            if request.form.get('action')=='apply':
                claimed=db.session.execute(update(AIDraft).where(AIDraft.id==draft.id,AIDraft.consumed.is_(False)).values(consumed=True))
                if claimed.rowcount!=1:
                    db.session.rollback()
                    flash('This draft has already been saved.','warning')
                    return redirect(url_for('tasks.tasks'))
                for fields,steps,separate in prepared:
                    if not separate:
                        parent=Task(student_profile_id=g.current_user.profile.id,**fields)
                        db.session.add(parent);db.session.flush()
                    for step in steps:
                        child_fields={**fields,'title':step['title'],'estimated_minutes':step['minutes'],'planned_start_at':None}
                        db.session.add(Task(student_profile_id=g.current_user.profile.id,
                            parent_task_id=None if separate else parent.id,**child_fields))
                draft.steps=[]
                db.session.commit()
                flash(f'Saved {preview_count} tasks, including selected subtasks and repeat occurrences.','success')
                return redirect(url_for('tasks.tasks'))
    return render_template('ai_batch_review.html',rows=rows,selected=selected,step_selected=step_selected,
        errors=errors,preview_count=preview_count,budget=metadata['options'].get('budget'))
