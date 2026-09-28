from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, url_for
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from extensions import db
from models import Task
from services.auth_service import login_required
from services.access_service import verify_csrf

task_bulk_bp = Blueprint('task_bulk', __name__)


def owned_tasks():
    return Task.query.join(Task.student_profile).filter_by(user_id=g.current_user.id).order_by(Task.due_at, Task.id).all()


def expand_selection(selected, tasks):
    """Include descendants and unfinished prep, and show the full set before deletion."""
    result=set(selected)
    while True:
        added={task.id for task in tasks if task.parent_task_id in result or (task.prep_for_id in result and task.status!='completed')}
        if added.issubset(result):
            return result
        result.update(added)


def signer():
    return URLSafeTimedSerializer(current_app.secret_key, salt='task-bulk-delete-v1')


@task_bulk_bp.route('/tasks/select', methods=['GET','POST'])
@login_required
def select():
    tasks=owned_tasks()
    if request.method=='GET':
        return render_template('task_select.html',tasks=tasks)
    verify_csrf()
    try:
        selected={int(value) for value in request.form.getlist('task_ids')}
    except ValueError:
        abort(400)
    if not selected:
        flash('Select at least one task first.', 'warning')
        return redirect(url_for('task_bulk.select'))
    if not selected.issubset({task.id for task in tasks}):
        abort(404)
    expanded=expand_selection(selected,tasks)
    token=signer().dumps({'user':g.current_user.id,'ids':sorted(expanded)})
    return render_template('task_delete_review.html', tasks=[task for task in tasks if task.id in expanded],
        added=len(expanded-selected), token=token)


@task_bulk_bp.post('/tasks/delete-selected')
@login_required
def delete_selected():
    verify_csrf()
    try:
        payload=signer().loads(request.form.get('selection_token',''), max_age=600)
    except (BadSignature, SignatureExpired):
        flash('The deletion review expired. Select your tasks and review them again.', 'warning')
        return redirect(url_for('task_bulk.select'))
    if payload.get('user')!=g.current_user.id:
        abort(404)
    selected=set(payload['ids'])
    tasks=owned_tasks()
    by_id={task.id:task for task in tasks}
    if not selected or not selected.issubset(by_id) or expand_selection(selected,tasks)!=selected:
        flash('These tasks changed since your review. Review the selection again before deleting.', 'warning')
        return redirect(url_for('task_bulk.select'))
    parents={task.parent_task_id for task in tasks if task.id in selected and task.parent_task_id not in selected}
    # Preserve completed prep history without leaving a reference to a deleted task.
    for task in tasks:
        if task.id not in selected and task.prep_for_id in selected:
            task.prep_for_id=None
    for identifier in selected:
        task=by_id[identifier]
        if task.parent_task_id in parents and task.parent:
            task.parent.children.remove(task)
        db.session.delete(task)
    db.session.flush()
    from routes.task_routes import _sync_parent
    for identifier in parents:
        parent=by_id.get(identifier)
        if parent:
            db.session.expire(parent,['children'])
            if parent.children:
                _sync_parent(parent.children[0])
    db.session.commit()
    flash(f'Deleted {len(selected)} tasks.', 'success')
    return redirect(url_for('tasks.tasks',_anchor='task-queue'))
