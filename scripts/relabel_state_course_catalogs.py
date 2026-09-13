"""Apply repeatable planning-label rules to existing state course catalogs."""

import json
from pathlib import Path

from import_course_databases import course_kind, planning_levels


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
EXCLUDED_FILES = {"courses_ap.json", "courses_ib.json"}


def relabel_catalog(path):
    courses = json.loads(path.read_text(encoding="utf-8"))
    changed = 0

    for course in courses:
        rigor_level, workload_level = planning_levels(
            course, course_kind(course)
        )
        if (
            course.get("rigor_level") != rigor_level
            or course.get("workload_level") != workload_level
        ):
            course["rigor_level"] = rigor_level
            course["workload_level"] = workload_level
            changed += 1

    path.write_text(
        json.dumps(courses, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    return len(courses), changed


def main():
    total_courses = 0
    total_changed = 0
    for path in sorted(DATA_DIR.glob("courses_??.json")):
        if path.name in EXCLUDED_FILES:
            continue
        course_count, changed_count = relabel_catalog(path)
        total_courses += course_count
        total_changed += changed_count
        print(f"{path.name}: {changed_count} of {course_count} relabeled")

    print(f"Total: {total_changed} of {total_courses} relabeled")


if __name__ == "__main__":
    main()
