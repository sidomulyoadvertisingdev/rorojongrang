from datetime import datetime
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import db
from models.lead_pipeline import LeadPipeline
from models.lead_activity import LeadActivity
from models.followup import FollowUp
from models.business import Business
from models.user import User

leads_bp = Blueprint("leads", __name__)


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            flash("Akses ditolak.", "danger")
            return redirect(url_for("leads.lead_pipeline"))
        return f(*args, **kwargs)
    return decorated


def _log_lead_activity(lead_id, action, detail=""):
    log = LeadActivity(lead_id=lead_id, user_id=current_user.id, action=action, detail=detail)
    db.session.add(log)


LEAD_STATUSES = [
    {"key": "new", "label": "New", "color": "#6b6480"},
    {"key": "contacted", "label": "Contacted", "color": "#3b82f6"},
    {"key": "negotiation", "label": "Negotiation", "color": "#f59e0b"},
    {"key": "won", "label": "Won", "color": "#22c55e"},
    {"key": "lost", "label": "Lost", "color": "#ef4444"},
]


@leads_bp.route("/leads")
@login_required
def lead_pipeline():
    if current_user.is_admin:
        leads = LeadPipeline.query.filter_by(assigned_to=None).all() + \
                LeadPipeline.query.filter(LeadPipeline.assigned_to.isnot(None)).all()
    else:
        leads = LeadPipeline.query.filter_by(assigned_to=current_user.id).all()
    leads_by_status = {}
    for s in LEAD_STATUSES:
        leads_by_status[s["key"]] = [l for l in leads if l.status == s["key"]]
    users = User.query.filter_by(is_active=True).all()
    campaigns = __import__("models.campaign", fromlist=["Campaign"]).Campaign.query.filter_by(status="active").all()
    return render_template("leads/pipeline.html", leads_by_status=leads_by_status, statuses=LEAD_STATUSES, users=users, campaigns=campaigns)


@leads_bp.route("/leads/create", methods=["GET", "POST"])
@login_required
def create_lead():
    if request.method == "POST":
        business_id = request.form.get("business_id", type=int)
        assigned_to = request.form.get("assigned_to", type=int)
        priority = request.form.get("priority", "medium")
        value = request.form.get("value", 0, type=float)
        notes = request.form.get("notes", "").strip()
        campaign_id = request.form.get("campaign_id", type=int)
        due_date_str = request.form.get("due_date", "")
        due_date = datetime.strptime(due_date_str, "%Y-%m-%d") if due_date_str else None

        if not business_id:
            flash("Pilih bisnis terlebih dahulu.", "danger")
            return redirect(url_for("leads.create_lead"))

        existing = LeadPipeline.query.filter_by(business_id=business_id).first()
        if existing:
            flash("Bisnis ini sudah ada di pipeline.", "warning")
            return redirect(url_for("leads.lead_detail", lead_id=existing.id))

        lead = LeadPipeline(
            business_id=business_id,
            assigned_to=assigned_to,
            assigned_by=current_user.id,
            priority=priority,
            value=value,
            notes=notes,
            campaign_id=campaign_id if campaign_id else None,
            due_date=due_date,
        )
        db.session.add(lead)
        db.session.flush()
        _log_lead_activity(lead.id, "created", f"Lead '{Business.query.get(business_id).name}' dibuat")
        if assigned_to:
            _log_lead_activity(lead.id, "assigned", f"Di-assign ke {User.query.get(assigned_to).username}")
        db.session.commit()
        flash("Lead berhasil dibuat!", "success")
        return redirect(url_for("leads.lead_detail", lead_id=lead.id))

    businesses = Business.query.filter_by(user_id=current_user.id).all()
    users = User.query.filter_by(is_active=True).all()
    from models.campaign import Campaign
    campaigns = Campaign.query.filter_by(status="active").all()
    return render_template("leads/create.html", businesses=businesses, users=users, campaigns=campaigns)


@leads_bp.route("/leads/<int:lead_id>")
@login_required
def lead_detail(lead_id):
    lead = LeadPipeline.query.get_or_404(lead_id)
    activities = LeadActivity.query.filter_by(lead_id=lead.id).order_by(LeadActivity.created_at.desc()).all()
    followups = FollowUp.query.filter_by(lead_id=lead.id).order_by(FollowUp.scheduled_at.desc()).all()
    users = User.query.filter_by(is_active=True).all()
    from models.campaign import Campaign
    campaigns = Campaign.query.filter_by(status="active").all()
    return render_template("leads/detail.html", lead=lead, activities=activities, followups=followups, users=users, campaigns=campaigns, statuses=LEAD_STATUSES)


