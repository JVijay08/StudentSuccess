"""Explain catalog differences without inventing hours, eligibility, or rankings."""
from collections import defaultdict


def _values(course, key):
    return {str(value).strip() for value in course.get(key, []) if str(value).strip()}


def suggested_pairs(courses, grade, anchor=None, limit=3):
    """Offer same-subject options with overlapping catalog grade ranges."""
    groups = defaultdict(list)
    for course in courses:
        groups[course.get("subject")].append(course)
    pairs = []
    anchors = [anchor] if anchor else [
        next((c for c in group if grade in c.get("grade_levels", [])), None)
        for group in groups.values()
    ]
    for first in anchors:
        if not first:
            continue
        candidates = [c for c in groups[first.get("subject")]
                      if c["course_id"] != first["course_id"]
                      and set(c.get("grade_levels", [])) & set(first.get("grade_levels", []))]
        if not candidates:
            continue
        def difference(other):
            return (grade in other.get("grade_levels", []),
                    first.get("workload_level") != other.get("workload_level"),
                    first.get("rigor_level") != other.get("rigor_level"),
                    _values(first, "prerequisites") != _values(other, "prerequisites"))
        second = max(candidates, key=difference)
        pairs.append([first, second])
        if len(pairs) == limit:
            break
    return pairs


def build_comparison(courses, grade):
    if len(courses) < 2:
        return None
    rows = []
    fields = [("workload_level", "Time commitment"), ("rigor_level", "Academic depth"),
              ("prerequisites", "Listed prerequisites"), ("career_clusters", "Career pathways"),
              ("grade_levels", "Catalog grade years"), ("graduation_category", "Graduation category"),
              ("course_type", "Course type"), ("subject", "Subject")]
    for key, label in fields:
        values = []
        normalized = []
        for course in courses:
            value = course.get(key)
            if isinstance(value, list):
                normalized.append(tuple(sorted(str(v) for v in value)))
                values.append(", ".join(str(v) for v in value) or "Not listed")
            else:
                normalized.append(value or None)
                values.append(value or "Not listed")
        rows.append({"label": label, "values": values, "different": len(set(normalized)) > 1})

    levels = {"Low": 0, "Medium": 1, "High": 2}
    workload = [c.get("workload_level") for c in courses]
    if any(v not in levels for v in workload):
        time = "Some workload labels are missing or unrecognized, so a lighter option cannot be identified reliably."
    elif len(set(workload)) == 1:
        time = f"All selected courses have a {workload[0].lower()} time-commitment estimate. This catalog does not identify a lighter option."
    else:
        lightest = min(workload, key=levels.get)
        names = ", ".join(c["course_name"] for c in courses if c["workload_level"] == lightest)
        time = f"{names} has the lowest listed time commitment ({lightest}) among these options. This is a category comparison, not a weekly-hours estimate."

    prereqs = [_values(c, "prerequisites") for c in courses]
    shared = sorted(set.intersection(*prereqs))
    prereq_text = ("Shared prerequisites: " + ", ".join(shared) + ". " if shared else "No prerequisite is listed in common across all selected courses. ")
    prereq_text += "Check the course-specific requirements below; an empty list does not confirm that a course has no requirements."
    pathways = [_values(c, "career_clusters") for c in courses]
    shared_paths = sorted(set.intersection(*pathways))
    path_text = ("Shared pathways: " + ", ".join(shared_paths) + ". " if shared_paths else "No career pathway is listed in common across all selected courses. ")
    path_text += "Use the distinct catalog tags below to explore your interests; they are not admission or career guarantees."
    options = []
    for index, course in enumerate(courses):
        others_prereqs = set.union(*(p for i, p in enumerate(prereqs) if i != index))
        others_paths = set.union(*(p for i, p in enumerate(pathways) if i != index))
        options.append({"course": course,
                        "distinct_prereqs": sorted(prereqs[index] - others_prereqs),
                        "distinct_paths": sorted(pathways[index] - others_paths),
                        "grade_listed": grade in course.get("grade_levels", [])})
    return {"rows": rows, "time": time, "prerequisites": prereq_text,
            "pathways": path_text, "options": options,
            "different_count": sum(row["different"] for row in rows),
            "mixed_subjects": len({c.get("subject") for c in courses}) > 1}
