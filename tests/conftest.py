import pytest

from app import create_app
from extensions import db
from models import User


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
    """A test client already authenticated as a freshly registered user.

    Registration (``POST /register``) both creates the user and logs them in
    by setting the session; because the test client persists the session
    cookie, the returned client is authenticated for subsequent requests.

    The registered user's id is exposed via ``client.user_id`` so tests can
    scope profiles/tasks to that user when they set up data directly.
    """
    client = app.test_client()

    response = client.post(
        "/register",
        data={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )
    # Registration succeeds and redirects to onboarding.
    assert response.status_code == 302

    with app.app_context():
        user = User.query.filter_by(username=TEST_USERNAME).first()
        assert user is not None
        client.user_id = user.id

    return client
