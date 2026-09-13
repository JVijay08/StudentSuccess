import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
COURSES_FILE = PROJECT_ROOT / "data" / "courses.json"
CATALOGS = {
    "national": {
        "label": "National reference",
        "description": "Common course families for broad planning; verify local requirements.",
        "path": PROJECT_ROOT / "data" / "courses_national.json",
        "kind": "reference",
        "state": None,
    },
    "forsyth-ga": {
        "label": "Forsyth County, Georgia",
        "description": "Representative local catalog sourced from Forsyth County Schools.",
        "path": COURSES_FILE,
        "kind": "state",
        "state": "GA",
    },
    "al": {
        "label": "Alabama",
        "description": "Supplied Alabama statewide course catalog; verify current local availability.",
        "path": PROJECT_ROOT / "data" / "courses_al.json",
        "kind": "state",
        "state": "AL",
    },
    "ar": {
        "label": "Arkansas",
        "description": "Supplied Arkansas statewide course catalog; verify current local availability.",
        "path": PROJECT_ROOT / "data" / "courses_ar.json",
        "kind": "state",
        "state": "AR",
    },
    "fl": {
        "label": "Florida",
        "description": "Supplied Florida provider catalog; not a complete statewide master catalog.",
        "path": PROJECT_ROOT / "data" / "courses_fl.json",
        "kind": "state",
        "state": "FL",
    },
    "ky": {
        "label": "Kentucky",
        "description": "Supplied Kentucky course-code and CTE records; coverage is partial.",
        "path": PROJECT_ROOT / "data" / "courses_ky.json",
        "kind": "state",
        "state": "KY",
    },
    "la": {
        "label": "Louisiana",
        "description": "Supplied Louisiana provider catalog; not a complete statewide master catalog.",
        "path": PROJECT_ROOT / "data" / "courses_la.json",
        "kind": "state",
        "state": "LA",
    },
    "ms": {
        "label": "Mississippi",
        "description": "Supplied Mississippi graduation-pathway records; coverage is limited.",
        "path": PROJECT_ROOT / "data" / "courses_ms.json",
        "kind": "state",
        "state": "MS",
    },
    "nc": {
        "label": "North Carolina",
        "description": "Supplied North Carolina statewide CTE inventory; not a full academic catalog.",
        "path": PROJECT_ROOT / "data" / "courses_nc.json",
        "kind": "state",
        "state": "NC",
    },
    "sc": {
        "label": "South Carolina",
        "description": "Supplied South Carolina School for the Deaf and the Blind course guide.",
        "path": PROJECT_ROOT / "data" / "courses_sc.json",
        "kind": "state",
        "state": "SC",
    },
    "tn": {
        "label": "Tennessee",
        "description": "Supplied Tennessee approved-course catalog; source is dated 2016.",
        "path": PROJECT_ROOT / "data" / "courses_tn.json",
        "kind": "state",
        "state": "TN",
    },
    "va": {
        "label": "Virginia",
        "description": "Supplied Virtual Virginia provider catalog; not a complete statewide catalog.",
        "path": PROJECT_ROOT / "data" / "courses_va.json",
        "kind": "state",
        "state": "VA",
    },
    "wv": {
        "label": "West Virginia",
        "description": "Supplied Berkeley Springs High School course-selection catalog; local coverage only.",
        "path": PROJECT_ROOT / "data" / "courses_wv.json",
        "kind": "state",
        "state": "WV",
    },
    "il": {"label": "Illinois", "description": "Supplied Illinois district catalog extract; coverage is partial.", "path": PROJECT_ROOT / "data" / "courses_il.json", "kind": "state", "state": "IL"},
    "in": {"label": "Indiana", "description": "Supplied Indiana statewide course-title catalog.", "path": PROJECT_ROOT / "data" / "courses_in.json", "kind": "state", "state": "IN"},
    "mi": {"label": "Michigan", "description": "Supplied Michigan district course catalog.", "path": PROJECT_ROOT / "data" / "courses_mi.json", "kind": "state", "state": "MI"},
    "mn": {"label": "Minnesota", "description": "Supplied Minnesota statewide course-classification extract.", "path": PROJECT_ROOT / "data" / "courses_mn.json", "kind": "state", "state": "MN"},
    "oh": {"label": "Ohio", "description": "Supplied Ohio local school course catalog.", "path": PROJECT_ROOT / "data" / "courses_oh.json", "kind": "state", "state": "OH"},
    "wi": {"label": "Wisconsin", "description": "Supplied Wisconsin virtual-provider catalog.", "path": PROJECT_ROOT / "data" / "courses_wi.json", "kind": "state", "state": "WI"},
    "ia": {"label": "Iowa", "description": "Supplied Iowa district master catalog.", "path": PROJECT_ROOT / "data" / "courses_ia.json", "kind": "state", "state": "IA"},
    "ks": {"label": "Kansas", "description": "Supplied Kansas district catalog extract; coverage is partial.", "path": PROJECT_ROOT / "data" / "courses_ks.json", "kind": "state", "state": "KS"},
    "mo": {"label": "Missouri", "description": "Supplied Missouri FCS and human-services course list.", "path": PROJECT_ROOT / "data" / "courses_mo.json", "kind": "state", "state": "MO"},
    "ne": {"label": "Nebraska", "description": "Supplied Nebraska statewide course-code list; source is dated.", "path": PROJECT_ROOT / "data" / "courses_ne.json", "kind": "state", "state": "NE"},
    "nd": {"label": "North Dakota", "description": "Supplied North Dakota distance-provider catalog extract.", "path": PROJECT_ROOT / "data" / "courses_nd.json", "kind": "state", "state": "ND"},
    "sd": {"label": "South Dakota", "description": "Supplied South Dakota local school course catalog.", "path": PROJECT_ROOT / "data" / "courses_sd.json", "kind": "state", "state": "SD"},
    "ap": {
        "label": "Advanced Placement (AP)",
        "description": "Program-level AP reference catalog; local availability varies.",
        "path": PROJECT_ROOT / "data" / "courses_ap.json",
        "kind": "program",
        "state": None,
    },
    "ib": {
        "label": "International Baccalaureate (IB)",
        "description": "IB Diploma Programme subject reference; school availability varies.",
        "path": PROJECT_ROOT / "data" / "courses_ib.json",
        "kind": "program",
        "state": None,
    },
}

US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming",
}


def get_catalogs():
    return CATALOGS


def get_state_options():
    local_states = {
        catalog["state"]: catalog_id
        for catalog_id, catalog in CATALOGS.items()
        if catalog["state"]
    }
    return [
        {
            "code": code,
            "name": name,
            "catalog_id": local_states.get(code, "national"),
            "available": code in local_states,
        }
        for code, name in sorted(US_STATES.items(), key=lambda item: item[1])
    ]


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
