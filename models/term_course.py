from extensions import db


class TermCourse(db.Model):
    __tablename__ = "term_courses"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(120), nullable=False)
    term = db.Column(db.String(60), nullable=False)
    weekly_hours = db.Column(db.Float, nullable=False, default=0)
    user = db.relationship("User", backref=db.backref("term_courses", cascade="all, delete-orphan"))
