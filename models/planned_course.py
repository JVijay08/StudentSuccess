from datetime import datetime, timezone

from extensions import db


def get_current_time():
    return datetime.now(timezone.utc)


class PlannedCourse(db.Model):
    __tablename__ = "planned_courses"
    __table_args__ = (
        db.UniqueConstraint(
            "student_profile_id",
            "catalog_id",
            "course_id",
            "school_year",
            name="unique_student_course_year",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    student_profile_id = db.Column(
        db.Integer, db.ForeignKey("student_profiles.id"), nullable=False
    )
    catalog_id = db.Column(db.String(40), nullable=False, default="national")
    course_id = db.Column(db.String(100), nullable=False)
    school_year = db.Column(db.Integer, nullable=False)
    term = db.Column(db.String(30), nullable=False, default="Full year")
    status = db.Column(db.String(20), nullable=False, default="considering")
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=get_current_time
    )

    student_profile = db.relationship("StudentProfile", back_populates="planned_courses")
