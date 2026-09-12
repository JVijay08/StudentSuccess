import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
COURSES_FILE = PROJECT_ROOT / "data" / "courses.json"


def load_courses():
    with COURSES_FILE.open("r", encoding="utf-8") as file:
        courses = json.load(file)

    if not isinstance(courses, list):
        raise ValueError("Course dataset must contain a list of courses.")

    return courses


def get_course_by_id(course_id):
    for course in load_courses():
        if course["course_id"] == course_id:
            return course

    return None


def get_courses_by_subject(subject):
    return [
        course
        for course in load_courses()
        if course["subject"].lower() == subject.lower()
    ]


def get_courses_by_type(course_type):
    return [
        course
        for course in load_courses()
        if course["course_type"].lower() == course_type.lower()
    ]


def get_courses_by_grade(grade_level):
    return [
        course
        for course in load_courses()
        if grade_level in course["grade_levels"]
    ]


def filter_courses(grade_level=None, subject=None, course_type=None):
    matching_courses = []

    for course in load_courses():
        if grade_level is not None and grade_level not in course["grade_levels"]:
            continue

        if subject is not None and course["subject"].lower() != subject.lower():
            continue

        if (
            course_type is not None
            and course["course_type"].lower() != course_type.lower()
        ):
            continue

        matching_courses.append(course)

    return matching_courses
