import csv
import io
import json
from pathlib import Path
from flask import Blueprint, render_template, request, jsonify, send_file
from flask_login import login_required, current_user
from models import db
from models.task import ScrapingTask
from models.business import Business

scraper_bp = Blueprint("scraper", __name__)

LOCATIONS = [
    "Kabupaten Bandung", "Kabupaten Bandung Barat", "Kabupaten Cimahi",
    "Kabupaten Sumedang", "Kabupaten Garut", "Kabupaten Tasikmalaya",
    "Kabupaten Ciamis", "Kabupaten Kuningan", "Kabupaten Majalengka",
    "Kabupaten Indramayu",
]

CATEGORIES = [
    {"name": "Toko Material Bangunan", "keywords": ["toko material bangunan", "toko besi", "toko cat", "toko plumbing", "toko listrik"]},
    {"name": "Toko Bangunan", "keywords": ["toko bangunan", "hardware store"]},
    {"name": "Sekolah", "keywords": ["sekolah dasar", "sekolah menengah pertama", "sekolah menengah atas"]},
    {"name": "Perusahaan", "keywords": ["kantor perusahaan", "PT", "CV", "pabrik"]},
]


@scraper_bp.route("/scrape")
@login_required
def scrape_form():
    tasks = ScrapingTask.query.filter_by(user_id=current_user.id)\
        .order_by(ScrapingTask.created_at.desc()).limit(20).all()
    return render_template(
        "scraper/form.html",
        locations=LOCATIONS,
        categories=CATEGORIES,
        tasks=tasks,
    )


@scraper_bp.route("/scrape", methods=["POST"])
@login_required
def start_scrape():
    keyword = request.form.get("keyword", "").strip()
    location = request.form.get("location", "").strip()
    category = request.form.get("category", "").strip()
    radius = request.form.get("radius", "5").strip()

    if not keyword or not location:
        return jsonify({"error": "Keyword dan lokasi harus diisi"}), 400

    try:
        radius = int(radius)
    except (ValueError, TypeError):
        radius = 5

    task = ScrapingTask(
        user_id=current_user.id,
        keyword=keyword,
        location=location,
        category=category,
        status="pending",
    )
    task.search_radius = radius
    db.session.add(task)
    db.session.commit()

    from services.scraping_service import run_scraping
    celery_result = run_scraping.delay(task.id, radius=radius)

    task.celery_task_id = celery_result.id
    db.session.commit()

    return jsonify({"task_id": task.id, "status": "pending", "radius": radius})


@scraper_bp.route("/scrape/<int:task_id>/cancel", methods=["POST"])
@login_required
def cancel_scrape(task_id):
    task = ScrapingTask.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    if task.status in ("pending", "running"):
        task.status = "cancelled"
        db.session.commit()
        if task.celery_task_id:
            from celery_worker import celery
            celery.control.revoke(task.celery_task_id, terminate=True)
        return jsonify({"status": "cancelled"})
    return jsonify({"error": "Task tidak bisa dibatalkan"}), 400


@scraper_bp.route("/history")
@login_required
def history():
    page = request.args.get("page", 1, type=int)
    tasks = ScrapingTask.query.filter_by(user_id=current_user.id)\
        .order_by(ScrapingTask.created_at.desc())\
        .paginate(page=page, per_page=20)
    return render_template("scraper/history.html", tasks=tasks)


@scraper_bp.route("/download/<int:task_id>/<fmt>")
@login_required
def download(task_id, fmt="csv"):
    task = ScrapingTask.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()

    businesses = Business.query.filter_by(task_id=task_id).all()
    if not businesses:
        return jsonify({"error": "Tidak ada data"}), 404

    if fmt == "json":
        data = [b.to_dict() for b in businesses]
        output = io.BytesIO()
        output.write(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))
        output.seek(0)
        filename = f"{task.keyword}_{task.location}_{task.id}.json"
        return send_file(output, mimetype="application/json", as_attachment=True, download_name=filename)

    output = io.StringIO()
    headers = [
        "name", "category", "address", "phone", "website",
        "rating", "review_count", "google_maps_url",
        "latitude", "longitude", "operating_hours",
    ]
    writer = csv.DictWriter(output, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()
    for b in businesses:
        writer.writerow(b.to_dict())

    mem = io.BytesIO()
    mem.write(output.getvalue().encode("utf-8"))
    mem.seek(0)
    filename = f"{task.keyword}_{task.location}_{task.id}.csv"
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name=filename)
