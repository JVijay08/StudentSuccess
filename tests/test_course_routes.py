from models import PlannedCourse


def complete_profile(client):
    response = client.post(
        "/onboarding",
        data={
            "first_name": "Course Demo",
            "grade_level": "11",
            "graduation_year": "2027",
            "current_gpa": "4.0",
            "target_gpa": "4.5",
            "study_hours_per_week": "15",
            "career_interest": "Engineering",
            "course_rigor_preference": "Challenging",
        },
    )
    assert response.status_code == 302


def test_course_explorer_filters_catalog(authed_client):
    complete_profile(authed_client)

    response = authed_client.get("/courses?subject=Math&course_type=AP")

    assert response.status_code == 200
    assert b"AP Calculus AB" in response.data
    assert b"AP Biology" not in response.data


def test_program_catalog_selection_overrides_stale_state_selection(authed_client):
    complete_profile(authed_client)

    response = authed_client.get("/courses?state=GA&catalog=ap")

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
