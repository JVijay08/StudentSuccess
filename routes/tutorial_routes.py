"""A guided tour in disposable data, never in a student's own planner."""
from flask import Blueprint, abort, g, redirect, render_template, request, session, url_for
from extensions import db
from models import User, Task
from services.auth_service import login_required
from services.access_service import verify_csrf
from services.settings_service import get_or_create_settings

tutorial_bp = Blueprint('tutorial', __name__)

# Instructions describe real controls; advancing never pretends an exercise was done.
STEPS = [
    ('Welcome to your practice planner', 'Today gives you one clear place to start. This is a separate sample account: experiment freely. Use Show me to find a control, then try it. Next section is always available if you prefer to skip an exercise.', 'main.dashboard', '.focus-card'),
    ('Start your first task', 'Choose Start this task on the recommended assignment. Its status changes to In progress. The recommendation explains where to begin; it is a planning suggestion, not a grade.', 'main.dashboard', '.start-next-task button'),
    ('Complete it and see what comes next', 'Choose Complete task when you are done. Recording minutes is optional in the three-dot menu. Today then brings your next assignment forward.', 'main.dashboard', '.complete-next-task button'),
    ('Build your task queue', 'Open Add a task. Try a title, deadline, and work estimate. Choose a saved course or your own subject. For repeats, choose a start date and Repeat through date: each occurrence uses the same due time, 11:59 PM by default.', 'tasks.tasks', '.task-entry>summary'),
    ('Reschedule from the task menu', 'Open the three dots on an unstarted task, then Reschedule. Change its planned start without changing its deadline. Editing the task lets you change the deadline too.', 'tasks.tasks', '.task-card .task-menu>summary'),
    ('Break a large assignment into steps', 'This assignment has its own detail page. Add a small subtask or split the estimate into work blocks. Steps have their own completion controls; optional breaks stay separate from working minutes.', 'tasks.task_detail', '[data-paper-detail]'),
    ('Find completed work and queue tools', 'Open Completed to revisit finished work or undo completion. Use Select tasks to review and delete several together. Explore sorting, filtering, and import/export below the queue. Today also has a Full dashboard view for progress and workload summaries.', 'tasks.tasks', '#completed-tasks>summary'),
    ('Choose high-school courses', 'Open Filter courses to choose a catalog and narrow results. Open course details, compare two or more courses, or add one to your plan. Catalog notes explain coverage and unverified information.', 'courses.course_explorer', '.filter-panel'),
    ('Add college courses alongside high school', 'Open Add a college course for dual enrollment. Search for a college, then enter its course and your high-school grade. Each course can belong to a different college. Credit transfer is not automatically verified.', 'courses.course_explorer', '#college-entry>summary'),
    ('See the four-year plan', 'Your saved courses are grouped by grade. Review the estimated workload, change plans, and open course assignments to create tasks and steps. College courses sit alongside the high-school plan.', 'courses.course_plan', '.plan-grid'),
    ('Try the college preset', 'We switched only this practice account to college planning. Terms replace school grades. Add courses from multiple colleges, track credits and requirements, and set a program or term goal in planning preferences.', 'terms.plan', '.college-context,.term-overview,.term-grid'),
    ('Make the planner comfortable', 'Try text size, contrast, Reduce motion, reminders, and your education preset. Save all settings applies your choices. Account tools also let you export or delete data. Real accounts use a username and password, without email.', 'settings.settings', '#workspace-settings'),
    ('Personalize how you study', 'Choose your study budget, academic goals, and planning preferences. New accounts complete this setup before using the planner; you can return here from Settings whenever your plans change.', 'profile.onboarding', '.onboarding-sheet'),
    ('Read your progress without judgment', 'The full dashboard brings together timing history, completed work, and course workload. Open the timing graphs to explore patterns. Early starts count as on time; they do not cancel out late starts. These summaries are planning tools, not grades.', 'main.dashboard', '.timing-panel'),
    ('Explore the college directory', 'Search by college name, city, or state. You can choose a default for new courses; existing courses keep their own college. Read the directory source notes and verify courses, admission, and transfer credit with the institution.', 'colleges.browse', '.college-search'),
    ('Put deadlines on Google Calendar', 'Use a task menu to add one deadline, or download active deadlines for a bulk import. Google lets you review and save the event. These are calendar copies: later task edits and completion are not synced.', 'settings.calendar_help', '#main-content .panel'),
    ('Follow updates and find your way back', 'Search the Updates page to see what changed. The top navigation returns to Today, Tasks, and your course plan. The gear menu contains settings and this tutorial. You can explore any page and return to the current section.', 'main.updates', '#update-query'),
    ('You are ready to plan', 'You have reached the end of the guide. Explore any section again or finish to delete this practice workspace. Your own account stays separate. Use real coursework, but leave out full names, student numbers, and other sensitive details.', 'main.dashboard', '.app-bar'),
]


