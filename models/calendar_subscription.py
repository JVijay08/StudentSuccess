from extensions import db


class CalendarSubscription(db.Model):
    __tablename__ = 'calendar_subscriptions'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    token_hash = db.Column(db.String(64), nullable=False, unique=True)
    auth_version = db.Column(db.Integer, nullable=False)
