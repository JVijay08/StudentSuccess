# StudentSuccess

> **Public prototype:** StudentSuccess is still under development and is not ready to store real student information. Use fictional data only when exploring the live demo.

StudentSuccess is a focused Flask application for procrastination-aware academic planning. It is designed for high school students who know what work they need to complete but have trouble starting before deadline pressure creates urgency.

## What problem does it address?

The project aims to help a student choose what to work on now, compare planned and actual start times, recognize repeated delay patterns, and eventually build more realistic schedules from real behavior.

## Implemented

- Flask application factory and Blueprints
- Student onboarding and editable profile stored in SQLite
- A profile-aware dashboard with a real recommended next task
- A catalog-aware course explorer with state selection, national reference courses, imported state catalogs, AP/IB program catalogs, and a Forsyth County local catalog
- Course explorer with search, filters, details, comparison, prerequisites, and four-year planning
- Task creation, planned/actual start tracking, completion, and explainable rule-based risk
- Automated route, task, risk, and course-service tests

Machine learning, AI assistance, optimization, and calendar integration are not implemented. State selection is available for all 50 states, with imported data for Alabama, Arkansas, Florida, Georgia/Forsyth, Illinois, Indiana, Iowa, Kansas, Kentucky, Louisiana, Michigan, Minnesota, Mississippi, Missouri, Nebraska, North Carolina, North Dakota, Ohio, South Carolina, South Dakota, Tennessee, Virginia, West Virginia, and Wisconsin. Coverage varies by supplied source. The national and AP/IB catalogs are planning references, not universal graduation or placement authorities.

## Technology

- Python and Flask
- Flask-SQLAlchemy with SQLite locally and PostgreSQL in persistent deployments
- HTML and CSS
- pytest

## Local setup

1. Create and activate a virtual environment.
2. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

3. Start the development server:

   ```powershell
   python app.py
   ```

4. Open `http://127.0.0.1:5000`.

The app creates missing tables in `instance/studentsuccess.db`. This local database is ignored by Git.

To run tests:

```powershell
python -m pytest
```

## Public demo launch

The app is configured for Render with `render.yaml`. Use a Render **Web Service**
with the Free compute plan, then confirm these commands if entering the service
manually:

```text
Build: pip install -r requirements.txt
Start: gunicorn app:app
```

Before sharing the link, set `SECRET_KEY` in the host environment and use only
fictional demo data. The included `scripts/seed_test_login.py` creates a
populated local test account for screenshots and walkthroughs; it is not a
production account and should not be used with real student information.

The Render blueprint disables `DEMO_RESET_ON_DEPLOY` and connects the web
service to the managed `studentsuccess-db` PostgreSQL database, so deployments
do not delete accounts and service restarts do not lose them. If the service was
created before this database was added to `render.yaml`, apply the blueprint
update in Render and confirm that `DATABASE_URL` is linked to
`studentsuccess-db`. Without that connection, the app falls back to SQLite,
whose filesystem is temporary on Render.

The `/health` endpoint returns `{"status": "ok"}` for deployment checks.

Render's free service sleeps after inactivity and its local SQLite filesystem is
temporary, so this deployment is suitable for a portfolio demo rather than
reliable long-term data storage.

## Project structure

```text
StudentSuccess/
|-- app.py
|-- config.py
|-- extensions.py
|-- data/
|   `-- courses.json
|-- docs/
|-- instance/
|-- models/
|-- routes/
|-- services/
|-- static/css/
|-- templates/
`-- tests/
```

- `models/` defines persisted application data.
- `routes/` handles browser requests through Flask Blueprints.
- `services/` contains reusable logic and catalog access.
- `templates/` and `static/` provide the server-rendered interface.
- `data/` contains the curated course catalog.

## Short roadmap

The next step is to summarize planned-versus-actual start delays by task type and subject. Adaptive scheduling, optimization, or machine learning should only be considered after useful real behavior data exists.
