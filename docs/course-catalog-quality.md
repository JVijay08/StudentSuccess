# Course catalog quality

The explorer now groups equivalent title spellings (case, punctuation, ampersands, and common AP title abbreviations). Distinct year, level, and combined-course titles stay separate. Source labels describe where a listing came from, not proof that a course is exclusive to a state. Raw identifiers remain resolvable so existing plans are preserved.

Imported titles containing prerequisite/description paragraphs or more than 180 characters are excluded from new searches and new plan additions. Existing saved records use a short verification label. The raw records remain intact for correction against their original sources; guessing a title from the end of a paragraph is unsafe because some extracts appear to contain neighboring courses.

Run `.venv\Scripts\python.exe scripts/audit_course_catalogs.py` to list every affected identifier and grouped listing. This is a presentation safeguard, not a claim that every imported source has been independently verified.

## Verified additions, September 27, 2026

- Standard and honors ninth- and tenth-grade English, American Literature, Advanced Composition, and British Literature were added from the [Forsyth County English course digest](https://www.forsyth.k12.ga.us/district-services/teaching-learning/high-school-course-digest/english).
- Health and Personal Fitness were added from [Alliance Academy's published offerings](https://alliance.forsyth.k12.ga.us/academics/course-offerings), which currently identify the 2027–2028 school year. Each entry carries that coverage note; availability at other schools or in other years is not implied.

Academic-depth and workload values are planner estimates. District placement, prerequisite, credit, and availability decisions remain with the school. The Georgia catalog is still a partial local reference, not a complete statewide database.

## Remaining source work

Correct quarantined imports against original source tables and verify program offerings before relabeling them as current official catalogs. The audit output identifies the records. Do not delete legacy IDs, silently replace one course with another, or expand partial provider/district catalogs into claims of statewide coverage.
