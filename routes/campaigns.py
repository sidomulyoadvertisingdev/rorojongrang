from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import db
from models.campaign import Campaign, CampaignMetric
from models.lead_pipeline import LeadPipeline

campaigns_bp = Blueprint("campaigns", __name__)


@campaigns_bp.route("/campaigns")
@login_required
def list_campaigns():
    if current_user.is_admin:
        campaigns = Campaign.query.order_by(Campaign.created_at.desc()).all()
    else:
        campaign_ids = db.session.query(LeadPipeline.campaign_id).filter_by(assigned_to=current_user.id).distinct().all()
        ids = [c[0] for c in campaign_ids if c[0]]
        campaigns = Campaign.query.filter(Campaign.id.in_(ids)).all()
    return render_template("campaigns/list.html", campaigns=campaigns)


@campaigns_bp.route("/campaigns/create", methods=["GET", "POST"])
@login_required
def create_campaign():
    if not current_user.is_admin:
        flash("Akses ditolak.", "danger")
        return redirect(url_for("campaigns.list_campaigns"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        start_date_str = request.form.get("start_date", "")
        end_date_str = request.form.get("end_date", "")
        target_leads = request.form.get("target_leads", 0, type=int)

        if not name:
            flash("Nama campaign tidak boleh kosong.", "danger")
            return redirect(url_for("campaigns.create_campaign"))

        start_date = datetime.strptime(start_date_str, "%Y-%m-%d") if start_date_str else None
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d") if end_date_str else None

        campaign = Campaign(
            name=name,
            description=description,
            created_by=current_user.id,
            start_date=start_date,
            end_date=end_date,
            target_leads=target_leads,
        )
        db.session.add(campaign)
        db.session.flush()
        metrics = CampaignMetric(campaign_id=campaign.id)
        db.session.add(metrics)
        db.session.commit()
        flash(f"Campaign '{name}' berhasil dibuat!", "success")
        return redirect(url_for("campaigns.dashboard", campaign_id=campaign.id))

    return render_template("campaigns/create.html")


@campaigns_bp.route("/campaigns/<int:campaign_id>")
@login_required
def dashboard(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    metrics = campaign.get_or_create_metrics()
    campaign.recalculate_metrics()
    leads = LeadPipeline.query.filter_by(campaign_id=campaign.id).order_by(LeadPipeline.created_at.desc()).all()

    leads_by_status = {}
    for s in ["new", "contacted", "negotiation", "won", "lost"]:
        leads_by_status[s] = len([l for l in leads if l.status == s])

    return render_template("campaigns/dashboard.html",
                           campaign=campaign, metrics=metrics, leads=leads,
                           leads_by_status=leads_by_status)


@campaigns_bp.route("/campaigns/<int:campaign_id>/update", methods=["POST"])
@login_required
def update_campaign(campaign_id):
    if not current_user.is_admin:
        return jsonify({"error": "Akses ditolak"}), 403
    campaign = Campaign.query.get_or_404(campaign_id)
    data = request.get_json()
    if "status" in data:
        campaign.status = data["status"]
    if "name" in data:
        campaign.name = data["name"]
    db.session.commit()
    return jsonify({"ok": True})


@campaigns_bp.route("/api/campaigns/<int:campaign_id>/metrics")
@login_required
def api_metrics(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    campaign.recalculate_metrics()
    m = campaign.metrics
    return jsonify({
        "total_leads": m.total_leads,
        "contacted_leads": m.contacted_leads,
        "responded_leads": m.responded_leads,
        "won_leads": m.won_leads,
        "lost_leads": m.lost_leads,
        "total_value": m.total_value,
        "conversion_rate": m.conversion_rate,
    })
