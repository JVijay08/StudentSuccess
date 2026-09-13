# Architecture

StudentSuccess uses a small Flask app-factory architecture:

```text
Browser
  -> Flask Blueprint route
  -> model and/or service
  -> SQLite database or JSON course catalog
  -> Jinja template response
```

## Application entry points

`app.py` creates and configures the Flask application, initializes SQLAlchemy, registers Blueprints, and creates tables that do not yet exist. `config.py` holds the local database configuration. `extensions.py` owns the shared SQLAlchemy object so models and the app factory can import it without a circular dependency.

## Directory responsibilities

- `models/`: SQLAlchemy models for information that must persist. `StudentProfile` and `Task` are the current models.
- `routes/`: Blueprints that validate requests, coordinate models or services, and render responses. Main routes own the dashboard, profile routes own onboarding, task routes own task creation and status changes, and course routes own catalog exploration and planning.
- `services/`: reusable application logic that does not belong in a route or model. The course service reads and filters the JSON catalog. The procrastination service calculates transparent task risk from visible rules.
- `templates/`: Jinja HTML returned to the browser.
- `static/`: CSS used by the templates.
- `data/`: curated, version-controlled reference data. It is not a substitute for the SQLite application database. Course records remain in JSON; student selections are stored as `PlannedCourse` rows keyed by stable `course_id` values.
- `tests/`: pytest coverage for routes and services.
- `instance/`: local runtime data. The SQLite database is ignored and must not be committed.

The code intentionally avoids speculative layers. A new module should be added only when it contains working behavior.
