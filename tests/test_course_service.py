from services.course_service import (
    filter_courses,
    get_course_by_id,
    get_courses_by_grade,
    get_courses_by_subject,
    get_courses_by_type,
    get_catalogs,
    get_state_options,
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

    assert {"national", "forsyth-ga", "ap", "ib"}.issubset(catalogs)
    assert {"al", "ar", "fl", "ky", "la", "ms", "nc", "sc", "tn", "va", "wv"}.issubset(catalogs)
    assert any(course["course_name"] == "Algebra I" for course in national_courses)
    assert any(
        course["course_name"] == "Algebra: Concepts and Connections"
        for course in local_courses
    )


def test_program_catalogs_include_supplied_ap_and_ib_references():
    ap_courses = load_courses("ap")
    ib_courses = load_courses("ib")

    assert any(course["course_name"] == "AP Cybersecurity" for course in ap_courses)
    assert any(course["course_name"] == "IB Global Politics" for course in ib_courses)
    assert all(course["course_type"] == "AP" for course in ap_courses)
    assert all(course["course_type"] == "IB" for course in ib_courses)


def test_state_options_cover_all_us_states_and_mark_only_loaded_states():
    states = get_state_options()

    assert len(states) == 50
    assert len({state["code"] for state in states}) == 50
    assert any(
        state["code"] == "GA"
        and state["available"]
        and state["catalog_id"] == "forsyth-ga"
        for state in states
    )
    assert any(
        state["code"] == "WI"
        and not state["available"]
        and state["catalog_id"] == "national"
        for state in states
    )
    for code, catalog_id in {
        "AL": "al",
        "AR": "ar",
        "FL": "fl",
        "KY": "ky",
        "LA": "la",
        "MS": "ms",
        "NC": "nc",
        "SC": "sc",
        "TN": "tn",
        "VA": "va",
        "WV": "wv",
    }.items():
        assert any(
            state["code"] == code
            and state["available"]
            and state["catalog_id"] == catalog_id
            for state in states
        )


def test_imported_state_catalogs_and_program_merges_are_usable():
    for catalog_id in ["al", "ar", "fl", "ky", "la", "ms", "nc", "sc", "tn", "va", "wv"]:
        courses = load_courses(catalog_id)
        assert courses
        assert len({course["course_id"] for course in courses}) == len(courses)

    assert len(load_courses("ap")) >= 67
    assert len(load_courses("ib")) >= 223
    assert all(course["course_type"] == "AP" for course in load_courses("ap"))
    assert all(course["course_type"] == "IB" for course in load_courses("ib"))
