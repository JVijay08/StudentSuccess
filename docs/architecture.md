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

- `models/` stores users, access-code digests, profiles, tasks, planned courses, preferences, and deployment state.
- `routes/` validates browser requests and coordinates authentication, planner access, dashboard data, tasks, courses, profiles, and settings.
- `services/` implements reusable account logic, rule-based scoring, history-aware suggestions, timing summaries, recurrence, settings, and catalog access.
- `templates/` contains Jinja pages and shared fragments.
- `static/` contains CSS, JavaScript, illustrations, and social-preview assets.
- `data/` contains versioned course reference catalogs. Account course selections store both course and catalog identifiers.
- `tests/` covers application routes and service behavior.
- `instance/` holds local runtime data and must not be included in source exports.

## Account and browser workspaces

Private-code planners and fictional demo workspaces use the server database. Legacy username/password accounts remain supported. Private-code users receive sample planning defaults rather than personal-profile onboarding. See [privacy notes](privacy_notes.md) for credential handling and account controls.

The optional `/planner` workspace stores its plan in browser localStorage. It downloads a public catalog bundle from `/planner/catalogs.json`, then performs catalog searches and selections locally. Browser plans and server accounts do not automatically synchronize.

## Recommendations

Task priority starts with explicit deadline, effort, difficulty, interest, and start-status rules. History-aware suggestions can add a small bonus based on recorded starting patterns. The interface presents reasons alongside recommendations. These services do not use machine learning or an external AI service.


## Interface and screenshot checks

The shared template head loads the base styles, accessibility and mobile rules,
then the notebook (`fieldnotes.css`) and paper-depth (`depth.css`) layers.
`fieldnotes.js` handles the fictional landing-page exercise; it saves no user data.
`depth.js` adds pointer-responsive perspective and one-time entrance effects,
respecting operating-system and application reduced-motion preferences.
`compact.js` keeps supporting sections expandable on small screens.

The dashboard starts tasks through the existing authenticated POST route.
Settings remains one form: its sticky Save button submits all sections, including
those collapsed on mobile. The desktop sidebar stays within the viewport so
navigation and logout remain reachable.

`scripts/capture_fieldnotes.py` runs against an isolated in-memory database and
captures desktop, mobile, and alternate-theme views. It also checks keyboard
interaction, reduced motion, settings persistence, task starts, and logout.
`scripts/check_mobile_layout.py --check` audits page widths and enlarged text.
