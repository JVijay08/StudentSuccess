import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "instance" / "studentsuccess.db"
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)


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
