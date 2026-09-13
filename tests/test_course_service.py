from services.course_service import (
    filter_courses,
    get_course_by_id,
    get_courses_by_grade,
    get_courses_by_subject,
    get_courses_by_type,
    get_catalogs,
    load_courses,
)


def test_load_courses_returns_non_empty_list():
    courses = load_courses()

    assert isinstance(courses, list)
    assert courses


def test_get_course_by_id_handles_known_and_unknown_ids():
    course = get_course_by_id("MATH_ALGEBRA_CC")

    assert course is not None
    assert course["course_name"] == "Algebra: Concepts and Connections"
    assert get_course_by_id("NOT_A_REAL_COURSE") is None


def test_course_filters_match_each_category():
    math_courses = get_courses_by_subject("math")
    ap_courses = get_courses_by_type("ap")
    ninth_grade_courses = get_courses_by_grade(9)

    assert math_courses
    assert all(course["subject"] == "Math" for course in math_courses)
    assert ap_courses
    assert all(course["course_type"] == "AP" for course in ap_courses)
    assert ninth_grade_courses
    assert all(9 in course["grade_levels"] for course in ninth_grade_courses)


def test_filter_courses_combines_filters():
    courses = filter_courses(grade_level=11, subject="Math", course_type="AP")

    assert courses
    assert all(
        11 in course["grade_levels"]
        and course["subject"] == "Math"
        and course["course_type"] == "AP"
        for course in courses
    )


def test_national_and_local_catalogs_are_separate():
    catalogs = get_catalogs()
    national_courses = load_courses("national")
    local_courses = load_courses("forsyth-ga")

    assert set(catalogs) == {"national", "forsyth-ga"}
    assert any(course["course_name"] == "Algebra I" for course in national_courses)
    assert any(
        course["course_name"] == "Algebra: Concepts and Connections"
        for course in local_courses
    )
