import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "instance" / "studentsuccess.db"


class config:
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE_PATH.as_posix()}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get("SECRET_KEY") or (
        "dev-only-secret"
        if os.environ.get("APP_ENV", "development") != "production"
        else None
    )
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
