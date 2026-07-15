from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import db
from models.campaign import Campaign, CampaignMetric
from models.campaign_attachment import CampaignAttachment
from models.lead_pipeline import LeadPipeline
from models.user_drive_token import UserDriveToken

MAX_FILE_SIZE = 25 * 1024 * 1024

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

        files = request.files.getlist("files")
        token = UserDriveToken.query.filter_by(user_id=current_user.id).first()
        uploaded_count = 0
        if token and files:
            from helpers.drive import upload_file_to_drive, share_file_anyone
            for f in files:
                if not f.filename:
                    continue
                file_data = f.read()
                if len(file_data) > MAX_FILE_SIZE:
                    continue
                try:
                    result = upload_file_to_drive(token, file_data, f.filename, f.content_type, board_name=f"Campaign - {name}")
                    drive_file_id = result.get("id", "")
                    share_file_anyone(token, drive_file_id)
                    mime = f.content_type or ""
                    file_type = "other"
                    if "image" in mime:
                        file_type = "image"
                    elif "pdf" in mime:
                        file_type = "pdf"
                    elif "spreadsheet" in mime or "excel" in mime or "csv" in mime:
                        file_type = "spreadsheet"
                    att = CampaignAttachment(
                        campaign_id=campaign.id,
                        uploaded_by=current_user.id,
                        drive_file_id=drive_file_id,
                        filename=f.filename,
                        mime_type=f.content_type,
                        file_size=len(file_data),
                        drive_url=f"https://drive.google.com/file/d/{drive_file_id}/view",
                        file_type=file_type,
                    )
                    db.session.add(att)
                    uploaded_count += 1
                except Exception:
                    pass

        db.session.commit()
        if uploaded_count > 0:
            flash(f"Campaign '{name}' berhasil dibuat dengan {uploaded_count} file!", "success")
        else:
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
    attachments = CampaignAttachment.query.filter_by(campaign_id=campaign.id).order_by(CampaignAttachment.created_at.desc()).all()
    drive_token = UserDriveToken.query.filter_by(user_id=current_user.id).first()

    leads_by_status = {}
    for s in ["new", "contacted", "negotiation", "won", "lost"]:
        leads_by_status[s] = len([l for l in leads if l.status == s])

    return render_template("campaigns/dashboard.html",
                           campaign=campaign, metrics=metrics, leads=leads,
                           leads_by_status=leads_by_status, attachments=attachments,
                           drive_token=drive_token)


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


@campaigns_bp.route("/campaigns/<int:campaign_id>/upload", methods=["POST"])
@login_required
def upload_attachment(campaign_id):
    if not current_user.is_admin:
        return jsonify({"error": "Akses ditolak"}), 403

    campaign = Campaign.query.get_or_404(campaign_id)
    token = UserDriveToken.query.filter_by(user_id=current_user.id).first()
    if not token:
        return jsonify({"error": "Google Drive belum terhubung. Hubungkan di profil Anda."}), 400

    if "file" not in request.files:
        return jsonify({"error": "Tidak ada file"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Filename kosong"}), 400

    file_data = file.read()
    if len(file_data) > MAX_FILE_SIZE:
        return jsonify({"error": "File terlalu besar (maks 25MB)"}), 400

    try:
        from helpers.drive import upload_file_to_drive, share_file_anyone
        result = upload_file_to_drive(
            token, file_data, file.filename, file.content_type,
            board_name=f"Campaign - {campaign.name}"
        )
        drive_file_id = result.get("id", "")
        share_file_anyone(token, drive_file_id)

        mime = file.content_type or ""
        file_type = "other"
        if "image" in mime:
            file_type = "image"
        elif "pdf" in mime:
            file_type = "pdf"
        elif "spreadsheet" in mime or "excel" in mime or "csv" in mime:
            file_type = "spreadsheet"

        att = CampaignAttachment(
            campaign_id=campaign.id,
            uploaded_by=current_user.id,
            drive_file_id=drive_file_id,
            filename=file.filename,
            mime_type=file.content_type,
            file_size=len(file_data),
            drive_url=f"https://drive.google.com/file/d/{drive_file_id}/view",
            file_type=file_type,
        )
        db.session.add(att)
        db.session.commit()

        return jsonify({
            "ok": True,
            "id": att.id,
            "filename": att.filename,
            "size": att.size_display(),
            "mime_type": att.mime_type,
            "url": att.drive_url,
            "uploaded_by": current_user.full_name or current_user.username,
            "created_at": att.created_at.strftime("%d %b %Y %H:%M"),
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Gagal upload: {str(e)}"}), 500


@campaigns_bp.route("/campaigns/<int:campaign_id>/attachments")
@login_required
def list_attachments(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    attachments = CampaignAttachment.query.filter_by(campaign_id=campaign.id).order_by(CampaignAttachment.created_at.desc()).all()
    result = []
    for att in attachments:
        result.append({
            "id": att.id,
            "filename": att.filename,
            "size": att.size_display(),
            "mime_type": att.mime_type,
            "url": att.drive_url,
            "file_type": att.file_type,
            "uploaded_by": att.uploader.full_name or att.uploader.username if att.uploader else "Unknown",
            "created_at": att.created_at.strftime("%d %b %Y %H:%M"),
        })
    return jsonify(result)


@campaigns_bp.route("/campaigns/<int:campaign_id>/attachment/<int:att_id>/delete", methods=["POST"])
@login_required
def delete_attachment(campaign_id, att_id):
    if not current_user.is_admin:
        return jsonify({"error": "Akses ditolak"}), 403

    att = CampaignAttachment.query.get_or_404(att_id)
    if att.campaign_id != campaign_id:
        return jsonify({"error": "Invalid"}), 400

    try:
        token = UserDriveToken.query.filter_by(user_id=att.uploaded_by).first()
        if not token:
            token = UserDriveToken.query.filter_by(user_id=current_user.id).first()
        if token and att.drive_file_id:
            from helpers.drive import delete_file_from_drive
            delete_file_from_drive(token, att.drive_file_id)
    except Exception:
        pass

    db.session.delete(att)
    db.session.commit()
    return jsonify({"ok": True})
