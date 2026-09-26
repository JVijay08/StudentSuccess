# Site-aware React Bits evaluation

StudentSuccess uses Flask, SQLAlchemy, Jinja, native HTML controls, plain JavaScript,
and CSS. There is no React runtime or Node build. The existing visual system uses
warm graph paper, blue primary actions, layered notebook surfaces, clear focus outlines,
and short animations that explain state changes. Mobile sections disclose secondary
controls on demand. Both OS and saved reduced-motion preferences are supported.

The main flow is `/login` or `/register`, mandatory `/onboarding`, then `/dashboard`,
`/tasks`, and high-school `/courses` or college `/terms`. Settings own reminder preferences;
college search already runs against the public institution directory. Those existing
features are the only selected integration points.

## Selection (shown before implementation)

| Component | Decision | Exact location | Rationale | Added dependencies |
| --- | --- | --- | --- | --- |
| CursorGrid | Skip | Landing hero considered | Static graph paper already supplies identity; pointer-following decoration adds distraction and little touch value. | None |
| ScrollStack | Skip | Landing feature cards considered | Keep ordinary scrolling and simultaneously readable cards. | None; no Lenis |
| BellToggle | Adapt | `/settings` > Reminders; `/onboarding` > How you like to work | One clearer on/off control for the existing in-app reminder preference. | None; native checkbox, SVG, CSS, Web Animations |
| CallChip | Adapt | `/courses?course_source=dual` and `/terms` > Add college course > Find a college by state or name | Actual lookup feedback and a visible, functional retry replace the existing status paragraph. | None; existing fetch, native SVG and CSS |
| FuseButton | Skip | Rescheduling and removal considered | Rescheduling already has an immediate save and a ten-minute undo; a delayed commit would change that model. | None |
| HoldButton | Skip | Deletion considered | Keep conventional confirmation without imposing a sustained gesture. | None |
| Shredder | Skip | Task lists considered | No dedicated nonessential list warrants a destruction metaphor. | None |
| SwipeRow | Skip | Task queue considered | Existing visible controls work across keyboard, pointer, touch and assistive technology. | None |
| FolderFloat | Skip | Workspace shortcuts considered | The existing menu is discoverable and stable; floating physics would hide navigation behind an unfamiliar interaction. | None; no Matter.js |

For overlapping list actions, existing visible row controls win over SwipeRow/Shredder.
For consequential actions, existing confirmation and rescheduling undo win over both
FuseButton and HoldButton. The workspace menu wins over FolderFloat. Neither proposed
background/scroll effect is selected. BellToggle and CallChip have separate jobs.

## Source review and adaptation

The combined brief did not contain the original prompt files. The official JS/CSS
registry implementations were inspected for the two selected components only:

- [BellToggle documentation](https://reactbits.dev/micro/bell-toggle) and [JS/CSS source](https://reactbits.dev/r/BellToggle-JS-CSS).
- [CallChip documentation](https://reactbits.dev/micro/call-chip) and [JS/CSS source](https://reactbits.dev/r/CallChip-JS-CSS).

These are native adaptations of their interaction patterns, not drop-in React components.
No upstream source or icon package is bundled; the production markup, SVGs, styles, and
JavaScript are written for this site's existing stack. No skipped component code is installed.

BellToggle's controlled state maps to the existing `reminders_enabled` checkbox and
server-rendered preference. The reusable Jinja macro accepts `enabled`, `help_id`,
`save_hint`, and optional `disabled`. It keeps a stable accessible name, visible checkbox,
textual On/Off state, normal form submission, and a 360 ms damped bell response only on
activation. Saving remains explicit, with nearby copy explaining when the choice applies.
There is no badge because no unread count exists; no email/push subscription is implied.
Reduced motion cancels/prevents the ring, including the current form's motion preference.
There is no initial-load or continuous bell animation, clipped label, or blur transition.

CallChip's states map to actual request lifecycle: idle, running, done, error. The result
count comes from the response. Empty results are a completed search, not an error. Retry
submits the same form using current filters. A 15-second timeout stops indefinite waiting;
newer requests cancel older requests and stale responses cannot overwrite newer results.
Failures retain both the course draft and selected institution. The status uses a polite,
atomic live region, and retry is a separate labeled button with standard focus behavior.
There is no guessed percentage, expected-duration animation, decorative shake, or timer.
Text wraps and control height grows at large text sizes. The original same-page GET lookup
and native reminder form work without JavaScript.

## Files and verification

- `templates/_reminder_toggle.html`, `static/js/reminder_toggle.js`, and `static/css/planner_controls.css`: reusable reminder control and shared scoped status styling.
- `templates/_college_finder.html` and `static/js/college_courses.js`: real lookup state, timeout and retry, preserving draft/selection and avoiding stale responses.
- Settings, onboarding, course and term templates load the selected adaptations only where used.
- Landing navigation's stale "Open with a code" label is corrected to "Sign in".
- `scripts/check_planner_controls.py`: persistence across both reminder forms, keyboard input, OS/form reduced motion, search success/error/empty/timeout/retry, draft preservation, no-JS fallback, mobile/desktop bounds and large-text themes.
- Existing settings, colleges, account/onboarding and route tests plus `scripts/check_college_planning.py` verify the underlying behavior remains intact.

No Python or JavaScript dependency changes. Tasks, deletion, rescheduling, navigation,
and the site-wide design system retain their existing interaction models.

Verified: 81 relevant backend tests passed. The new control browser check passed 56
viewport/state combinations with no layout or JavaScript errors; the existing college
planning browser workflow also passed. Keyboard focus after retry and empty results,
both reminder save paths, OS/form reduced motion, and no-JS fallbacks were exercised.
