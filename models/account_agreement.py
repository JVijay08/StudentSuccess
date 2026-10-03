from datetime import datetime, timezone
from extensions import db


class AccountAgreement(db.Model):
    """Minimal record of the signup acknowledgment; no birth date or IP address."""
    __tablename__ = 'account_agreements'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    version = db.Column(db.String(20), nullable=False)
    accepted_at = db.Column(db.DateTime(timezone=True), nullable=False,
                            default=lambda: datetime.now(timezone.utc))
    user = db.relationship('User', backref=db.backref('agreements', cascade='all, delete-orphan'))
