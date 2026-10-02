from extensions import db


class AIQuota(db.Model):
    __tablename__ = 'ai_quotas'
    key = db.Column(db.String(100), primary_key=True)
    used = db.Column(db.Integer, nullable=False, default=0)


class AIDraft(db.Model):
    __tablename__ = 'ai_drafts'
    id = db.Column(db.String(64), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    task_id = db.Column(db.Integer, nullable=False)
    snapshot = db.Column(db.Text, nullable=False)
    steps = db.Column(db.JSON, nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    consumed = db.Column(db.Boolean, nullable=False, default=False)
    user = db.relationship('User', backref=db.backref('ai_drafts', cascade='all, delete-orphan'))
