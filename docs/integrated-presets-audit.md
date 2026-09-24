# Integrated presets and mobile audit

## Already satisfied; preserved
- Stable priority ordering, completed tasks, parent tasks/subtasks, long minute estimates.
- On-time start metrics, secondary graphs/explanations, progressive task entry.
- Notebook texture/depth, keyboard focus, reduced motion and accessibility themes.
- Institution directory, per-course college association and account-scoped edits/exports.

## Partial features completed
- Dual enrollment now uses the high-school course selector, including lookup, entry,
  saved cards, edits, grade placement and assignments. Old term links redirect there.
- Mobile gutters, recommended-action hierarchy, queue options and comparison controls
  were adjusted after screenshots. Comparison rows stack without a wide table.
- Removed the landing page's horizontal overflow mask; actual bounds are audited.

## New
- College program, current term, personal credit target and course requirement categories.
- Planned-term totals with missing-credit disclosure; presets retain each other's data.
- Inline college lookup preserves drafts and has a no-JavaScript GET fallback.

## Deferred / coverage limits
- User-authored state databases have not been created; existing directory is retained.
- Individual college offerings remain student-entered, with no transfer/eligibility claims.
- Course-task grouping still uses normalized names; institution-specific enrollment IDs
  remain a future migration, not an assertion of this update.

## Validation
Baseline and final responsive bounds audits each covered 213 page/width combinations,
including 320, 375, 390, 430 and intermediate/desktop widths, disclosures/dialogs, plus
200% text in dark/high-contrast themes. Neither reported bounds or JavaScript failures.
Screenshots revealed hierarchy/gutter issues that geometric checks alone did not catch.
The integrated workflow additionally exercises lookup draft retention, creation, editing,
no-JavaScript selection, keyboard skip navigation and control bounds.
