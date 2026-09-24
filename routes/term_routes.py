import math
from flask import Blueprint, g, request, render_template, redirect, url_for, flash, abort
from extensions import db
from models.term_course import TermCourse
from services.auth_service import login_required
from services.privacy_service import confirmation_errors
from services.college_directory import institution, valid_catalog_url
from services.settings_service import get_or_create_settings


def course_values(form):
    errors = confirmation_errors(form)
    values = {key: form.get(key, '').strip() for key in
              ('title', 'term', 'course_code', 'description', 'catalog_url')}
    for key, limit in [('title', 120), ('term', 60), ('course_code', 32), ('description', 1000)]:
        if len(values[key]) > limit or (key in {'title', 'term'} and not values[key]):
            errors.append(f"Enter {key.replace('_', ' ')} (up to {limit} characters).")
    for key, maximum, optional in [('weekly_hours', 168, False), ('credits', 60, True)]:
        raw = form.get(key, '').strip()
        try:
            value = None if optional and not raw else float(raw or '0')
            if value is not None and (not math.isfinite(value) or not 0 <= value <= maximum):
                raise ValueError
            values[key] = value
        except ValueError:
            errors.append(f"Enter {key.replace('_', ' ')} between 0 and {maximum}.")
    values['institution_id'] = form.get('institution_id', '').strip() or None
    if values['institution_id'] and not institution(values['institution_id']):
        errors.append('Choose a college from the directory or leave it unselected.')
    values['enrollment_type'] = form.get('enrollment_type', 'college')
    if values['enrollment_type'] not in {'college', 'dual'}:
        errors.append('Choose college or dual enrollment.')
    values['status'] = form.get('status', 'planned')
    if values['status'] not in {'considering', 'planned', 'completed'}:
        errors.append('Choose considering, planned, or completed.')
    values['school_year'] = None
    if values['enrollment_type'] == 'dual':
        try:
            values['school_year'] = int(form.get('school_year', ''))
            if values['school_year'] not in {9, 10, 11, 12}:
                raise ValueError
        except ValueError:
            errors.append('Choose a high-school grade from 9 through 12 for dual enrollment.')
    if values['catalog_url'] and not valid_catalog_url(values['catalog_url']):
        errors.append('Use a complete http:// or https:// public course catalog link (up to 500 characters).')
    return values, errors


def render_plan(errors=None, editing=None):
    courses = TermCourse.query.filter_by(user_id=g.current_user.id).order_by(TermCourse.term, TermCourse.title, TermCourse.id).all()
    preferences = get_or_create_settings(g.current_user)
    selected = institution(preferences.institution_id)
    ids = {course.institution_id for course in courses if course.institution_id}
    if selected:
        ids.add(selected['id'])
    choices = sorted((institution(i) for i in ids if institution(i)), key=lambda row: row['name'])
    if request.method == 'POST':
        values = request.form
    elif editing:
        values = {key: getattr(editing, key) for key in ('title', 'term', 'weekly_hours', 'institution_id',
            'enrollment_type', 'school_year', 'status', 'course_code', 'credits', 'description', 'catalog_url')}
    else:
        values = dict(institution_id=preferences.institution_id, weekly_hours=3, status='considering',
            enrollment_type='dual' if preferences.academic_context == 'high_school' else 'college')
    return render_template('term_plan.html', courses=courses, errors=errors or [], editing=editing,
        values=values, college_choices=choices, selected_college=selected)

term_bp = Blueprint("terms", __name__)


@term_bp.route("/terms", methods=["GET", "POST"])
@login_required
def plan():
    errors = []
    if request.method == "POST":
        values, errors = course_values(request.form)
        if not errors:
            db.session.add(TermCourse(user_id=g.current_user.id, **values))
            db.session.commit()
            return redirect(url_for("terms.plan"))
    return render_plan(errors)


@term_bp.route('/terms/<int:course_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(course_id):
    course = db.get_or_404(TermCourse, course_id)
    if course.user_id != g.current_user.id:
        abort(404)
    errors = []
    if request.method == 'POST':
        values, errors = course_values(request.form)
        if not errors:
            for key, value in values.items():
                setattr(course, key, value)
            db.session.commit()
            flash('Course updated. Existing assignments keep their current subject name.', 'success')
            return redirect(url_for('terms.plan'))
    return render_plan(errors, editing=course)


@term_bp.post("/terms/<int:course_id>/delete")
@login_required
def delete(course_id):
    course = db.get_or_404(TermCourse, course_id)
    if course.user_id != g.current_user.id:
        abort(404)
    db.session.delete(course)
    db.session.commit()
    flash("Course removed from this term.", "success")
    return redirect(url_for("terms.plan"))
