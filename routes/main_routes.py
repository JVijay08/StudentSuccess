from flask import Blueprint, redirect, render_template, url_for

from models import StudentProfile


main_bp = Blueprint("main", __name__)
@main_bp.get("/")
def home():
    return redirect(url_for("main.dashboard"))
@main_bp.get("/dashboard")
def dashboard():
    profile = StudentProfile.query.first()
    return render_template("dashboard.html", profile=profile)
