from models import PlannedCourse


def complete_profile(client):
    from tests.account_helpers import setup
    assert setup(client, grade='11', study_hours='15').status_code == 302


def test_course_explorer_filters_catalog(authed_client):
    complete_profile(authed_client)

    response = authed_client.get("/courses?subject=Math&course_type=AP")

    assert response.status_code == 200
    assert b"AP Calculus AB" in response.data
    assert b"AP Biology" not in response.data
    assert b"U.S. high-school planning" in response.data


def test_program_catalog_selection_overrides_stale_state_selection(authed_client):
    complete_profile(authed_client)

    response = authed_client.get("/courses?state=GA&catalog=ap&q=AP+Cybersecurity&nonpersonal_confirmed=yes")

    assert response.status_code == 200
    assert b"AP Cybersecurity" in response.data
    assert b"Algebra: Concepts and Connections" not in response.data


def test_course_can_be_added_and_removed_from_plan(app, authed_client):
    complete_profile(authed_client)

    response = authed_client.post(
        "/courses/plan/add/MATH_AP_STATISTICS",
        data={"school_year": "11", "term": "Full year", "status": "planned"},
    )
    assert response.status_code == 302

    with app.app_context():
        planned = PlannedCourse.query.one()
        planned_id = planned.id
        assert planned.course_id == "MATH_AP_STATISTICS"
        assert planned.school_year == 11
        assert planned.status == "planned"

    plan_response = authed_client.get("/courses/plan")
    assert plan_response.status_code == 200
    assert b"AP Statistics" in plan_response.data

    delete_response = authed_client.post(
        f"/courses/plan/{planned_id}/delete"
    )
    assert delete_response.status_code == 302

    with app.app_context():
        assert PlannedCourse.query.count() == 0

    second_delete_response = authed_client.post(
        f"/courses/plan/{planned_id}/delete"
    )
    assert second_delete_response.status_code == 302
    assert second_delete_response.headers["Location"].endswith("/courses/plan")


def test_course_detail_and_comparison_render(authed_client):
    complete_profile(authed_client)

    detail_response = authed_client.get("/courses/SCI_AP_CHEMISTRY")
    comparison_response = authed_client.get(
        "/courses/compare?id=SCI_AP_CHEMISTRY&id=SCI_AP_BIOLOGY"
    )

    assert detail_response.status_code == 200
    assert b"Algebra II" in detail_response.data
    assert comparison_response.status_code == 200
    assert b"AP Chemistry" in comparison_response.data
    assert b"AP Biology" in comparison_response.data


def test_course_comparison_requires_two_courses(authed_client):
    complete_profile(authed_client)
    response = authed_client.get("/courses/compare?id=SCI_AP_CHEMISTRY")
    assert response.status_code == 200
    assert b"Select at least two courses" in response.data
    assert b"Select two or three courses" in response.data
def test_legacy_catalog_migration_preserves_plan(app, authed_client):
    from app import _migrate_planned_course_catalog_column
    from extensions import db
    from models import PlannedCourse
    from tests.test_main_routes import add_profile

    with app.app_context():
        profile = add_profile(authed_client.user_id)
        planned = PlannedCourse(
            student_profile_id=profile.id, catalog_id="forsyth-ga",
            course_id="MATH_ALGEBRA_CC", school_year=9,
        )
        db.session.add(planned)
        db.session.commit()
        saved_id = planned.id
        _migrate_planned_course_catalog_column()
        _migrate_planned_course_catalog_column()
        db.session.expire_all()
        assert db.session.get(PlannedCourse, saved_id).catalog_id == "ga"
        assert PlannedCourse.query.count() == 1
    response = authed_client.get("/courses/plan")
    assert response.status_code == 200
    assert b"Georgia reference" in response.data
    assert b"forsyth" not in response.data.lower()
