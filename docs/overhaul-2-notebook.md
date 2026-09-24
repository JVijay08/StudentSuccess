# Overhaul 2.0: the dimensional notebook

September 23, 2026. This revision restores the notebook identity while retaining the task-first layout and functional changes from overhaul 1.

## What changed

- Graph paper is back as a low-contrast background pattern. Reading surfaces stay opaque; high-contrast mode removes the texture.
- Paper surfaces use consistent, layered shadows with light coming from the top left. The landing preview has layered page edges, a notebook spine, and an index tab. Illustrations add character without blocking the workflow.
- Raised primary buttons have distinct hover, pressed, disabled, and keyboard-focus states. Secondary actions and destructive actions use separate treatments. Static preview controls no longer pretend to be clickable: the preview opens the real demo.
- Shared action-row layouts fix cramped or touching links/buttons. Controls wrap, input labels remain visible, and long text can reflow. Settings has a sticky Save bar and a two-column desktop layout; mobile sections remain expandable.
- Brief disclosure and status animations communicate changes. There are no looping decorations, scroll hijacking, or pointer-follow effects. Both system and saved reduced-motion preferences suppress motion.
- The full dashboard separates the main recommendation from upcoming work. The queue retains stable urgency ordering and shows readable status/urgency badges. Course groups with active assignments appear before the optional list of empty courses.
- A new By course view shows course/subject -> assignment -> subtask, with progress and direct Start/Complete actions. Completed children remain in completed history. Course names from saved high-school plans and college terms appear as task-entry suggestions; both course-plan screens link to assignments. Browser-only planning also supports the grouped view.
- College term planning now puts saved courses first and connects each course to its assignments. Add-course forms can be opened by keyboard-friendly deep links.
- Timing leads with on-time starts. Early starts count as on time. Average and median lateness use max(0, actual start - planned start), so early starts cannot cancel late starts. Detailed charts retain the true signed early/late values. Projects do not double-count their children.

## Feedback coverage

| Feedback | Coverage |
| --- | --- |
| Queue feels jumbled | Deterministic priority order retained; urgency labels, separate course view, and empty-course disclosure improve scanning. |
| Completed-task section | Retained on both planners, with actual durations and reopen/undo actions. |
| On time instead of early averages | New on-time-first summary and nonnegative lateness calculations in both planners; signed history stays available. |
| Start-delay graphs and less clutter | Timing charts remain optional, with text equivalents and clear empty states. |
| Minute limit too low | Existing 10,080-minute estimate/actual limit retained and regression-tested. |
| College personalization | Manual college terms, course-first layout, and linked assignment grouping; existing academic-context preference retained. |
| Subtasks / broken-up work | Existing one-level subtasks, exact timed splitting, parent progress/completion/reopening retained; hierarchy now visible by course. |
| Flat, generic appearance | Graph paper, dimensional controls, layered paper, contextual illustration, purposeful motion. |
| Broken buttons, text, links | Shared action layouts, clearer control roles, wrapping, focus, contrast and clipping checks across representative pages. |

## Validation

- Full Python regression suite: 287 passed, including five new hierarchy/timing cases.
- Existing Chrome workflow checks: no JavaScript errors or horizontal overflow. Includes local course grouping, task/subtask persistence, start/complete/reopen, college terms, long estimates and work-block creation.
- `scripts/check_notebook_v2.py`: end-to-end course -> project -> subtask completion, retained navigation context, and prefilled/focused Add assignment flow. Checks desktop/mobile layouts, visible-control contrast and clipping, hover/focus, and reduced motion. Tests use a fresh isolated database, never a real user's workspace.
- Viewports: 320, 390, 768, and 1440 pixels. Dark/high-contrast preferences and 200% text checked on the principal workspace pages. Local screenshots/results are in `.test-overhaul-v2/`.
- Automated checks establish the tested behaviors and calculated contrast; they are not a full accessibility certification or a replacement for human usability testing.

## Remaining backlog / intentional limits

- Course grouping uses normalized course/subject names, not an institutional enrollment identifier. Reusing the same name in multiple terms shares its assignment group. Separate term-specific assignment identity remains a future enhancement. Task subject names retain their existing 80-character limit; longer catalog names use their first 80 characters in this view.
- College catalogs, degree audits, native apps, live calendar/LMS sync, and browser-to-account sync are not included in this visual revision.
- Retest the redesigned pages with students, including keyboard and assistive-technology users. Track any additional device-specific control/layout issues found in that testing.

## How the supplied articles informed the design

- [Josh W. Comeau: Designing Beautiful Shadows](https://www.joshwcomeau.com/css/designing-shadows/): a consistent light source, layered color-aware shadows, and different elevations for surfaces and controls.
- [NN/g: Flat-Design Best Practices](https://www.nngroup.com/articles/flat-design-best-practices/): recognizable controls, consistent clickable cues, and selective depth.
- [NN/g: The Role of Animation and Motion in UX](https://www.nngroup.com/articles/animation-purpose-ux/): short feedback and disclosure motion; no ambient distraction.
- [Smashing Magazine: How to Use Textures in Web Design](https://www.smashingmagazine.com/2011/10/whys-hows-textures-web-design/): texture establishes atmosphere and grouping while preserving readable content surfaces.
- [Smashing Magazine: Bringing Personality Back to the Web](https://shop.smashingmagazine.com/2018/06/bringing-personality-back-to-the-web/): notebook details and coherent visual character rather than generic interchangeable blocks.
