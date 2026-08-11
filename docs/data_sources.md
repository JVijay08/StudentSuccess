# StudentSuccess AI Data Sources

## Source-Use Rules

StudentSuccess AI uses public reference information only when it supports a visible feature.

The project records where curated data came from and distinguishes source facts from project-created estimates.

Project-created workload labels are educational estimates. They are not official ratings from a school or organization.

---

## Planned Sources

| Data Type | Source Organization | Source Title / Page | What Will Be Used | Source Type | Status |
|---|---|---|---|---|---|
| Course catalog | Forsyth County Schools | High School Course Digest, accessed July 4, 2026 | Course names, prerequisites, grade levels, graduation category | Public official source | In Use |
| Portfolio activities | To be added later | Public program, competition, or organization pages | Activity names, categories, descriptions, time commitments | Public reference source | Planned |
| Student ML training data | StudentSuccess AI project | Generated with Python later | Synthetic student-record features for ML demonstration models | Synthetic project data | Planned |

---

## Data Limitations

- Course prerequisites and grade eligibility should come from official course-catalog sources when available.
- Course workload levels will be project estimates unless an official source provides workload information.
- Portfolio recommendations are suggestions for growth and exploration. They do not guarantee admissions outcomes.
- Machine-learning training data will be synthetic and clearly labeled as synthetic.

## Source Links

