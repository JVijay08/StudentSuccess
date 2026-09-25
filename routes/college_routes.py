from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for
from extensions import db
from services.auth_service import login_required
from services import college_directory
from services.settings_service import get_or_create_settings

college_bp = Blueprint('colleges', __name__)


@college_bp.get('/colleges/search')
@login_required
def search():
    query=request.args.get('q','').strip()[:120]
    state=request.args.get('state','').upper()
    if state and state not in college_directory.states():
        return {'results':[], 'total':0}
    matches=college_directory.search(query,state)
    return {'results':[{'id':r['id'],'name':r['name'],'state':r['state'],'city':r['city']} for r in matches[:40]],'total':len(matches)}


@college_bp.get('/colleges')
@login_required
def browse():
    query = request.args.get('q', '').strip()[:120]
    state = request.args.get('state', '').upper()
    if state not in college_directory.states():
        state = ''
    rows = college_directory.search(query, state)
    pages = max(1, (len(rows) + 24) // 25)
    page = min(pages, max(1, request.args.get('page', 1, type=int)))
    settings = get_or_create_settings(g.current_user)
    return render_template('colleges.html', colleges=rows[(page-1)*25:page*25],
        total=len(rows), page=page, pages=pages, query=query, state=state,
        states=college_directory.states(), state_names=college_directory.STATE_NAMES, directory=college_directory.directory(),
        selected=college_directory.institution(settings.institution_id))


@college_bp.post('/colleges/select')
@login_required
def select():
    identifier = request.form.get('institution_id', '')
    if identifier and not college_directory.institution(identifier):
        abort(400)
    get_or_create_settings(g.current_user).institution_id = identifier or None
    db.session.commit()
    flash('Default college updated. Existing courses keep their college.' if identifier else 'College preference cleared. Existing courses keep their college.', 'success')
    return redirect(url_for('terms.plan', _anchor='term-form'))
