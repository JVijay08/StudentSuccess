import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
COURSES_FILE = PROJECT_ROOT / "data" / "courses.json"
CATALOGS = {
    "national": {
        "label": "National reference",
        "description": "Common course families for broad planning; verify local requirements.",
        "path": PROJECT_ROOT / "data" / "courses_national.json",
    },
    "forsyth-ga": {
        "label": "Forsyth County, Georgia",
        "description": "Representative local catalog sourced from Forsyth County Schools.",
        "path": COURSES_FILE,
    },
}


def get_catalogs():
    return CATALOGS


def load_courses(catalog="forsyth-ga"):
    catalog_config = CATALOGS.get(catalog)
    if catalog_config is None:
        raise ValueError(f"Unknown course catalog: {catalog}")

    with catalog_config["path"].open("r", encoding="utf-8") as file:
        courses = json.load(file)

    if not isinstance(courses, list):
        raise ValueError("Course dataset must contain a list of courses.")

    return courses


def get_course_by_id(course_id, catalog="forsyth-ga"):
    for course in load_courses(catalog):
        if course["course_id"] == course_id:
            return course

    return None


def get_courses_by_subject(subject, catalog="forsyth-ga"):
    return [
        course
        for course in load_courses(catalog)
        if course["subject"].lower() == subject.lower()
    ]


def get_courses_by_type(course_type, catalog="forsyth-ga"):
    return [
        course
        for course in load_courses(catalog)
        if course["course_type"].lower() == course_type.lower()
    ]


def get_courses_by_grade(grade_level, catalog="forsyth-ga"):
    return [
        course
        for course in load_courses(catalog)
        if grade_level in course["grade_levels"]
    ]


def filter_courses(
    grade_level=None,
    subject=None,
    course_type=None,
    rigor_level=None,
    workload_level=None,
    career_cluster=None,
    query=None,
    catalog="forsyth-ga",
):
    matching_courses = []

    for course in load_courses(catalog):
        if grade_level is not None and grade_level not in course["grade_levels"]:
            continue

        if subject is not None and course["subject"].lower() != subject.lower():
            continue

        if (
            course_type is not None
            and course["course_type"].lower() != course_type.lower()
        ):
            continue

        if (
            rigor_level is not None
            and course["rigor_level"].lower() != rigor_level.lower()
        ):
            continue

        if (
            workload_level is not None
            and course["workload_level"].lower() != workload_level.lower()
        ):
            continue

        if career_cluster is not None and career_cluster.lower() not in [
            cluster.lower() for cluster in course.get("career_clusters", [])
        ]:
            continue

        if query is not None:
            searchable = " ".join(
                [
                    course["course_name"],
                    course["subject"],
                    course["course_type"],
                    *course.get("career_clusters", []),
                ]
            ).lower()
            if query.lower() not in searchable:
                continue

        matching_courses.append(course)

    return matching_courses


def get_catalog_options(catalog="forsyth-ga"):
    courses = load_courses(catalog)
    return {
        "subjects": sorted({course["subject"] for course in courses}),
        "course_types": sorted({course["course_type"] for course in courses}),
        "rigor_levels": sorted({course["rigor_level"] for course in courses}),
        "workload_levels": sorted(
            {course["workload_level"] for course in courses}
        ),
        "career_clusters": sorted(
            {
                cluster
                for course in courses
                for cluster in course.get("career_clusters", [])
            }
        ),
    }
