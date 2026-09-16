from extensions import db


class AccessCredential(db.Model):
    """Only the digest of a high-entropy bearer code is persisted."""

    __tablename__ = "access_credentials"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    digest = db.Column(db.String(64), unique=True, nullable=False)
    version = db.Column(db.Integer, nullable=False, default=1)
    user = db.relationship("User", back_populates="access_credential")
