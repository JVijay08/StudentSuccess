# StudentSuccess

StudentSuccess is a focused Flask application for procrastination-aware academic planning. It is designed for high school students who know what work they need to complete but have trouble starting before deadline pressure creates urgency.

## What problem does it address?

The project aims to help a student choose what to work on now, compare planned and actual start times, recognize repeated delay patterns, and eventually build more realistic schedules from real behavior.

## Implemented today

- Flask application factory and Blueprints
- Student onboarding and editable profile stored in SQLite
- A profile-aware dashboard with a real recommended next task
- A curated 59-course JSON catalog
- Course lookup and filtering services
- Task creation, planned/actual start tracking, completion, and explainable rule-based risk
- Automated route, task, risk, and course-service tests

Machine learning, AI assistance, optimization, authentication, calendar integration, and a course-planning interface are not implemented.

## Technology

- Python and Flask
- Flask-SQLAlchemy with SQLite
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
