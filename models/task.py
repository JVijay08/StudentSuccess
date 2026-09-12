from extensions import db
from .student import get_current_time


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    student_profile_id = db.Column(
        db.Integer,
        db.ForeignKey("student_profiles.id"),
        nullable=False,
        index=True,
    )
    title = db.Column(db.String(160), nullable=False)
    subject = db.Column(db.String(80), nullable=True)
    task_type = db.Column(db.String(40), nullable=True)
    due_at = db.Column(db.DateTime(timezone=True), nullable=False)
    estimated_minutes = db.Column(db.Integer, nullable=False)
    difficulty = db.Column(db.String(20), nullable=False, default="medium")
    interest_level = db.Column(db.String(20), nullable=False, default="medium")
    status = db.Column(db.String(20), nullable=False, default="not_started")
    planned_start_at = db.Column(db.DateTime(timezone=True), nullable=True)
    started_at = db.Column(db.DateTime(timezone=True), nullable=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    recurrence_rule = db.Column(db.String(20), nullable=True)
    prep_for_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=get_current_time
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=get_current_time,
        onupdate=get_current_time,
    )

    student_profile = db.relationship(
        "StudentProfile",
        back_populates="tasks",
    )

    def __repr__(self):
        return f"<Task id {self.id} title {self.title!r}>"
