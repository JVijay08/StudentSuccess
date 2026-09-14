import argparse
import json
import re
from pathlib import Path


STATE_CODES = {
    "Alabama": "AL",
    "Arkansas": "AR",
    "Florida": "FL",
    "Georgia": "GA",
    "Illinois": "IL",
    "Indiana": "IN",
    "Iowa": "IA",
    "Kentucky": "KY",
    "Louisiana": "LA",
    "Michigan": "MI",
    "Minnesota": "MN",
    "Mississippi": "MS",
    "North Carolina": "NC",
    "North Dakota": "ND",
    "Nebraska": "NE",
    "Ohio": "OH",
    "South Carolina": "SC",
    "Tennessee": "TN",
    "Virginia": "VA",
    "West Virginia": "WV",
    "Wisconsin": "WI",
    "South Dakota": "SD",
    "Missouri": "MO",
    "Kansas": "KS",
}

FOUNDATIONAL_TITLE_PATTERN = re.compile(
    r"\b(?:basic|beginning|essentials?|exploratory|exploration|foundations?|"
    r"fundamentals?|intro|introduction|introductory|orientation|survey)\b",
    re.IGNORECASE,
)
HONORS_TITLE_PATTERN = re.compile(r"\bhonou?rs?\b", re.IGNORECASE)
ADVANCED_TITLE_PATTERN = re.compile(
    r"\b(?:advanced|accelerated|capstone|college[ -]level|dual[ -](?:credit|enrollment)|"
    r"internship|practicum)\b",
    re.IGNORECASE,
)


def slug(value):
    return re.sub(r"[^A-Z0-9]+", "_", str(value).upper()).strip("_")


def course_kind(record):
    name = record.get("course_name", "").upper()
    kind = str(record.get("course_type", "")).upper()
    source_section = str(record.get("source_section", "")).upper()
    if kind == "AP" or name.startswith("AP ") or "ADVANCED PLACEMENT" in name or source_section == "ADVANCED PLACEMENT":
        return "AP"
    if kind == "IB" or name.startswith("IB ") or "INTERNATIONAL BACCALAUREATE" in source_section:
        return "IB"
    return "Standard"


def planning_levels(record, kind):
    """Return conservative project-created rigor and workload estimates.

    Imported state sources generally provide course titles, not official
    difficulty ratings. Only explicit title or catalog signals change the
    neutral Standard/Medium defaults.
    """
    name = str(record.get("course_name") or record.get("subject_name") or "")
    subject = str(record.get("subject") or record.get("source_section") or "")

    if kind in {"AP", "IB"}:
        return "Advanced", "High"
    if HONORS_TITLE_PATTERN.search(name):
        return "Honors", "High"
    if subject.casefold() in {"math", "mathematics"} and re.search(
        r"\bcompression\b", name, re.IGNORECASE
    ):
        return "Advanced", "High"
    if subject.casefold() == "college credit" or ADVANCED_TITLE_PATTERN.search(name):
        return "Advanced", "High"
    if FOUNDATIONAL_TITLE_PATTERN.search(name):
        return "Standard", "Low"
    return "Standard", "Medium"


def grade_levels(record):
    levels = record.get("grade_levels")
    name = str(record.get("course_name") or record.get("subject_name") or "")
    embedded_range = re.search(
        r"\bgrade range:\s*(9|10|11|12)\s*-\s*(9|10|11|12)\b",
        name,
        re.IGNORECASE,
    )
    if embedded_range:
        first, last = map(int, embedded_range.groups())
        return list(range(first, last + 1))

    named_grade = re.search(
        r"\((9|10|11|12)(?:st|nd|rd|th) grade\b[^)]*\)\s*$",
        name,
        re.IGNORECASE,
    )
    if named_grade:
        return [int(named_grade.group(1))]

    if isinstance(levels, list) and levels:
        return sorted({int(level) for level in levels if str(level).isdigit()})

    text = " ".join(
        str(record.get(field, ""))
        for field in ("grade_levels_text", "school_level")
    )
    found = {int(level) for level in re.findall(r"\b(9|10|11|12)\b", text)}
    return sorted(found) or [9, 10, 11, 12]


def prerequisites(record):
    values = record.get("prerequisites") or record.get("prerequisite") or []
    if isinstance(values, list):
        return [str(value) for value in values if value]
    return [str(values)] if values else []


def source_identifier(record):
    for field in ("course_id", "course_code", "course_number", "course_codes"):
        value = record.get(field)
        if isinstance(value, list):
            value = value[0] if value else None
        if value:
            return str(value)
    return record.get("course_name", "course")


