from extensions import db
from models import UserSettings


def get_or_create_settings(user):
    if user.settings is None:
        user.settings = UserSettings()
        db.session.add(user.settings)
        db.session.commit()
    return user.settings


def default_settings():
    """Unsaved defaults for signed-out pages."""
    return UserSettings(
        theme="light",
        text_scale=100,
        comfortable_spacing=False,
        reduce_motion=False,
        font_choice="system",
        card_density="comfortable",
        session_timeout_minutes=30,
    )
