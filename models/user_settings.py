from extensions import db
from .student import get_current_time


class UserSettings(db.Model):
    __tablename__ = "user_settings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False
    )
    theme = db.Column(db.String(20), nullable=False, default="system")
    text_scale = db.Column(db.Integer, nullable=False, default=100)
    comfortable_spacing = db.Column(db.Boolean, nullable=False, default=False)
    reduce_motion = db.Column(db.Boolean, nullable=False, default=False)
    font_choice = db.Column(db.String(20), nullable=False, default="system")
    dashboard_mode = db.Column(db.String(20), nullable=False, default="standard")
    hidden_dashboard_cards = db.Column(db.String(200), nullable=False, default="")
    card_density = db.Column(db.String(20), nullable=False, default="comfortable")
    default_task_minutes = db.Column(db.Integer, nullable=False, default=60)
    work_session_minutes = db.Column(db.Integer, nullable=False, default=25)
    start_buffer_days = db.Column(db.Integer, nullable=False, default=2)
    suggest_breakdown = db.Column(db.Boolean, nullable=False, default=True)
    recommendation_count = db.Column(db.Integer, nullable=False, default=3)
    recommendation_tone = db.Column(db.String(20), nullable=False, default="neutral")
    reminders_enabled = db.Column(db.Boolean, nullable=False, default=False)
    reminder_lead_hours = db.Column(db.Integer, nullable=False, default=24)
    quiet_start = db.Column(db.String(5), nullable=False, default="21:00")
    quiet_end = db.Column(db.String(5), nullable=False, default="07:00")
    snooze_minutes = db.Column(db.Integer, nullable=False, default=30)
    calendar_export_enabled = db.Column(db.Boolean, nullable=False, default=True)
    timezone_name = db.Column(
        db.String(60), nullable=False, default="America/New_York"
    )
    time_format = db.Column(db.String(10), nullable=False, default="12-hour")
    week_start = db.Column(db.String(10), nullable=False, default="Sunday")
    date_format = db.Column(db.String(15), nullable=False, default="month-first")
    relative_dates = db.Column(db.Boolean, nullable=False, default=True)
    session_timeout_minutes = db.Column(db.Integer, nullable=False, default=30)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=get_current_time
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=get_current_time,
        onupdate=get_current_time,
    )

    user = db.relationship("User", back_populates="settings")

    @property
    def hidden_cards(self):
        return {
            value for value in self.hidden_dashboard_cards.split(",") if value
        }