def step_url(index):
    endpoint = STEPS[index][2]
    if index == 13:
        return url_for(endpoint, view='full')
    if endpoint == 'tasks.task_detail':
        task = db.session.get(Task, session.get('tutorial_task'))
        if task and task.student_profile.user_id == session.get('user_id'):
            return url_for(endpoint, task_id=task.id)
        return url_for('tasks.tasks')
    return url_for(endpoint)


@tutorial_bp.app_context_processor
def tutorial_context():
    if not session.get('tutorial_mode') or not session.get('demo_mode') or not getattr(g, 'current_user', None):
        return {'tutorial': None}
    index = min(max(session.get('tutorial_step', 0), 0), len(STEPS)-1)
    title, description, endpoint, target = STEPS[index]
    return {'tutorial': dict(index=index, title=title, description=description,
        target=target, url=step_url(index), steps=STEPS, total=len(STEPS))}


@tutorial_bp.post('/tutorial/start')
def start():
    verify_csrf()
    if session.get('user_id') and not session.get('demo_mode'):
        return login_required(_start)()
    return _start()


def _start():
    from routes.auth_routes import start_demo
    previous = session.get('tutorial_return')
    if session.get('user_id') and not session.get('demo_mode'):
        previous = {key: session[key] for key in ('user_id', 'auth_version', '_last_active', 'access_version') if key in session}
    if session.get('demo_mode'):
        old = db.session.get(User, session.get('user_id'))
        if old and old.username.startswith('demo-'):
            db.session.delete(old)
            db.session.commit()
    response = start_demo()
    session['tutorial_mode'] = True
    session['tutorial_step'] = 0
    if previous:
        session['tutorial_return'] = previous
    user = db.session.get(User, session['user_id'])
    settings = get_or_create_settings(user)
    settings.dashboard_mode = 'focus'
    db.session.commit()
    task = Task.query.filter_by(student_profile_id=user.profile.id, status='not_started').order_by(Task.id.desc()).first()
    session['tutorial_task'] = task.id
    return response


@tutorial_bp.post('/tutorial/step')
@login_required
def advance():
    verify_csrf()
    if not session.get('tutorial_mode') or not session.get('demo_mode'):
        abort(403)
    try:
        index = int(request.form.get('step', '0'))
    except ValueError:
        abort(400)
    if not 0 <= index < len(STEPS):
        abort(400)
    session['tutorial_step'] = index
    if 7 <= index <= 10:
        settings = get_or_create_settings(g.current_user)
        settings.academic_context = 'college' if index == 10 else 'high_school'
        db.session.commit()
    return redirect(step_url(index))


@tutorial_bp.post('/tutorial/finish')
@login_required
def finish():
    verify_csrf()
    if not session.get('tutorial_mode') or not session.get('demo_mode') or not g.current_user.username.startswith('demo-'):
        abort(403)
    previous = session.get('tutorial_return')
    db.session.delete(g.current_user)
    db.session.commit()
    session.clear()
    if previous:
        user = db.session.get(User, previous.get('user_id'))
        if user and user.auth_version == previous.get('auth_version', 0):
            session.update(previous)
            session.permanent = True
            # Normal authentication still checks inactivity and credential versions.
            return redirect(url_for('main.dashboard'))
    return redirect(url_for('tutorial.finished'))


@tutorial_bp.get('/tutorial/finished')
def finished():
    return render_template('tutorial_finished.html')
