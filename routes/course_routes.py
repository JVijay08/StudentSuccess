from collections import defaultdict

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from extensions import db
from models import PlannedCourse, StudentProfile
from services import course_service
from services.auth_service import login_required


course_bp = Blueprint("courses", __name__)


def _profile_or_redirect():
    profile = StudentProfile.query.filter_by(user_id=g.current_user.id).first()
    if profile is None:
        return None, redirect(url_for("profile.onboarding"))
    return profile, None


def _planned_ids(profile):
    return {planned.course_id for planned in profile.planned_courses}


def _planned_course_rows(profile):
    catalog = {
        course["course_id"]: course for course in course_service.load_courses()
    }
    rows = []
    for planned in sorted(
        profile.planned_courses,
        key=lambda item: (item.school_year, item.term, item.course_id),
    ):
        course = catalog.get(planned.course_id)
        if course is not None:
            rows.append({"planned": planned, "course": course})
    return rows


def _prerequisite_status(course, planned_rows):
    completed_names = {
        row["course"]["course_name"].lower()
        for row in planned_rows
        if row["planned"].status == "completed"
    }
    missing = [
        prerequisite
        for prerequisite in course.get("prerequisites", [])
        if prerequisite.lower() not in completed_names
    ]
    return {"missing": missing, "has_prerequisites": bool(course.get("prerequisites"))}


@course_bp.get("/courses")
@login_required
def course_explorer():
    profile, redirect_response = _profile_or_redirect()
    if redirect_response:
        return redirect_response

    filters = {
        "query": request.args.get("q", "").strip() or None,
        "grade_level": request.args.get("grade", type=int),
        "subject": request.args.get("subject") or None,
        "course_type": request.args.get("course_type") or None,
        "rigor_level": request.args.get("rigor") or None,
        "workload_level": request.args.get("workload") or None,
        "career_cluster": request.args.get("career") or None,
    }
    courses = course_service.filter_courses(**filters)
    return render_template(
        "courses.html",
        profile=profile,
        courses=courses,
        filters=request.args,
        options=course_service.get_catalog_options(),
        planned_ids=_planned_ids(profile),
    )


@course_bp.get("/courses/<course_id>")
@login_required
def course_detail(course_id):
    profile, redirect_response = _profile_or_redirect()
    if redirect_response:
        return redirect_response

    course = course_service.get_course_by_id(course_id)
    if course is None:
        abort(404)

    planned_rows = _planned_course_rows(profile)
    return render_template(
        "course_detail.html",
        profile=profile,
        course=course,
        planned_ids=_planned_ids(profile),
        prerequisite_status=_prerequisite_status(course, planned_rows),
    )


@course_bp.post("/courses/plan/add/<course_id>")
@login_required
def add_to_plan(course_id):
    profile, redirect_response = _profile_or_redirect()
    if redirect_response:
        return redirect_response

    course = course_service.get_course_by_id(course_id)
    if course is None:
        abort(404)

    school_year = request.form.get("school_year", type=int)
    if school_year not in {9, 10, 11, 12}:
        flash("Choose a grade year from 9th through 12th.", "error")
        return redirect(request.referrer or url_for("courses.course_explorer"))

    term = request.form.get("term", "Full year").strip() or "Full year"
    status = request.form.get("status", "considering").strip().lower()
    if status not in {"considering", "planned", "completed"}:
        status = "considering"

    existing = PlannedCourse.query.filter_by(
        student_profile_id=profile.id,
        course_id=course_id,
        school_year=school_year,
    ).first()
    if existing is None:
        db.session.add(
            PlannedCourse(
                student_profile_id=profile.id,
                course_id=course_id,
                school_year=school_year,
                term=term,
                status=status,
            )
        )
        db.session.commit()
        flash(f"{course['course_name']} added to your plan.", "success")
    else:
        flash("That course is already planned for that grade year.", "warning")

    return redirect(request.referrer or url_for("courses.course_plan"))


@course_bp.post("/courses/plan/<int:planned_course_id>/delete")
@login_required
def remove_from_plan(planned_course_id):
    profile, redirect_response = _profile_or_redirect()
    if redirect_response:
        return redirect_response

    planned = db.get_or_404(PlannedCourse, planned_course_id)
    if planned.student_profile_id != profile.id:
        abort(404)

    db.session.delete(planned)
    db.session.commit()
    flash("Course removed from your plan.", "success")
    return redirect(url_for("courses.course_plan"))


@course_bp.get("/courses/plan")
@login_required
def course_plan():
    profile, redirect_response = _profile_or_redirect()
    if redirect_response:
        return redirect_response

    rows = _planned_course_rows(profile)
    by_year = defaultdict(list)
    for row in rows:
        by_year[row["planned"].school_year].append(row)

    workload_points = {"Low": 1, "Medium": 2, "High": 3}
    year_summaries = []
    for school_year in range(9, 13):
        year_rows = by_year.get(school_year, [])
        points = sum(
            workload_points.get(row["course"]["workload_level"], 0)
            for row in year_rows
        )
        year_summaries.append(
            {
                "school_year": school_year,
                "rows": year_rows,
                "workload_points": points,
                "workload_label": (
                    "Heavy" if points >= 8 else "Moderate" if points >= 4 else "Light"
                ),
            }
        )

    return render_template(
        "course_plan.html",
        profile=profile,
        year_summaries=year_summaries,
        planned_rows=rows,
    )


@course_bp.get("/courses/compare")
@login_required
def course_compare():
    profile, redirect_response = _profile_or_redirect()
    if redirect_response:
        return redirect_response

    course_ids = request.args.getlist("id")
    if len(course_ids) == 1 and "," in course_ids[0]:
        course_ids = course_ids[0].split(",")
    courses = [
        course_service.get_course_by_id(course_id)
        for course_id in course_ids[:3]
    ]
    courses = [course for course in courses if course is not None]
    return render_template("course_compare.html", profile=profile, courses=courses)
