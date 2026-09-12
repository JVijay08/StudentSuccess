from flask import Blueprint, redirect, render_template, url_for

from models import StudentProfile, Task
from services.procrastination_service import explain_procrastination_risk


main_bp = Blueprint("main", __name__)


@main_bp.get("/")
def home():
    return redirect(url_for("main.dashboard"))


@main_bp.get("/dashboard")
def dashboard():
    profile = StudentProfile.query.first()
    active_tasks = []
    recommended_task = None
    recommended_risk = None

    if profile is not None:
        active_tasks = (
            Task.query.filter(
                Task.student_profile_id == profile.id,
                Task.status != "completed",
            )
            .order_by(Task.due_at)
            .all()
        )
        if active_tasks:
            ranked_tasks = [
                (task, explain_procrastination_risk(task))
                for task in active_tasks
            ]
            recommended_task, recommended_risk = max(
                ranked_tasks,
                key=lambda item: (
                    item[1]["score"],
                    -item[0].due_at.timestamp(),
                ),
            )

    return render_template(
        "dashboard.html",
        profile=profile,
        active_task_count=len(active_tasks),
        recommended_task=recommended_task,
        recommended_risk=recommended_risk,
    )
