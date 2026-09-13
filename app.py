from pathlib import Path
import os

from flask import Flask
from sqlalchemy import inspect, text

from config import config
from extensions import db
from routes.auth_routes import auth_bp
from routes.course_routes import course_bp
from routes.main_routes import main_bp
from routes.profile_routes import profile_bp
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
    app.register_blueprint(task_bp)

    with app.app_context():
        from models import StudentProfile, Task, User

        db.create_all()
        _migrate_planned_course_catalog_column()

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
