from flask import Blueprint, redirect, render_template, request, url_for

from extensions import db
from models import StudentProfile


profile_bp = Blueprint("profile", __name__)


@profile_bp.route("/onboarding", methods=["GET", "POST"])
def onboarding():
    errors = []

    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        grade_level_text = request.form.get("grade_level", "").strip()
        graduation_year_text = request.form.get("graduation_year", "").strip()
        current_gpa_text = request.form.get("current_gpa", "").strip()
        target_gpa_text = request.form.get("target_gpa", "").strip()
        study_hours_text = request.form.get(
            "study_hours_per_week",
            "",
        ).strip()
        career_interest = request.form.get("career_interest", "").strip()
        course_rigor_preference = request.form.get(
            "course_rigor_preference",
            "",
        ).strip()

        if not first_name:
            errors.append("First name is required.")

        if len(first_name) > 80:
            errors.append("First name must be 80 characters or fewer.")

        try:
            grade_level = int(grade_level_text)

            if grade_level not in [9, 10, 11, 12]:
                errors.append("Grade level must be between 9 and 12.")
        except ValueError:
            grade_level = None
            errors.append("Please select a valid grade level.")

        try:
            graduation_year = int(graduation_year_text)

            if graduation_year < 2026 or graduation_year > 2035:
                errors.append(
                    "Graduation year must be between 2026 and 2035."
                )
        except ValueError:
            graduation_year = None
            errors.append("Please enter a valid graduation year.")

        try:
            current_gpa = float(current_gpa_text)

            if current_gpa < 0 or current_gpa > 5:
                errors.append("Current GPA must be between 0 and 5.")
        except ValueError:
            current_gpa = None
            errors.append("Please enter a valid current GPA.")

        try:
            target_gpa = float(target_gpa_text)

            if target_gpa < 0 or target_gpa > 5:
                errors.append("Target GPA must be between 0 and 5.")
        except ValueError:
            target_gpa = None
            errors.append("Please enter a valid target GPA.")

        try:
            study_hours_per_week = float(study_hours_text)

            if study_hours_per_week < 0 or study_hours_per_week > 80:
                errors.append(
                    "Study hours must be between 0 and 80 per week."
                )
        except ValueError:
            study_hours_per_week = None
            errors.append("Please enter valid weekly study hours.")

        if len(career_interest) > 120:
            errors.append(
                "Career interest must be 120 characters or fewer."
            )

        valid_rigor_options = [
            "",
            "Balanced",
            "Challenging",
            "Highly Challenging",
        ]

        if course_rigor_preference not in valid_rigor_options:
            errors.append("Please select a valid course rigor preference.")

        if errors:
            return render_template(
                "onboarding.html",
                errors=errors,
                form_data=request.form,
            )

        profile = StudentProfile.query.first()

        if profile is None:
            profile = StudentProfile()
            db.session.add(profile)

        profile.first_name = first_name
        profile.grade = grade_level
        profile.graduation_year = graduation_year
        profile.current_gpa = current_gpa
        profile.target_gpa = target_gpa
        profile.study_hours_per_week = study_hours_per_week
        profile.career_goals = career_interest or None
        profile.course_rigor = course_rigor_preference or None

        db.session.commit()

        return redirect(url_for("main.dashboard"))

    existing_profile = StudentProfile.query.first()

    if existing_profile is not None:
        form_data = {
            "first_name": existing_profile.first_name,
            "grade_level": str(existing_profile.grade),
            "graduation_year": str(existing_profile.graduation_year),
            "current_gpa": str(existing_profile.current_gpa),
            "target_gpa": str(existing_profile.target_gpa),
            "study_hours_per_week": str(
                existing_profile.study_hours_per_week
            ),
            "career_interest": existing_profile.career_goals or "",
            "course_rigor_preference": (
                existing_profile.course_rigor or ""
            ),
        }
    else:
        form_data = {}

    return render_template(
        "onboarding.html",
        errors=[],
        form_data=form_data,
    )