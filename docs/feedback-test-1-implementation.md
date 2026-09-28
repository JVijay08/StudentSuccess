# Test 1 feedback implementation

Updated September 27, 2026. Reviewed all three PDF pages and their embedded screenshots. This update builds on the previously deployed task-card redesign.

| Feedback | Implementation |
| --- | --- |
| Course confirmation jumps to top | Stable course-card anchors preserve the selected catalog/filter URL and return to the added course. |
| State/program filters conflict | One explicit catalog selector replaces competing state and reference selectors. Changing catalog clears incompatible secondary filters; legacy URLs remain supported. |
| Apply filters too far down | Apply/reset controls appear near the top; less-used filters are disclosed separately. |
| Duplicate and corrupted course titles | Equivalent title spellings are grouped with source listings. Distinct levels/years remain separate. Suspect paragraph-length imports are excluded from searches and new additions; saved IDs remain accessible with a verification label. |
| Janky/cramped course selection | Wider responsive result area, 30 results per page, shorter cards, clearer scope and coverage, stable confirmation position, and reduced filter clutter. |
| Missing local English, Health, Fitness | Added nine sourced Forsyth entries, including standard/honors English and Health/Personal Fitness. Source/year notes and official links are available on detail pages. |
| Duplicate four-year-plan links | Suppressed the second link when the contextual Back link already goes there. |
| Source labels and AP/IB duplicates | Visible source listings and grouped equivalent names; variants and legacy references preserved. Source location is not labeled as proof of state exclusivity. |
| Empty college selector | College search is visible above the course form, with numbered search/select steps, clearer optional-selection wording, and retry feedback. |
| Missing In progress course status | Added to college/dual and high-school entry; college editing and term-load summaries handle it consistently. |
| Subtasks hard to find; task progression page | Task titles and menus open a dedicated task page. An accessible numbered trail supports completing/reopening each step, with progress, adding subtasks, and splitting work blocks. |
| Expired actions show confusing errors | Expired-session redirects explain that the attempted action was not saved. Invalid/expired forms have dashboard/sign-in recovery. |
| Long task explanations | Previously deployed redesign keeps explanations inside task options; main cards stay concise. |
| Mobile due dates blend in | Queue deadlines now have their own emphasized line, matching the recommendation card's hierarchy. |
| Flexibility for breaks | Optional break allowance is stored separately from focused-work estimates, shown as a combined planning allowance on task details, copied to recurring tasks, and included in export. It does not change deadlines or automatically count breaks as worked time. |
| Extend time fails after host sleeps | Extension checks response status/content and redirects, uses a timeout, restores retry controls, and provides sign-in recovery. Failed requests leave the page draft intact. |
| Dual courses missing from task selection | A full saved-course select replaces reliance on browser datalist suggestions; custom subjects remain available. Server submissions honor the chosen saved course. |

## Source limitation

Quarantined imports have not been guessed or silently reassigned. Their original sources must be checked before those individual records return to search. Catalogs remain partial where their sources are partial. [Catalog quality notes](course-catalog-quality.md) document verified additions and the audit command for affected IDs.

## Verification

Automated checks cover course status and saved-course selection, break allowance persistence/validation, completing and reopening steps, task ownership, catalog grouping/quarantine, stable add-course returns, and expired-session messaging. Browser checks cover college search, course return anchors, the saved-course picker, step actions, session failure/recovery, and responsive layouts. Final run results are reported with the release.
