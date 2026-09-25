from pathlib import Path
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from flask import Flask, render_template, session, request
from sqlalchemy import inspect, text

from config import config
from extensions import db
from routes.auth_routes import auth_bp
from routes.access_routes import access_bp
from services.access_service import csrf_token
from routes.course_routes import course_bp
from routes.main_routes import main_bp
from routes.profile_routes import profile_bp
from routes.settings_routes import settings_bp
from routes.task_routes import task_bp


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(config)

    if test_config is not None:
        app.config.update(test_config)

    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY must be set before starting the application.")

    instance_dir = Path(app.instance_path)
    instance_dir.mkdir(parents=True, exist_ok=True)

    db.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(access_bp)
    from routes.account_routes import account_bp
    from services.email_accounts import ready
    app.register_blueprint(account_bp)
    app.jinja_env.globals['email_accounts_ready'] = ready
    app.jinja_env.globals["access_csrf_token"] = csrf_token
    app.register_blueprint(course_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(settings_bp)
    from routes.term_routes import term_bp
    app.register_blueprint(term_bp)
    from routes.college_routes import college_bp
    app.register_blueprint(college_bp)
    from services.college_directory import institution
    app.jinja_env.globals['college_by_id'] = institution
    app.register_blueprint(task_bp)
    from services.task_policy import MAX_TASK_MINUTES
    app.jinja_env.globals["MAX_TASK_MINUTES"] = MAX_TASK_MINUTES

    @app.template_filter("planner_time")
    def planner_time(value):
        if value is None:
            return "Not recorded"
        from models import UserSettings
        from services.datetime_util import format_local
        preferences = UserSettings.query.filter_by(user_id=session.get("user_id")).first()
        return format_local(value, preferences.timezone_name if preferences else "America/New_York",
                            preferences.time_format if preferences else "12-hour",
                            preferences.date_format if preferences else "month-first")
    from services.navigation import template_context
    app.context_processor(template_context)

    @app.context_processor
    def inject_ui_settings():
        from models import UserSettings
        from services.settings_service import default_settings

        user_id = session.get("user_id")
        preferences = (
            UserSettings.query.filter_by(user_id=user_id).first()
            if user_id is not None
            else None
        )
        settings = preferences or default_settings()
        now = datetime.now(timezone.utc)
        local_now = now.astimezone(ZoneInfo(settings.timezone_name or "America/New_York"))
        return {
            "ui_settings": settings,
            "clock_iso": now.isoformat(),
            "clock_display": (
                f"{local_now.month}/{local_now.day}/{local_now.year} "
                f"{local_now.hour % 12 or 12}:{local_now.minute:02d}"
                f"{'AM' if local_now.hour < 12 else 'PM'}"
            ),
        }

    @app.after_request
    def add_security_headers(response):
        if request.path.startswith(("/access/", "/account/")) or session.get("user_id") or request.path in ("/login", "/register"):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Referrer-Policy"] = "no-referrer"
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        return response

    @app.get("/time")
    def current_time():
        return {"utc": datetime.now(timezone.utc).isoformat()}, 200, {"Cache-Control": "no-store"}

    @app.errorhandler(404)
    def page_not_found(_error):
        return render_template("error.html", status_code=404, heading="That page is not here.", message="The link may be outdated, or the item may have been removed."), 404

    @app.errorhandler(500)
    def internal_error(_error):
        db.session.rollback()
        return render_template("error.html", status_code=500, heading="StudentSuccess hit a snag.", message="Your saved information is still safe. Try the page again in a moment."), 500

    with app.app_context():
        from models import StudentProfile, Task, User

        db.create_all()
        _migrate_feedback_columns()
        db.session.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_verified_email ON users(email)"))
        db.session.commit()
        _migrate_planned_course_catalog_column()
        _migrate_task_reminder_columns()
        _migrate_task_actual_minutes_column()
        _reset_demo_accounts_for_deployment()

    return app


def _migrate_feedback_columns():
    """Additive migration; existing tasks, history, and preferences are retained."""
    additions = {
        "users": {"email": "VARCHAR(254)", "auth_version": "INTEGER NOT NULL DEFAULT 0"},
        "tasks": {"parent_task_id": "INTEGER REFERENCES tasks(id)", "external_uid": "VARCHAR(255)"},
        "user_settings": {"academic_context": "VARCHAR(20) NOT NULL DEFAULT 'high_school'", "institution_id": "VARCHAR(12)",
            "college_program": "VARCHAR(120) NOT NULL DEFAULT ''", "college_term": "VARCHAR(60) NOT NULL DEFAULT ''", "term_credit_goal": "FLOAT"},
        "term_courses": {
            "institution_id": "VARCHAR(12)", "enrollment_type": "VARCHAR(20) NOT NULL DEFAULT 'college'",
            "school_year": "INTEGER", "status": "VARCHAR(20) NOT NULL DEFAULT 'planned'",
            "course_code": "VARCHAR(32) NOT NULL DEFAULT ''", "credits": "FLOAT",
            "description": "TEXT NOT NULL DEFAULT ''", "catalog_url": "VARCHAR(500) NOT NULL DEFAULT ''",
            "requirement_area": "VARCHAR(20) NOT NULL DEFAULT 'unspecified'",
        },
    }
    for table, fields in additions.items():
        if table not in inspect(db.engine).get_table_names():
            continue
        columns = {c["name"] for c in inspect(db.engine).get_columns(table)}
        for name, definition in fields.items():
            if name not in columns:
                db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {definition}"))
    db.session.commit()


def _migrate_planned_course_catalog_column():
    inspector = inspect(db.engine)
    if "planned_courses" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("planned_courses")}
    if "catalog_id" not in columns:
        db.session.execute(
            text(
                "ALTER TABLE planned_courses "
                "ADD COLUMN catalog_id VARCHAR(40) NOT NULL DEFAULT 'ga'"
            )
        )
        db.session.commit()

    # Preserve existing plans while retiring the location-specific public identifier.
    db.session.execute(
        text("UPDATE planned_courses SET catalog_id = :new WHERE catalog_id = :old"),
        {"new": "ga", "old": "forsyth-ga"},
    )
    db.session.commit()


