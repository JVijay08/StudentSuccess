from copy import deepcopy

from services.course_comparison import build_comparison, suggested_pairs
from services.course_service import get_course_by_id
from tests.test_course_routes import complete_profile


def test_real_science_tradeoffs_do_not_invent_a_lighter_course():
    courses = [get_course_by_id(key, "national") for key in ["SCI_AP_CHEMISTRY", "SCI_AP_BIOLOGY"]]
    result = build_comparison(courses, 11)
    assert "does not identify a lighter option" in result["time"]
    assert "Shared prerequisites: Chemistry." in result["prerequisites"]
    assert result["options"][0]["distinct_prereqs"] == ["Algebra II"]
    assert result["options"][1]["distinct_prereqs"] == ["Biology"]
    assert result["options"][0]["distinct_paths"] == ["Engineering"]
    assert result["options"][1]["distinct_paths"] == ["Environmental Science"]
    assert result["different_count"] == 2


def test_lighter_option_and_missing_data():
    first = deepcopy(get_course_by_id("SCI_AP_BIOLOGY", "national"))
    second = deepcopy(first)
    first.update(course_name="Lower workload", workload_level="Medium")
    result = build_comparison([first, second], 9)
    assert "Lower workload has the lowest" in result["time"]
    assert not result["options"][0]["grade_listed"]
    second.pop("workload_level")
    assert "cannot be identified reliably" in build_comparison([first, second], 11)["time"]


def test_three_way_shared_is_intersection_and_unique_excludes_both_other_options():
    base = get_course_by_id("SCI_AP_BIOLOGY", "national")
    courses = [dict(base, prerequisites=p) for p in [["A", "B"], ["A", "C"], ["C", "D"]]]
    result = build_comparison(courses, 11)
    assert "No prerequisite is listed in common" in result["prerequisites"]
    assert [option["distinct_prereqs"] for option in result["options"]] == [["B"], [], ["D"]]


def test_reordered_lists_are_not_reported_as_differences():
    first = get_course_by_id("SCI_AP_BIOLOGY", "national")
    second = dict(first, prerequisites=list(reversed(first["prerequisites"])))
    assert build_comparison([first, second], 11)["different_count"] == 0


def test_pair_suggestions_require_subject_and_grade_overlap():
    base = get_course_by_id("SCI_AP_BIOLOGY", "national")
    courses = [base, dict(base, course_id="other-subject", subject="English"),
               dict(base, course_id="other-grade", grade_levels=[9]),
               dict(base, course_id="valid", workload_level="Medium")]
    pairs = suggested_pairs(courses, 11, anchor=base)
    assert pairs[0][1]["course_id"] == "valid"
    assert suggested_pairs(courses[:3], 11, anchor=base) == []


def test_duplicate_and_unknown_ids_do_not_make_a_comparison(authed_client):
    complete_profile(authed_client)
    response = authed_client.get("/courses/compare?id=SCI_AP_BIOLOGY&id=SCI_AP_BIOLOGY&id=unknown")
    assert b"Select at least two courses" in response.data
    assert b'class="tradeoff-summary"' not in response.data


def test_compare_rendering_preserves_catalog_and_saves_selection(app, authed_client):
    from services.course_service import load_courses
    from models import PlannedCourse
    complete_profile(authed_client)
    ids = [c["course_id"] for c in load_courses("ap")[:2]]
    response = authed_client.get("/courses/compare", query_string={"catalog": "ap", "id": ids})
    assert response.status_code == 200
    assert b'catalog=ap' in response.data
    assert b'name="catalog" value="ap"' in response.data
    assert b'id="differences-only"' in response.data
    saved_response = authed_client.post("/courses/plan/add/" + ids[0], data={"catalog": "ap", "school_year": "11", "status": "considering", "comparison_id": ids})
    assert "/courses/compare?" in saved_response.headers["Location"]
    assert "catalog=ap" in saved_response.headers["Location"]
    with app.app_context():
        saved = PlannedCourse.query.one()
        assert saved.catalog_id == "ap" and saved.course_id == ids[0]
