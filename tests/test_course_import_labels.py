from scripts.import_course_databases import grade_levels, planning_levels


def test_ap_and_ib_courses_are_advanced_high_workload():
    assert planning_levels({"course_name": "AP Biology"}, "AP") == (
        "Advanced",
        "High",
    )
    assert planning_levels({"course_name": "IB Biology HL"}, "IB") == (
        "Advanced",
        "High",
    )


def test_honors_course_has_honors_rigor_and_high_workload():
    assert planning_levels({"course_name": "English 10 Honors"}, "Standard") == (
        "Honors",
        "High",
    )


def test_explicit_advanced_and_dual_credit_courses_are_advanced():
    assert planning_levels(
        {"course_name": "Advanced Mathematical Decision Making"}, "Standard"
    ) == ("Advanced", "High")
    assert planning_levels(
        {"course_name": "Biology Dual Credit"}, "Standard"
    ) == ("Advanced", "High")


def test_college_credit_catalog_overrides_foundational_title():
    assert planning_levels(
        {"course_name": "Basic Pharmacology", "subject": "College Credit"},
        "Standard",
    ) == ("Advanced", "High")


def test_foundational_course_has_low_workload():
    assert planning_levels(
        {"course_name": "Introduction to Engineering"}, "Standard"
    ) == ("Standard", "Low")


def test_ambiguous_course_keeps_neutral_defaults():
    assert planning_levels({"course_name": "World History"}, "Standard") == (
        "Standard",
        "Medium",
    )


def test_math_compression_course_is_advanced_high_workload():
    assert planning_levels(
        {"course_name": "Math 3 Compression", "subject": "Mathematics"},
        "Standard",
    ) == ("Advanced", "High")


def test_explicit_grade_in_course_name_corrects_default_grade_band():
    assert grade_levels(
        {
            "course_name": "English/Language Arts III (11th Grade)",
            "grade_levels": [9, 10, 11, 12],
        }
    ) == [11]


def test_embedded_grade_range_is_not_mistaken_for_only_the_last_grade():
    assert grade_levels(
        {
            "course_name": "Description: advanced text. Grade Range: 9 - 12",
            "grade_levels": [12],
        }
    ) == [9, 10, 11, 12]
