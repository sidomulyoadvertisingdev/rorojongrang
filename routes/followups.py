from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import db
from models.followup import FollowUp
from models.lead_pipeline import LeadPipeline
from models.lead_activity import LeadActivity

followups_bp = Blueprint("followups", __name__)


@followups_bp.route("/followups")
@login_required
def dashboard():
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    if current_user.is_admin:
        my_followups = FollowUp.query.filter(FollowUp.scheduled_at >= today_start - timedelta(days=7)).order_by(FollowUp.scheduled_at).all()
    else:
        my_followups = FollowUp.query.filter(
            FollowUp.user_id == current_user.id,
            FollowUp.scheduled_at >= today_start - timedelta(days=7)
        ).order_by(FollowUp.scheduled_at).all()

    overdue = [f for f in my_followups if f.status == "pending" and f.scheduled_at < now]
    today = [f for f in my_followups if f.status == "pending" and today_start <= f.scheduled_at < today_end]
    upcoming = [f for f in my_followups if f.status == "pending" and f.scheduled_at >= today_end]
    completed = [f for f in my_followups if f.status == "completed"]

    return render_template("followups/dashboard.html",
                           overdue=overdue, today=today, upcoming=upcoming, completed=completed,
                           now=now)


@followups_bp.route("/followups/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        lead_id = request.form.get("lead_id", type=int)
        followup_type = request.form.get("type", "call")
        scheduled_str = request.form.get("scheduled_at", "")
        notes = request.form.get("notes", "").strip()

        if not lead_id or not scheduled_str:
            flash("Lengkapi data follow-up.", "danger")
            return redirect(url_for("followups.create"))

        scheduled_at = datetime.strptime(scheduled_str, "%Y-%m-%dT%H:%M")
        fu = FollowUp(
            lead_id=lead_id,
            user_id=current_user.id,
            type=followup_type,
            scheduled_at=scheduled_at,
            notes=notes,
        )
        db.session.add(fu)
        db.session.flush()
        lead = LeadPipeline.query.get(lead_id)
        log = LeadActivity(lead_id=lead_id, user_id=current_user.id, action="followup",
                           detail=f"Follow-up dijadwalkan: {followup_type} pada {scheduled_at.strftime('%d %b %Y %H:%M')}")
        db.session.add(log)
        db.session.commit()
        flash("Follow-up berhasil dijadwalkan!", "success")
        return redirect(url_for("followups.dashboard"))

    leads = LeadPipeline.query.filter(LeadPipeline.status.notin_(["won", "lost"])).order_by(LeadPipeline.created_at.desc()).all()
    return render_template("followups/create.html", leads=leads)


@followups_bp.route("/followups/<int:fu_id>/complete", methods=["POST"])
@login_required
def complete(fu_id):
    fu = FollowUp.query.get_or_404(fu_id)
    fu.status = "completed"
    fu.completed_at = datetime.utcnow()
    log = LeadActivity(lead_id=fu.lead_id, user_id=current_user.id, action=fu.type,
                       detail=f"Follow-up {fu.type} selesai")
    db.session.add(log)
    db.session.commit()
    return jsonify({"ok": True})


@followups_bp.route("/followups/<int:fu_id>/reschedule", methods=["POST"])
@login_required
def reschedule(fu_id):
    fu = FollowUp.query.get_or_404(fu_id)
    data = request.get_json()
    new_date = datetime.strptime(data["scheduled_at"], "%Y-%m-%dT%H:%M")
    fu.scheduled_at = new_date
    fu.status = "rescheduled"
    log = LeadActivity(lead_id=fu.lead_id, user_id=current_user.id, action="note",
                       detail=f"Follow-up dijadwalkan ulang ke {new_date.strftime('%d %b %Y %H:%M')}")
    db.session.add(log)
    db.session.commit()
    return jsonify({"ok": True})


@followups_bp.route("/api/followups/today")
@login_required
def api_today():
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    followups = FollowUp.query.filter(
        FollowUp.user_id == current_user.id,
        FollowUp.status == "pending",
        FollowUp.scheduled_at >= today_start,
        FollowUp.scheduled_at < today_end,
    ).all()
    return jsonify([{
        "id": f.id,
        "lead_name": f.lead.business.name if f.lead and f.lead.business else "Unknown",
        "type": f.type,
        "scheduled_at": f.scheduled_at.strftime("%H:%M"),
        "notes": f.notes or "",
    } for f in followups])
