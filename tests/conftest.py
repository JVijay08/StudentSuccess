import pytest

from app import create_app
from extensions import db
from models import User
from services.auth_service import hash_password


@pytest.fixture()
def app(tmp_path):
    """A Flask app bound to an isolated per-test SQLite database.

    Never touches the real ``instance/studentsuccess.db`` — each test gets a
    fresh file under pytest's ``tmp_path``.
    """
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": (
                f"sqlite:///{tmp_path / 'test.db'}"
            ),
        }
    )

    with app.app_context():
        db.create_all()

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()


# Credentials for the fixture-registered test user.
TEST_USERNAME = "tester"
TEST_PASSWORD = "password123"


@pytest.fixture()
def authed_client(app):
    """An existing password account, retained for backward-compatibility tests."""
    client = app.test_client()
    with app.app_context():
        user = User(username=TEST_USERNAME, password_hash=hash_password(TEST_PASSWORD))
        db.session.add(user)
        db.session.commit()
    response = client.post(
        "/login",
        data={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )
    # Existing password accounts can still sign in.
    assert response.status_code == 302

    with app.app_context():
        user = User.query.filter_by(username=TEST_USERNAME).first()
        assert user is not None
        client.user_id = user.id

    return client
