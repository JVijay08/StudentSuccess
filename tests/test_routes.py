import pytest

from app import create_app
from extensions import db
from models import StudentProfile


@pytest.fixture()
def app(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": (
                f"sqlite:///{tmp_path / 'routes-test.db'}"
            ),
        }
    )

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()


def test_dashboard_and_onboarding_get_work(app):
    client = app.test_client()

    assert client.get("/dashboard").status_code == 200
    assert client.get("/onboarding").status_code == 200


def test_onboarding_saves_and_updates_profile(app):
    client = app.test_client()
    data = {
        "first_name": "Jayesh",
        "grade_level": "11",
        "graduation_year": "2027",
        "current_gpa": "4.16",
        "target_gpa": "5.0",
        "study_hours_per_week": "42",
        "career_interest": "Engineering",
        "course_rigor_preference": "Challenging",
    }

    response = client.post("/onboarding", data=data)
    assert response.status_code == 302

    data["first_name"] = "J"
    data["career_interest"] = "Computer Science"
    response = client.post("/onboarding", data=data)
    assert response.status_code == 302

    with app.app_context():
        profiles = StudentProfile.query.all()

    assert len(profiles) == 1
    assert profiles[0].first_name == "J"
    assert profiles[0].grade == 11
    assert profiles[0].career_goals == "Computer Science"
    assert profiles[0].course_rigor == "Challenging"


def test_onboarding_backend_limits_match_form(app):
    client = app.test_client()
    response = client.post(
        "/onboarding",
        data={
            "first_name": "Alex",
            "grade_level": "11",
            "graduation_year": "2036",
            "current_gpa": "3.5",
            "target_gpa": "4.0",
            "study_hours_per_week": "81",
            "career_interest": "",
            "course_rigor_preference": "Balanced",
        },
    )

    assert response.status_code == 200
    assert b"Graduation year must be between 2026 and 2035." in response.data
    assert b"Study hours must be between 0 and 80 per week." in response.data
