from extensions import db


class AccountRequest(db.Model):
    """Short-lived, single-use email actions. Raw tokens are never stored."""
    __tablename__ = 'account_requests'
    id = db.Column(db.Integer, primary_key=True)
    digest = db.Column(db.String(64), unique=True, nullable=False)
    purpose = db.Column(db.String(16), nullable=False)
    email = db.Column(db.String(254), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    auth_version = db.Column(db.Integer, nullable=False, default=0)
    password_hash = db.Column(db.String(256), nullable=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)


class AuthAttempt(db.Model):
    __tablename__ = 'auth_attempts'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
