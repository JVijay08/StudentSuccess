from extensions import db


class TermCourse(db.Model):
    __tablename__ = "term_courses"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(120), nullable=False)
    term = db.Column(db.String(60), nullable=False)
    weekly_hours = db.Column(db.Float, nullable=False, default=0)
    institution_id = db.Column(db.String(12), nullable=True)
    enrollment_type = db.Column(db.String(20), nullable=False, default='college')
    school_year = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='planned')
    course_code = db.Column(db.String(32), nullable=False, default='')
    credits = db.Column(db.Float, nullable=True)
    description = db.Column(db.Text, nullable=False, default='')
    catalog_url = db.Column(db.String(500), nullable=False, default='')
    requirement_area = db.Column(db.String(20), nullable=False, default='unspecified')
    user = db.relationship("User", backref=db.backref("term_courses", cascade="all, delete-orphan"))