@leads_bp.route("/leads/<int:lead_id>/from-business/<int:business_id>", methods=["POST"])
@login_required
def create_from_business(business_id, lead_id=None):
    business = Business.query.get_or_404(business_id)
    existing = LeadPipeline.query.filter_by(business_id=business_id).first()
    if existing:
        flash("Bisnis ini sudah ada di pipeline.", "warning")
        return redirect(url_for("leads.lead_detail", lead_id=existing.id))

    lead = LeadPipeline(
        business_id=business_id,
        assigned_by=current_user.id,
    )
    db.session.add(lead)
    db.session.flush()
    _log_lead_activity(lead.id, "created", f"Lead '{business.name}' dibuat dari scraping data")
    db.session.commit()
    flash(f"Lead '{business.name}' berhasil dibuat!", "success")
    return redirect(url_for("leads.lead_detail", lead_id=lead.id))


@leads_bp.route("/api/leads/move", methods=["POST"])
@login_required
def move_lead():
    data = request.get_json()
    lead_id = data.get("lead_id")
    status = data.get("status")
    lead = LeadPipeline.query.get_or_404(lead_id)
    old_status = lead.status
    lead.status = status
    if status in ("won", "lost"):
        lead.closed_at = datetime.utcnow()
    _log_lead_activity(lead.id, "status_change", f"Status diubah dari '{old_status}' ke '{status}'")
    db.session.commit()
    return jsonify({"ok": True})


@leads_bp.route("/api/leads/<int:lead_id>/update", methods=["POST"])
@login_required
def update_lead(lead_id):
    data = request.get_json()
    lead = LeadPipeline.query.get_or_404(lead_id)
    if "assigned_to" in data:
        lead.assigned_to = data["assigned_to"]
        user = User.query.get(data["assigned_to"]) if data["assigned_to"] else None
        _log_lead_activity(lead.id, "assigned", f"Di-assign ke {user.username if user else 'tidak ada'}")
    if "priority" in data:
        lead.priority = data["priority"]
        _log_lead_activity(lead.id, "priority", f"Prioritas diubah ke {data['priority']}")
    if "value" in data:
        lead.value = data["value"]
    if "campaign_id" in data:
        lead.campaign_id = data["campaign_id"]
    if "due_date" in data:
        lead.due_date = datetime.strptime(data["due_date"], "%Y-%m-%d") if data["due_date"] else None
    if "notes" in data:
        lead.notes = data["notes"]
    db.session.commit()
    return jsonify({"ok": True})


@leads_bp.route("/api/leads/<int:lead_id>/activity", methods=["POST"])
@login_required
def add_activity(lead_id):
    data = request.get_json()
    action = data.get("action", "note")
    detail = data.get("detail", "").strip()
    if not detail:
        return jsonify({"error": "Detail kosong"}), 400
    _log_lead_activity(lead_id, action, detail)
    if action in ("call", "whatsapp", "email"):
        lead = LeadPipeline.query.get(lead_id)
        if lead and lead.status == "new":
            lead.status = "contacted"
    db.session.commit()
    return jsonify({"ok": True})


@leads_bp.route("/api/leads/<int:lead_id>/delete", methods=["POST"])
@login_required
def delete_lead(lead_id):
    if not current_user.is_admin:
        return jsonify({"error": "Akses ditolak"}), 403
    lead = LeadPipeline.query.get_or_404(lead_id)
    LeadActivity.query.filter_by(lead_id=lead.id).delete()
    FollowUp.query.filter_by(lead_id=lead.id).delete()
    db.session.delete(lead)
    db.session.commit()
    return jsonify({"ok": True})


@leads_bp.route("/api/leads/search-business")
@login_required
def search_business():
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify([])
    businesses = Business.query.filter(
        Business.user_id == current_user.id,
        Business.name.ilike(f"%{q}%")
    ).limit(10).all()
    existing_ids = [l.business_id for l in LeadPipeline.query.all()]
    results = [
        {"id": b.id, "name": b.name, "address": b.address or "", "phone": b.phone or "", "in_pipeline": b.id in existing_ids}
        for b in businesses
    ]
    return jsonify(results)
