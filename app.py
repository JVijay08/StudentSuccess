from pathlib import Path
import os

from flask import Flask, render_template, session
from sqlalchemy import inspect, text

from config import config
from extensions import db
from routes.auth_routes import auth_bp
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
    app.register_blueprint(course_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(task_bp)

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
        return {"ui_settings": preferences or default_settings()}

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        return response

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
        _migrate_planned_course_catalog_column()
        _migrate_task_reminder_columns()
        _migrate_task_actual_minutes_column()
        _reset_demo_accounts_for_deployment()

    return app


def _migrate_planned_course_catalog_column():
    inspector = inspect(db.engine)
    if "planned_courses" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("planned_courses")}
    if "catalog_id" not in columns:
        db.session.execute(
            text(
                "ALTER TABLE planned_courses "
                "ADD COLUMN catalog_id VARCHAR(40) NOT NULL DEFAULT 'forsyth-ga'"
            )
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
