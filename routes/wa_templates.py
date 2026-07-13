from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from models import db
from models.wa_template import WaTemplate
from models.wa_link import WaLink
from models.wa_click import WaClick
from models.business import Business

wa_templates_bp = Blueprint("wa_templates", __name__)


@wa_templates_bp.route("/wa-templates")
@login_required
def list_templates():
    templates = WaTemplate.query.filter_by(user_id=current_user.id)\
        .order_by(WaTemplate.created_at.desc()).all()
    return render_template("wa_templates/list.html", templates=templates)


@wa_templates_bp.route("/wa-templates/create", methods=["GET", "POST"])
@login_required
def create_template():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        message = request.form.get("message", "").strip()
        if not name or not message:
            flash("Nama dan pesan template harus diisi.", "error")
            return redirect(url_for("wa_templates.create_template"))

        template = WaTemplate(user_id=current_user.id, name=name, message=message)
        db.session.add(template)
        db.session.flush()

        link_names = request.form.getlist("link_name[]")
        link_urls = request.form.getlist("link_url[]")
        for ln, lu in zip(link_names, link_urls):
            ln, lu = ln.strip(), lu.strip()
            if ln and lu:
                db.session.add(WaLink(template_id=template.id, user_id=current_user.id, name=ln, url=lu))

        db.session.commit()
        flash(f"Template '{name}' berhasil dibuat!", "success")
        return redirect(url_for("wa_templates.list_templates"))

    return render_template("wa_templates/form.html", template=None)


@wa_templates_bp.route("/wa-templates/<int:template_id>/edit", methods=["GET", "POST"])
@login_required
def edit_template(template_id):
    template = WaTemplate.query.filter_by(id=template_id, user_id=current_user.id).first_or_404()

    if request.method == "POST":
        template.name = request.form.get("name", "").strip()
        template.message = request.form.get("message", "").strip()
        if not template.name or not template.message:
            flash("Nama dan pesan template harus diisi.", "error")
            return redirect(url_for("wa_templates.edit_template", template_id=template_id))

        WaLink.query.filter_by(template_id=template_id).delete()
        link_names = request.form.getlist("link_name[]")
        link_urls = request.form.getlist("link_url[]")
        for ln, lu in zip(link_names, link_urls):
            ln, lu = ln.strip(), lu.strip()
            if ln and lu:
                db.session.add(WaLink(template_id=template_id, user_id=current_user.id, name=ln, url=lu))

        db.session.commit()
        flash(f"Template '{template.name}' berhasil diupdate!", "success")
        return redirect(url_for("wa_templates.list_templates"))

    return render_template("wa_templates/form.html", template=template)


@wa_templates_bp.route("/wa-templates/<int:template_id>/delete", methods=["POST"])
@login_required
def delete_template(template_id):
    template = WaTemplate.query.filter_by(id=template_id, user_id=current_user.id).first_or_404()
    name = template.name
    db.session.delete(template)
    db.session.commit()
    flash(f"Template '{name}' berhasil dihapus.", "success")
    return redirect(url_for("wa_templates.list_templates"))


@wa_templates_bp.route("/api/wa-click", methods=["POST"])
@login_required
def record_click():
    data = request.get_json()
    business_id = data.get("business_id")
    template_id = data.get("template_id")
    link_id = data.get("link_id")
    phone = data.get("phone", "")
    task_id = data.get("task_id")

    if not business_id or not template_id:
        return jsonify({"error": "business_id and template_id required"}), 400

    click = WaClick(
        user_id=current_user.id,
        business_id=business_id,
        template_id=template_id,
        link_id=link_id,
        task_id=task_id,
        phone=phone,
    )
    db.session.add(click)
    business = Business.query.filter_by(id=business_id, user_id=current_user.id).first()
    if business:
        business.last_contacted_at = datetime.utcnow()
        if not business.lead_status or business.lead_status == "new":
            business.lead_status = "sent"
    db.session.commit()
    return jsonify({"status": "recorded", "click_id": click.id})
