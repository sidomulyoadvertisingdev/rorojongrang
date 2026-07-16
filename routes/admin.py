from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import db
from models.user import User
from models.activity_log import ActivityLog
from utils.helpers import admin_required, platform_admin_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


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


@admin_bp.route("/users/<int:user_id>/role", methods=["POST"])
@platform_admin_required
def change_role(user_id):
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash("Tidak bisa mengubah role akun sendiri.", "danger")
        return redirect(url_for("admin.user_list"))

    new_role = request.form.get("role", "").strip()
    allowed_roles = [User.ROLE_USER, User.ROLE_ADMIN, User.ROLE_PLATFORM_ADMIN]
    if new_role not in allowed_roles:
        flash("Role tidak valid.", "danger")
        return redirect(url_for("admin.user_list"))

    if user.role == User.ROLE_PLATFORM_ADMIN and new_role != User.ROLE_PLATFORM_ADMIN:
        flash("Tidak bisa menurunkan role Admin Platform lain.", "danger")
        return redirect(url_for("admin.user_list"))

    user.role = new_role
    db.session.commit()

    log_activity(user_id, "change_role", user.username, f"role -> {new_role}")
    flash(f"Role {user.username} diubah menjadi '{new_role}'.", "success")
    return redirect(url_for("admin.user_list"))


@admin_bp.route("/users/<int:user_id>/ban", methods=["POST"])
@admin_required
def ban_user(user_id):
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash("Tidak bisa ban akun sendiri.", "danger")
        return redirect(url_for("admin.user_list"))

    if not current_user.can_manage(user):
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

    if not current_user.can_manage(user):
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


@admin_bp.route("/feedback")
@admin_required
def feedback_list():
    from models.feedback import Feedback

    page = request.args.get("page", 1, type=int)
    filter_type = request.args.get("filter", "").strip()
    per_page = 20

    query = Feedback.query

    if filter_type == "unread":
        query = query.filter_by(is_read=False)
    elif filter_type in ("feature", "complaint", "suggestion"):
        query = query.filter_by(category=filter_type)

    pagination = query.order_by(
        Feedback.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)

    total = Feedback.query.count()
    unread = Feedback.query.filter_by(is_read=False).count()
    feature_count = Feedback.query.filter_by(category="feature").count()
    complaint_count = Feedback.query.filter_by(category="complaint").count()

    return render_template(
        "admin/feedback.html",
        feedbacks=pagination.items,
        pagination=pagination,
        total=total,
        unread=unread,
        feature_count=feature_count,
        complaint_count=complaint_count,
        filter_type=filter_type,
    )


@admin_bp.route("/feedback/<int:fb_id>/read", methods=["POST"])
@admin_required
def mark_read(fb_id):
    from models.feedback import Feedback

    fb = Feedback.query.get_or_404(fb_id)
    fb.is_read = True
    db.session.commit()
    flash("Masukan ditandai sudah dibaca.", "success")
    return redirect(url_for("admin.feedback_list"))
