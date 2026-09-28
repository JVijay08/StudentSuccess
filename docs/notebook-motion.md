# Notebook motion

This follows the StudentSuccess animation brief after the feedback release
`31d8296`. Native forms, server validation, recommendation rules, and saved data
remain responsible for the actual result. No animation library was added.

## Implemented

- Starting a task draws a short blue underline and announces the confirmed state.
- Successful completion emphasizes the next recommendation and completed count.
- Visible task/course rows can settle across native navigation using cross-document
  view transitions. Movement is short; large position changes are not interpolated.
  Browsers without that API receive a small post-navigation settle instead.
- Created task steps receive a small arrival effect after the returned page confirms
  their existence. Rejected submissions never receive success feedback.
- Native disclosures animate their height, retain keyboard semantics, and handle
  rapid reversal. Task overflow menus use a small reveal with existing focus/Escape
  handling intact.
- Course saves highlight the confirmed selection and its destination year/term when
  visible. Comparison selection reveals the tray and count; an empty tray hides.
- Successful settings saves briefly show `Saved ✓`. Changing Reduce motion takes
  effect immediately. The operating-system preference also disables effects.
- Desktop navigation gains a short active underline. Books and Updates date groups
  settle once when visible. Touch screens omit these decorative reveals and lifts.
- Existing button press/depth and reminder feedback are reused.

## Boundaries

Metrics remain exact rather than counting through misleading intermediate values.
The graph-paper background stays static. There are no loops, pulsing deadlines,
parallax, mass card staggers, or delays before navigation. Long update searches
emphasize the result count rather than animating hundreds of hidden records.
Server-rendered removals use brief departure/remaining-row transitions where
supported, not a simulated pre-save deletion. Academic presets keep their native
control and confirmed saved-state feedback rather than adding new tabs.

Transient session storage contains action types, internal/public course IDs, route
pathnames, timestamps, and bounded viewport geometry only. It stores no task text,
form drafts, or credentials. Records expire after two minutes; blocked storage or
missing animation APIs do not prevent task actions.

## Verification

`scripts/check_notebook_motion.py` covers confirmed actions, rejected completion,
keyboard use, immediate/app and OS reduced motion, comparison selection, course
saves, blocked storage/missing Web Animations API, and 24 page/width combinations
at 320, 375, 390, and 430 pixels. The existing feedback and task-card browser checks
also cover the underlying workflows.

Cross-document transitions are progressive enhancement. See the
[Chrome cross-document guide](https://developer.chrome.com/docs/web-platform/view-transitions/cross-document)
and [MDN pagereveal documentation](https://developer.mozilla.org/en-US/docs/Web/API/Window/pagereveal_event).
Early head listeners skip transitions when the deferred engine is not ready;
content and navigation are never held waiting for an animation download.
