# StudentSuccess screenshots

[Back to the project README](../../README.md)

Captured September 17, 2026 from the current application running locally with isolated fictional demo data. Desktop images are 1440 pixels wide; mobile images are 390 pixels wide. These captures show the design deployed at [StudentSuccess](https://studentsuccess.onrender.com/). Open any image at full size for detail.

Still images do not show motion: try the landing-page example on the live site to see the paper tilt, note arrangement, and paper-plane animation.

## Landing page

Graph paper, layered notes, a folded-paper plane, and entry points for the demo and private planners.

[![Landing page: Graph paper, layered notes, a folded-paper plane, and entry points for the demo and private planners.](landing.png)](landing.png)

## Interactive starting plan

The example notes settle into a starting plan. Choose a problem set, essay, or exam, then check the first-step box to see the paper-plane animation. Pointer tilt and motion respect reduced-motion preferences.

[![Interactive starting plan: The example notes settle into a starting plan. Choose a problem set, essay, or exam, then check the first-step box to see the paper-plane animation. Pointer tilt and motion respect reduced-motion preferences.](landing-arranged.png)](landing-arranged.png)

## Dashboard

One prominent next task with a direct Start button, expandable reasons, and separate summary cards. Desktop navigation and logout remain reachable while scrolling.

[![Dashboard: One prominent next task with a direct Start button, expandable reasons, and separate summary cards. Desktop navigation and logout remain reachable while scrolling.](dashboard.png)](dashboard.png)

## Task planner

Task entry and fictional assignments with planned starts, deadlines, start controls, and completion controls.

[![Task planner: Task entry and fictional assignments with planned starts, deadlines, start controls, and completion controls.](tasks.png)](tasks.png)

## Course explorer

National reference courses with filters, workload estimates, and comparison controls. Reference coverage varies by catalog.

[![Course explorer: National reference courses with filters, workload estimates, and comparison controls. Reference coverage varies by catalog.](courses.png)](courses.png)

## Course comparison

AP Chemistry and AP Biology references shown side by side. Up to three courses can be compared.

[![Course comparison: AP Chemistry and AP Biology references shown side by side. Up to three courses can be compared.](comparison.png)](comparison.png)

## Four-year plan

A timeline for grades 9 through 12. This fictional demo has five courses in grade 11; the other years are empty.

[![Four-year plan: A timeline for grades 9 through 12. This fictional demo has five courses in grade 11; the other years are empty.](four-year-plan.png)](four-year-plan.png)

## Settings

Two columns on wide screens, a sticky Save all settings button, and appearance, focus, task-planning, reminder, date/time, and account controls.

[![Settings: Two columns on wide screens, a sticky Save all settings button, and appearance, focus, task-planning, reminder, date/time, and account controls.](settings.png)](settings.png)

## Mobile landing page

The interactive notebook adapts to a narrow screen with stacked content and touch-friendly controls.

[![Mobile landing page: The interactive notebook adapts to a narrow screen with stacked content and touch-friendly controls.](landing-mobile.png)](landing-mobile.png)

## Mobile dashboard

Full mobile navigation, logout, clock, task recommendations, summary cards, and expandable supporting information.

[![Mobile dashboard: Full mobile navigation, logout, clock, task recommendations, summary cards, and expandable supporting information.](mobile-dashboard.png)](mobile-dashboard.png)

## Dark appearance

The same interactive example in dark appearance. High-contrast appearance and reduced motion are also available.

[![Dark appearance: The same interactive example in dark appearance. High-contrast appearance and reduced motion are also available.](landing-dark.png)](landing-dark.png)

## Recreate the captures

Run `python scripts/capture_fieldnotes.py` with Playwright and Chrome installed. The script uses an in-memory database, writes to `output/fieldnotes-screenshots/`, and checks the example interaction, reduced motion, settings persistence, task starts, and logout. It does not modify production accounts.
