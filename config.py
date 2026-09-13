import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "instance" / "studentsuccess.db"


def normalize_database_url(database_url):
    if not database_url:
        return database_url

    for prefix in ("postgres://", "postgresql://"):
        if database_url.startswith(prefix):
            return database_url.replace(prefix, "postgresql+psycopg://", 1)

    return database_url


DATABASE_URL = normalize_database_url(os.environ.get("DATABASE_URL"))


class config:
    SQLALCHEMY_DATABASE_URI = DATABASE_URL or f"sqlite:///{DATABASE_PATH.as_posix()}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_REFRESH_EACH_REQUEST = True
    SECRET_KEY = os.environ.get("SECRET_KEY") or (
        "dev-only-secret"
        if os.environ.get("APP_ENV", "development") != "production"
        else None
    )
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
