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

    courses = load_courses()

    for course in courses:

        if course["course_id"] == course_id:

            return course

    return None


def get_courses_by_subject(subject):

    courses = load_courses()
    matching_courses = []

    for course in courses:

        if course["subject"].lower() == subject.lower():

            matching_courses.append(course)

    return matching_courses


def get_courses_by_type(course_type):

    courses = load_courses()
    matching_courses = []

    for course in courses:

        if course["course_type"].lower() == course_type.lower():

            matching_courses.append(course)

    return matching_courses


def get_courses_by_grade(grade_level):

    courses = load_courses()
    matching_courses = []

    for course in courses:

        if grade_level in course["grade_levels"]:
            
            matching_courses.append(course)

    return matching_courses