def _migrate_task_reminder_columns():
    inspector = inspect(db.engine)
    if "tasks" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("tasks")}
    if "reminder_snoozed_until" not in columns:
        db.session.execute(
            text("ALTER TABLE tasks ADD COLUMN reminder_snoozed_until TIMESTAMP")
        )
        db.session.commit()
    if "reminder_enabled" not in columns:
        db.session.execute(
            text("ALTER TABLE tasks ADD COLUMN reminder_enabled BOOLEAN NOT NULL DEFAULT TRUE")
        )
        db.session.commit()


def _migrate_task_actual_minutes_column():
    inspector = inspect(db.engine)
    if "tasks" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("tasks")}
    if "actual_minutes" not in columns:
        db.session.execute(text("ALTER TABLE tasks ADD COLUMN actual_minutes INTEGER"))
        db.session.commit()


def _reset_demo_accounts_for_deployment():
    if os.environ.get("DEMO_RESET_ON_DEPLOY") != "1":
        return

    commit_sha = os.environ.get("RENDER_GIT_COMMIT")
    if not commit_sha:
        return

    from models import DeploymentState, User

    state = db.session.get(DeploymentState, 1)
    if state is not None and state.commit_sha == commit_sha:
        return

    for user in User.query.all():
        db.session.delete(user)

    if state is None:
        state = DeploymentState(id=1, commit_sha=commit_sha)
        db.session.add(state)
    else:
        state.commit_sha = commit_sha

    db.session.commit()


app = create_app()


@app.get("/health")
def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(
        debug=os.environ.get("FLASK_DEBUG", "0") == "1",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "5000")),
    )
