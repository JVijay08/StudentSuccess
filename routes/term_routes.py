import math
from flask import Blueprint, g, request, render_template, redirect, url_for, flash, abort
from extensions import db
from models.term_course import TermCourse
from services.auth_service import login_required
from services.privacy_service import confirmation_errors

term_bp = Blueprint("terms", __name__)


@term_bp.route("/terms", methods=["GET", "POST"])
@login_required
def plan():
    errors = []
    if request.method == "POST":
        errors = confirmation_errors(request.form)
        title = request.form.get("title", "").strip()
        term = request.form.get("term", "").strip()
        try:
            hours = float(request.form.get("weekly_hours", "0"))
            if not math.isfinite(hours) or not 0 <= hours <= 168:
                raise ValueError
        except ValueError:
            hours = 0
            errors.append("Enter weekly hours between 0 and 168.")
        if not title or len(title) > 120 or not term or len(term) > 60:
            errors.append("Enter a course (up to 120 characters) and term (up to 60).")
        if not errors:
            db.session.add(TermCourse(user_id=g.current_user.id, title=title, term=term, weekly_hours=hours))
            db.session.commit()
            return redirect(url_for("terms.plan"))
    courses = TermCourse.query.filter_by(user_id=g.current_user.id).order_by(TermCourse.term, TermCourse.title, TermCourse.id).all()
    return render_template("term_plan.html", courses=courses, errors=errors)


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
