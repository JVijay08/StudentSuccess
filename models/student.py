from datetime import datetime, timezone

from extensions import db


def get_current_time():
    return datetime.now(timezone.utc)


class StudentProfile(db.Model):
    __tablename__ = "student_profiles"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    grade = db.Column(db.Integer, nullable=False)
    graduation_year = db.Column(db.Integer, nullable=False)
    current_gpa = db.Column(db.Float, nullable=False)
    target_gpa = db.Column(db.Float, nullable=False)
    study_hours_per_week = db.Column(db.Float, nullable=False)
    career_goals = db.Column(db.String(120), nullable=True)
    course_rigor = db.Column(db.String(60), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=get_current_time
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=get_current_time,
        onupdate=get_current_time,
    )
    tasks = db.relationship(
        "Task",
        back_populates="student_profile",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<StudentProfile id {self.id} first_name {self.first_name}>"
