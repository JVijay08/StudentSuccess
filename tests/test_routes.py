import pytest

from flask import Flask

from extensions import db
from models import StudentProfile
from routes.main_routes import main_bp
from routes.profile_routes import profile_bp


@pytest.fixture()
def app(tmp_path):
    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{tmp_path / 'test.db'}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    db.init_app(app)
    app.register_blueprint(main_bp)
    app.register_blueprint(profile_bp)

    with app.app_context():
        db.create_all()

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()


def test_onboarding_saves_grade_and_rigor(app):
    client = app.test_client()

    response = client.post(
        "/onboarding",
        data={
            "first_name": "Jayesh",
            "grade_level": "11",
            "graduation_year": "2027",
            "current_gpa": "4.16",
            "target_gpa": "5.0",
            "study_hours_per_week": "42",
            "career_interest": "Engineering",
            "course_rigor_preference": "Challenging",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302

    with app.app_context():
        profile = StudentProfile.query.first()

    assert profile is not None
    assert profile.grade == 11
    assert profile.career_goals == "Engineering"
    assert profile.course_rigor == "Challenging"