def normalize_record(record, subject, state_code, source_state, index):
    kind = course_kind(record)
    name = record.get("course_name") or record.get("subject_name")
    rigor_level, workload_level = planning_levels(
        {**record, "course_name": name, "subject": subject}, kind
    )
    source = record.get("source") or source_state
    identifier = f"{state_code}_{slug(source_identifier(record))}"
    if not identifier.strip("_"):
        identifier = f"{state_code}_{index}"
    return {
        "course_id": identifier,
        "course_name": name,
        "subject": subject,
        "course_type": kind,
        "grade_levels": grade_levels(record),
        "rigor_level": rigor_level,
        "workload_level": workload_level,
        "prerequisites": prerequisites(record),
        "graduation_category": record.get("graduation_category") or subject,
        "career_clusters": record.get("career_clusters") or [],
        "source_state": source_state,
        "source_page": record.get("source_page"),
        "source": source,
    }


def iter_state_records(info):
    for subject, records in info.get("subjects", {}).items():
        for record in records:
            if isinstance(record, dict) and record.get("course_name"):
                yield subject, record


def iter_ib_records(data):
    program = data.get("supplemental_programs", {}).get(
        "International Baccalaureate Diploma Programme", {}
    )
    for subject, records in program.get("subjects_by_group", {}).items():
        for record in records:
            if isinstance(record, dict) and record.get("subject_name"):
                yield subject, {
                    **record,
                    "course_name": f"IB {record['subject_name'].title()}",
                    "course_type": "IB",
                }


def append_unique(target, records):
    existing_names = {record["course_name"].casefold() for record in target}
    existing_ids = {record["course_id"] for record in target}
    for record in records:
        name_key = record["course_name"].casefold()
        if name_key in existing_names:
            continue
        base_id = record["course_id"]
        candidate = base_id
        suffix = 2
        while candidate in existing_ids:
            candidate = f"{base_id}_{suffix}"
            suffix += 1
        record["course_id"] = candidate
        target.append(record)
        existing_names.add(name_key)
        existing_ids.add(candidate)


def append_with_unique_id(target, record):
    existing_ids = {item["course_id"] for item in target}
    base_id = record["course_id"]
    candidate = base_id
    suffix = 2
    while candidate in existing_ids:
        candidate = f"{base_id}_{suffix}"
        suffix += 1
    record["course_id"] = candidate
    target.append(record)


def write_json(path, records):
    path.write_text(json.dumps(records, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Import supplied state course databases.")
    parser.add_argument("sources", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, default=Path("data"))
    args = parser.parse_args()

    sources = [json.loads(path.read_text(encoding="utf-8")) for path in args.sources]
    states = {}
    ap_records = []
    ib_records = []

    for source in sources:
        source_label = source.get("database_name", source.get("description", "Supplied database"))
        for state, info in source.get("states", {}).items():
            state_code = STATE_CODES[state]
            state_records = []
            for index, (subject, record) in enumerate(iter_state_records(info), start=1):
                normalized = normalize_record(record, subject, state_code, state, index)
                if normalized["course_type"] == "AP":
                    ap_records.append(normalized)
                elif normalized["course_type"] == "IB":
                    ib_records.append(normalized)
                else:
                    append_with_unique_id(state_records, normalized)
            states[state] = state_records

        for subject, record in iter_ib_records(source):
            ib_records.append(normalize_record(record, subject, "IB", "International Baccalaureate", len(ib_records) + 1))

    args.output.mkdir(parents=True, exist_ok=True)
    for state, records in states.items():
        if state != "Georgia":
            write_json(args.output / f"courses_{STATE_CODES[state].lower()}.json", records)

    ap_path = args.output / "courses_ap.json"
    ib_path = args.output / "courses_ib.json"
    ap_catalog = json.loads(ap_path.read_text(encoding="utf-8")) if ap_path.exists() else []
    ib_catalog = json.loads(ib_path.read_text(encoding="utf-8")) if ib_path.exists() else []
    append_unique(ap_catalog, [record for record in ap_records if record["course_type"] == "AP"])
    append_unique(ib_catalog, [record for record in ib_records if record["course_type"] == "IB"])
    write_json(ap_path, ap_catalog)
    write_json(ib_path, ib_catalog)

    print(f"Imported {len(states)} state catalogs.")
    print(f"Added {len(ap_catalog)} AP catalog records and {len(ib_catalog)} IB catalog records.")
    for state, records in states.items():
        print(f"{state}: {len(records)} state records")


if __name__ == "__main__":
    main()
