from pathlib import Path
from flask import Flask
from config import config
from extensions import db
from routes.main_routes import main_bp
from routes.profile_routes import profile_bp


def create_app():
    app = Flask(__name__)

    # Load settings from config.py.
    app.config.from_object(config)

    # Make sure the instance folder exists before SQLite tries to use it.
    instance_dir = Path(app.instance_path)
    instance_dir.mkdir(parents=True, exist_ok=True)

    # Ensure the configured database path is inside the writable instance directory.
    if app.config.get("SQLALCHEMY_DATABASE_URI", "").startswith("sqlite:///"):
        db_uri = app.config["SQLALCHEMY_DATABASE_URI"]
        if not db_uri.startswith("sqlite://"):
            raise ValueError("Invalid database URI configuration")

    # Connect the shared SQLAlchemy object to this Flask app.
    db.init_app(app)

    # Keep the existing dashboard routes working.
    app.register_blueprint(main_bp)
    app.register_blueprint(profile_bp)

    # Register the model, then create any missing database tables.
    with app.app_context():
        from models import StudentProfile
        db.create_all()

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)