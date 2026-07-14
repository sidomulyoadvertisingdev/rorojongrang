from datetime import datetime
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db
from models.user import User
from models.activity_log import ActivityLog

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            flash("Akses ditolak. Hanya admin yang bisa mengakses halaman ini.", "danger")
            return redirect(url_for("dashboard.index"))
        return f(*args, **kwargs)
    return decorated


def log_activity(user_id, action, target, detail=""):
    log = ActivityLog(
        user_id=user_id,
        admin_id=current_user.id,
        action=action,
        target=target,
        detail=detail,
    )
    db.session.add(log)
    db.session.commit()


@admin_bp.route("/users")
@admin_required
def user_list():
    search = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = 20

    query = User.query

    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(
                User.username.ilike(like),
                User.email.ilike(like),
                User.full_name.ilike(like),
            )
        )

    pagination = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return render_template(
        "admin/users.html",
        users=pagination.items,
        pagination=pagination,
        search=search,
    )


@admin_bp.route("/users/<int:user_id>/ban", methods=["POST"])
@admin_required
def ban_user(user_id):
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash("Tidak bisa ban akun sendiri.", "danger")
        return redirect(url_for("admin.user_list"))

    if user.is_admin:
        flash("Tidak bisa ban akun admin lain.", "danger")
        return redirect(url_for("admin.user_list"))

    if user.is_banned:
        flash(f"{user.username} sudah di-ban.", "warning")
        return redirect(url_for("admin.user_list"))

    user.is_banned = True
    user.banned_at = datetime.utcnow()
    user.banned_by = current_user.id
    db.session.commit()

    log_activity(user_id, "ban", user.username)
    flash(f"Akun {user.username} berhasil di-ban.", "success")
    return redirect(url_for("admin.user_list"))


@admin_bp.route("/users/<int:user_id>/unban", methods=["POST"])
@admin_required
def unban_user(user_id):
    user = User.query.get_or_404(user_id)

    if not user.is_banned:
        flash(f"{user.username} tidak sedang di-ban.", "warning")
        return redirect(url_for("admin.user_list"))

    user.is_banned = False
    user.banned_at = None
    user.banned_by = None
    db.session.commit()

    log_activity(user_id, "unban", user.username)
    flash(f"Akun {user.username} berhasil di-unban.", "success")
    return redirect(url_for("admin.user_list"))


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash("Tidak bisa hapus akun sendiri.", "danger")
        return redirect(url_for("admin.user_list"))

    if user.is_admin:
        flash("Tidak bisa hapus akun admin lain.", "danger")
        return redirect(url_for("admin.user_list"))

    username = user.username
    email = user.email

    from models.task import ScrapingTask
    from models.business import Business

    tasks = ScrapingTask.query.filter_by(user_id=user.id).all()
    for task in tasks:
        Business.query.filter_by(task_id=task.id).delete()
    ScrapingTask.query.filter_by(user_id=user.id).delete()

    db.session.delete(user)
    db.session.commit()

    log_activity(user_id, "delete", username, f"email: {email}")
    flash(f"Akun {username} berhasil dihapus permanen.", "success")
    return redirect(url_for("admin.user_list"))


@admin_bp.route("/activity")
@admin_required
def activity_log():
    page = request.args.get("page", 1, type=int)
    per_page = 30

    pagination = ActivityLog.query.order_by(
        ActivityLog.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        "admin/activity.html",
        logs=pagination.items,
        pagination=pagination,
    )
