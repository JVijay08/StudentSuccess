# Architecture

StudentSuccess is a Flask application with server-rendered pages and a separate browser-only workspace.

```text
Browser request
  -> Flask Blueprint
  -> application service and/or SQLAlchemy model
  -> account database or JSON reference catalog
  -> Jinja template response
```

## Application startup

`app.py` creates the application, loads `config.py`, initializes the shared database extension, registers Blueprints, and sets response headers and error handlers. Startup creates missing tables and runs selected schema migrations. `extensions.py` provides the shared SQLAlchemy object.

`DATABASE_URL` selects the account database. Local development falls back to SQLite in `instance/studentsuccess.db`; the Render blueprint links PostgreSQL. `/health` reports application availability without querying the database.

## Responsibilities

- `models/` stores users, profiles, tasks and subtasks, high-school plans, college term courses, preferences, and deployment state. Legacy credential tables remain for transfer compatibility.
- `routes/` validates browser requests and coordinates authentication, planner access, dashboard data, tasks, courses, profiles, and settings.
- `services/` implements reusable account logic, rule-based scoring, history-aware suggestions, timing summaries, recurrence, settings, and catalog access.
- `templates/` contains Jinja pages and shared fragments.
- `static/` contains CSS, JavaScript, illustrations, and social-preview assets.
- `data/` contains versioned course reference catalogs. Account course selections store both course and catalog identifiers.
- `tests/` covers application routes and service behavior.
- `instance/` holds local runtime data and must not be included in source exports.

## Account and browser workspaces

Nickname-style username/password accounts use the server database and must complete onboarding. Private codes are retired from daily sign-in; a one-time transfer preserves legacy plans. The interactive tutorial creates an isolated sample account and removes it on exit. See [privacy notes](privacy_notes.md) for credential handling and account controls.

The optional `/planner` workspace stores its plan in browser localStorage. It downloads a public catalog bundle from `/planner/catalogs.json`, then performs catalog searches and selections locally. Browser plans and server accounts do not automatically synchronize.

## Recommendations

Task priority starts with explicit deadline, effort, difficulty, interest, and start-status rules. History-aware suggestions can add a small bonus based on recorded starting patterns. The scorer returns the same point contributions used by the dashboard explanations. Each recommendation has a short reason; the leading task is compared with the runner-up, including explicit ties. History notes show the number of completed tasks with both start timestamps in the same group and distinguish insufficient history, no adjustment, and an applied bonus. An expandable breakdown shows all contributing points. These services do not use machine learning or an external AI service.


## Interface and screenshot checks

Shared templates load the notebook styles, responsive layout, accessibility controls,
and purposeful motion. JavaScript enhances server-rendered forms and navigation;
motion respects system and application reduced-motion preferences.

scripts/capture_project_media.py refreshes the repository gallery from an isolated
in-memory database with synthetic tasks, courses, and history. Dedicated
scripts/check_*.py scripts validate interactions and responsive layouts.

## Scheduling, Calendar, and tutorial

Task rescheduling is a task-menu action with a bounded undo window. New recurring
tasks create a finite set of occurrences through an inclusive end date. Bulk deletion
requires a reviewed selection, including project descendants. Calendar links and ICS
files copy deadlines; no OAuth tokens or automatic synchronization are used.

The tutorial maintains an isolated practice session, persists guide progress, and
restores the original account on exit when its session remains valid. Public SEO
metadata and sitemap entries cover public pages; account pages are marked noindex.
See [tutorial and Calendar details](tutorial-and-calendar.md) and [SEO](seo.md).
