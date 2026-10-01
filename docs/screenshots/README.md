# StudentSuccess screenshot gallery

[Back to the project README](../../README.md)

Refreshed **September 30, 2026** from the current application running locally. All courses, tasks, and history shown are synthetic demonstration data; no production account or private credentials are included. Desktop images are **1440 x 960 (3:2)**, and phone images are **390 x 844**. These are viewport captures, so content below the fold remains available in the application.

## Landing page

The notebook-style entry point with account creation and the interactive tutorial.

[![Landing page](landing.png)](landing.png)

## Dashboard

The recommended next task, clear actions, and supporting planning summaries.

[![Dashboard](dashboard.png)](dashboard.png)

## Task queue

Prioritized assignments with task menus and links from subtasks to their parent project.

[![Task queue](tasks.png)](tasks.png)

## Project steps

A larger chemistry assignment broken into smaller steps with progress.

[![Project steps](subtasks.png)](subtasks.png)

## High school course explorer

Reference courses and comparison controls; coverage varies by catalog.

[![High school course explorer](courses.png)](courses.png)

## Integrated dual enrollment

College courses from two institutions within the high school course workspace.

[![Integrated dual enrollment](dual-enrollment.png)](dual-enrollment.png)

## Course comparison

Compare prerequisites, workload labels, and course characteristics.

[![Course comparison](comparison.png)](comparison.png)

## Four-year plan

High school planning across grades 9-12.

[![Four-year plan](four-year-plan.png)](four-year-plan.png)

## College term planning

Term courses, credits, and study workload across institutions.

[![College term planning](college.png)](college.png)

## Calendar tools

One-way Google Calendar deadline links and calendar-file export/import guidance.

[![Calendar tools](calendar.png)](calendar.png)

## Personalization

Academic, display, accessibility, and planning preferences.

[![Personalization](settings.png)](settings.png)

## Interactive tutorial

A guided practice workspace using real site controls.

[![Interactive tutorial](tutorial.png)](tutorial.png)

## Dark appearance

The landing page using the dark theme.

[![Dark appearance](landing-dark.png)](landing-dark.png)

## Mobile landing page

The public entry point at a phone viewport.

[![Mobile landing page](landing-mobile.png)](landing-mobile.png)

## Mobile dashboard

The planning workspace at a phone viewport.

[![Mobile dashboard](mobile-dashboard.png)](mobile-dashboard.png)

## Recreate the gallery

Install project dependencies, Playwright, and Google Chrome, then run:

~~~bash
python scripts/capture_project_media.py
~~~

The script creates a disposable in-memory database and writes these images. It never accesses the production database. Generated sample history illustrates features; it is not evidence of measured student outcomes.
