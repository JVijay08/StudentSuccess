import math
from flask import Blueprint, g, request, render_template, redirect, url_for, flash, abort
from extensions import db
from models.term_course import TermCourse
from services.auth_service import login_required
from services.privacy_service import confirmation_errors
from services.college_directory import institution, valid_catalog_url
from services.settings_service import get_or_create_settings
from services.college_planning import entry_context, term_summary, REQUIREMENT_AREAS


def course_values(form):
    errors = confirmation_errors(form)
    values = {key: form.get(key, '').strip() for key in
              ('title', 'term', 'course_code', 'description', 'catalog_url')}
    if any(ord(c) < 32 and c not in '\n\t' for value in values.values() for c in value):
        errors.append('Course details contain unsupported control characters.')
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
    values['requirement_area'] = form.get('requirement_area','unspecified')
    if values['requirement_area'] not in REQUIREMENT_AREAS:
        errors.append('Choose a valid course requirement category.')
    if values['status'] not in {'considering', 'planned', 'in_progress', 'completed'}:
        errors.append('Choose considering, planned, in progress, or completed.')
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
    if get_or_create_settings(g.current_user).academic_context == 'high_school':
        from routes.course_routes import course_explorer
        return course_explorer(course_errors=errors, editing=editing)
    context=entry_context(editing)
    return render_template('term_plan.html', courses=context['term_courses'], errors=errors or [],
        college_summary=term_summary(g.current_user), **context)


def plan_destination():
    if get_or_create_settings(g.current_user).academic_context == 'high_school':
        return url_for('courses.course_explorer', course_source='dual', _anchor='college-entry')
    return url_for('terms.plan')

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
            return redirect(plan_destination())
    elif get_or_create_settings(g.current_user).academic_context == 'high_school':
        return redirect(plan_destination())
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
            return redirect(plan_destination())
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
    return redirect(plan_destination())
