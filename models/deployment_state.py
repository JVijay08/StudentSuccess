from extensions import db


class DeploymentState(db.Model):
    __tablename__ = "deployment_state"

    id = db.Column(db.Integer, primary_key=True, default=1)
    commit_sha = db.Column(db.String(64), nullable=False)