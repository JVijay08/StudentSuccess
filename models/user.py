from extensions import db
from .student import get_current_time


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=get_current_time
    )

    # username is stored lowercase; enforce this at the model level
    def __init__(self, username: str, password_hash: str, **kwargs):
        super().__init__(username=username.lower(), password_hash=password_hash, **kwargs)

    profile = db.relationship(
        "StudentProfile",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
    settings = db.relationship(
        "UserSettings",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )

    access_credential = db.relationship(
        "AccessCredential", back_populates="user",
        cascade="all, delete-orphan", uselist=False,
    )

    def __repr__(self):
        return f"<User id {self.id} username {self.username!r}>"
