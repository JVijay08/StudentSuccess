"""Advisory checks using entered hours and catalog prerequisite text only."""
from collections import defaultdict


def review_plan(rows, dual_courses, weekly_budget):
    checks = {}
    for row in rows:
        planned = row['planned']
        earlier = set()
        for other in rows:
            saved = other['planned']
            if saved.id != planned.id and (saved.status == 'completed' or (saved.school_year < planned.school_year and saved.status != 'considering')):
                earlier.update(str(other['course'].get(key, '')).strip().casefold() for key in ('course_name', 'display_name'))
        checks[planned.id] = [name for name in row['course'].get('prerequisites', []) if name.strip().casefold() not in earlier]
    hours = defaultdict(float)
    for course in dual_courses:
        if course.status != 'completed':
            hours[(course.school_year, course.term.strip().casefold())] += course.weekly_hours
    warnings = []
    for (year, term), total in sorted(hours.items()):
        if total > weekly_budget or total > 168:
            warnings.append(dict(year=year, term=term, hours=total, impossible=total > 168))
    return checks, warnings