- Official Course Catalog: [https://www.forsyth.k12.ga.us/district-services/teaching-learning/high-school-course-digest](https://www.forsyth.k12.ga.us/district-services/teaching-learning/high-school-course-digest)

## Verification Notes

The course catalog source was selected because it is hosted by the official school or district organization. Course workload labels will not be copied from the source unless the source explicitly provides them; any workload labels added later will be StudentSuccess project estimates.

---

## Initial Course Catalog Scope

The first StudentSuccess AI Course Pathway catalog will contain 33 representative Forsyth County high-school courses.

This intentionally small catalog is designed to demonstrate course sequences, prerequisites, advanced-course options, career pathways, and language progression without attempting to reproduce the entire district catalog.

The final structured dataset will be created later in `data/courses.json`.

### Important Data Rule

Prerequisites, eligibility notes, course titles, and official course descriptions below are based on public Forsyth County Schools course information.

The `Planning Grade Band` column is a StudentSuccess planning estimate unless the official source explicitly states the grade level. It is not an official district placement guarantee.

Courses requiring department approval, application, teacher recommendation, or other special eligibility rules must retain that information in the future dataset.

---

### Mathematics

| Course Name | Source-Verified Prerequisite or Eligibility Note | Planning Grade Band | Catalog Role |
|---|---|---|---|
| Algebra: Concepts and Connections | Successful completion of 8th Grade Math or 7th Grade Advanced Math | 9 | Core math sequence |
| Geometry: Concepts and Connections | Successful completion of Algebra: Concepts and Connections | 9–10 | Core math sequence |
| Advanced Algebra: Concepts and Connections | Successful completion of Geometry: Concepts and Connections or Honors Geometry: Concepts and Connections | 10–11 | Core math sequence |
| Precalculus | Successful completion of Advanced Algebra: Concepts and Connections | 11–12 | Advanced core math option |
| AP Precalculus | Successful completion of FCS Accelerated Geometry B/Advanced Algebra: Concepts and Connections or FCS Honors Advanced Algebra: Concepts and Connections | 10–12 | Advanced/AP math option |
| AP Statistics | Successful completion of Advanced Algebra: Concepts and Connections | 11–12 | AP statistics option |
| AP Calculus AB | Math department approval required; source does not state a specific course prerequisite | 11–12 | AP calculus option |
| AP Calculus BC | Successful completion of AP Calculus AB; math department approval required | 12 | Advanced AP calculus option |

### Science

| Course Name | Source-Verified Prerequisite or Eligibility Note | Planning Grade Band | Catalog Role |
|---|---|---|---|
| Biology | Strong K–8 science background and science-inquiry skills | 9–10 | Core science sequence |
| Chemistry | Biology and Algebra: Concepts and Connections; Geometry: Concepts and Connections is a co-requisite | 10–12 | Core science sequence |
| AP Biology | Biology and Chemistry; honors courses highly recommended for success | 11–12 | AP life-science option |
| AP Chemistry | Chemistry and Advanced Algebra: Concepts and Connections; honors/accelerated preparation highly recommended | 11–12 | AP physical-science option |
| Physics | Geometry: Concepts and Connections and Algebra: Concepts and Connections; Advanced Algebra taken or concurrent | 11–12 | Core physics option |
| AP Physics 1 | Geometry, Algebra, and Biology; Advanced Algebra taken or concurrent | 11–12 | AP algebra-based physics option |
| AP Environmental Science | Biology, Chemistry, and Algebra: Concepts and Connections | 11–12 | AP environmental-science option |

### English Language Arts

| Course Name | Source-Verified Prerequisite or Eligibility Note | Planning Grade Band | Catalog Role |
|---|---|---|---|
| 9th Grade Literature and Composition | Core entry course; no formal prerequisite listed in source | 9 | Core English sequence |
| 10th Grade Literature and Composition | Course description states it builds upon 9th Grade Literature and Composition | 10 | Core English sequence |
| American Literature and Composition | Course description states it builds upon 10th Grade Literature and Composition | 11 | Core English sequence |
| AP English Language and Composition / American Literature | Officially identified as an 11th-grade course | 11 | Advanced English option |
| AP English Literature and Composition | Officially identified as a 12th-grade course | 12 | Advanced English option |

### Social Studies

| Course Name | Source-Verified Prerequisite or Eligibility Note | Planning Grade Band | Catalog Role |
|---|---|---|---|
| World History | Required year-long course; no formal prerequisite listed in source | 9–10 | Core social-studies option |
| AP World History | Advanced world-history option; no formal prerequisite listed in source | 9–10 | AP social-studies option |
| United States History | Required year-long course; no formal prerequisite listed in source | 11 | Core social-studies option |
| AP United States History | Advanced U.S.-history option; no formal prerequisite listed in source | 11 | AP social-studies option |
| American Government | Required one-semester course; no formal prerequisite listed in source | 12 | Graduation-related social-studies option |

### CTAE / Career Pathways

| Course Name | Source-Verified Prerequisite or Eligibility Note | Planning Grade Band | Catalog Role |
|---|---|---|---|
| Introduction to Software Technology | Listed as the first course in the Computer Science pathway | 9–10 | Computer Science pathway foundation |
| AP Computer Science Principles | Listed as a second-course option in the Computer Science pathway | 10–11 | Computer Science pathway option |
| AP Computer Science A | Listed as the later course in the Computer Science pathway | 11–12 | Computer Science pathway advanced course |
| Foundations of Engineering and Technology | Listed as the first course in the Engineering and Technology pathway | 9–10 | Engineering pathway foundation |
| Engineering Concepts | Listed after Foundations of Engineering and Technology in the Engineering and Technology pathway | 10–11 | Engineering pathway continuation |

### World Language

| Course Name | Source-Verified Prerequisite or Eligibility Note | Planning Grade Band | Catalog Role |
|---|---|---|---|
| Spanish I | Entry-level Spanish course; no formal prerequisite listed in source | 9–12 | World-language foundation |
| Spanish II | Enhances Spanish I skills | 9–12 | World-language continuation |
| Spanish III | Enhances Spanish II skills | 10–12 | World-language continuation |

### Scope Notes

- The initial catalog includes 33 representative courses.
- The project does not yet include every Forsyth County Schools course.
- Support courses, application-only courses, IB courses, dual-enrollment placeholders, and highly specialized electives will be added only after the core pathway logic works.
- Dual Enrollment will not be represented as one generic course. Any future dual-enrollment entry must use an actual course title and clearly state its separate eligibility requirements.
- The future pathway tool must treat department approval, teacher recommendation, application-only status, and co-requisites as separate eligibility information rather than assuming a student is automatically eligible.
- Course workload labels will be added later as StudentSuccess educational planning estimates, not as official Forsyth County Schools ratings.

## Source Links

- Official Course Catalog: [https://www.forsyth.k12.ga.us/district-services/teaching-learning/high-school-course-digest](https://www.forsyth.k12.ga.us/district-services/teaching-learning/high-school-course-digest)
- Mathematics: [https://sfhs.forsyth.k12.ga.us/academics/mathematics](https://sfhs.forsyth.k12.ga.us/academics/mathematics)
- Science: [https://sfhs.forsyth.k12.ga.us/academics/science](https://sfhs.forsyth.k12.ga.us/academics/science)
- English Language Arts: [https://sfhs.forsyth.k12.ga.us/academics/englishlanguage-arts](https://sfhs.forsyth.k12.ga.us/academics/englishlanguage-arts)
- Social Studies: [https://sfhs.forsyth.k12.ga.us/academics/social-studies](https://sfhs.forsyth.k12.ga.us/academics/social-studies)
- CTAE / Career Pathways: [https://sfhs.forsyth.k12.ga.us/academics/career-tech](https://sfhs.forsyth.k12.ga.us/academics/career-tech)
- World Languages: [https://sfhs.forsyth.k12.ga.us/academics/world-languages-department](https://sfhs.forsyth.k12.ga.us/academics/world-languages-department)


