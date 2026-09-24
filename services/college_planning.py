"""Shared course-entry context and college-only term summaries."""
from flask import g, request
from models import TermCourse
from services import college_directory
from services.settings_service import get_or_create_settings

REQUIREMENT_AREAS = {'unspecified':'Not classified', 'major':'Major / program',
    'general':'General education', 'elective':'Elective', 'prerequisite':'Prerequisite / preparation'}


def entry_context(editing=None):
    preferences=get_or_create_settings(g.current_user)
    courses=TermCourse.query.filter_by(user_id=g.current_user.id).order_by(TermCourse.term,TermCourse.title,TermCourse.id).all()
    selected=college_directory.institution(preferences.institution_id)
    ids={c.institution_id for c in courses if c.institution_id}
    submitted_id=request.form.get('institution_id')
    if college_directory.institution(submitted_id): ids.add(submitted_id)
    if selected: ids.add(selected['id'])
    query=request.args.get('college_q','').strip()[:120]
    state=request.args.get('college_state','').upper()
    if state not in college_directory.states(): state=''
    matches=college_directory.search(query,state) if query or state else []
    choices={i:college_directory.institution(i) for i in ids if college_directory.institution(i)}
    choices.update({c['id']:c for c in matches[:40]})
    if request.method=='POST' and request.endpoint in {'terms.plan','terms.edit'}:
        values=request.form
    elif editing:
        values={key:getattr(editing,key) for key in ('title','term','weekly_hours','institution_id',
            'enrollment_type','school_year','status','course_code','credits','description','catalog_url','requirement_area')}
    else:
        values=dict(institution_id=preferences.institution_id,weekly_hours=3,status='considering',
            school_year=g.current_user.profile.grade if g.current_user.profile else 9,
            term=preferences.college_term if preferences.academic_context=='college' else '',
            enrollment_type='dual' if preferences.academic_context=='high_school' else 'college')
    return dict(term_courses=courses,values=values,editing=editing,selected_college=selected,
        college_choices=sorted(choices.values(),key=lambda r:r['name']),college_query=query,college_state=state,
        college_matches=len(matches),college_states=college_directory.states(),college_state_names=college_directory.STATE_NAMES,
        requirement_areas=REQUIREMENT_AREAS)


def term_summary(user):
    preferences=get_or_create_settings(user)
    courses=TermCourse.query.filter_by(user_id=user.id).all()
    terms=sorted({c.term for c in courses})
    term=preferences.college_term or (terms[0] if len(terms)==1 else '')
    planned=[c for c in courses if c.term==term and c.status=='planned']
    return dict(term=term,terms=terms,course_count=len(planned),
        credits=sum(c.credits or 0 for c in planned),unknown_credits=sum(c.credits is None for c in planned),
        weekly_hours=sum(c.weekly_hours for c in planned),goal=preferences.term_credit_goal,
        program=preferences.college_program)
