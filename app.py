from pathlib import Path

from flask import Flask

from config import config
from extensions import db
from routes.main_routes import main_bp
from routes.profile_routes import profile_bp
from routes.task_routes import task_bp


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(config)

    if test_config is not None:
        app.config.update(test_config)

    instance_dir = Path(app.instance_path)
    instance_dir.mkdir(parents=True, exist_ok=True)

    db.init_app(app)

    app.register_blueprint(main_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(task_bp)

    with app.app_context():
        from models import StudentProfile, Task

        db.create_all()

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
