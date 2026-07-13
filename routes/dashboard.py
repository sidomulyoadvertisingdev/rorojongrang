import json
from flask import Blueprint, redirect, render_template, url_for
from flask_login import login_required, current_user
from models import db
from models.task import ScrapingTask
from models.business import Business

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def index():
    if not current_user.is_authenticated:
        return redirect(url_for("blog.home"))

    total_tasks = ScrapingTask.query.filter_by(user_id=current_user.id).count()
    total_data = db.session.query(
        db.func.coalesce(db.func.sum(ScrapingTask.scraped_results), 0)
    ).filter(
        ScrapingTask.user_id == current_user.id,
        ScrapingTask.status == "completed"
    ).scalar()
    running_tasks = ScrapingTask.query.filter(
        ScrapingTask.user_id == current_user.id,
        ScrapingTask.status.in_(["pending", "running"])
    ).count()

    recent_tasks = ScrapingTask.query.filter_by(user_id=current_user.id)\
        .order_by(ScrapingTask.created_at.desc()).limit(10).all()

    return render_template(
        "dashboard/index.html",
        total_tasks=total_tasks,
        total_data=total_data,
        running_tasks=running_tasks,
        recent_tasks=recent_tasks,
    )
