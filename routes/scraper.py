import csv
import io
import json
import requests as http_requests
from flask import Blueprint, render_template, request, jsonify, send_file
from flask_login import login_required, current_user
from models import db
from models.task import ScrapingTask
from models.business import Business

scraper_bp = Blueprint("scraper", __name__)

WILAYAH_API = "https://wilayah-id-restapi.vercel.app/api/v1"

CATEGORIES = [
    {"name": "Toko Material Bangunan", "keywords": ["toko material bangunan", "toko besi", "toko cat", "toko plumbing", "toko listrik"]},
    {"name": "Toko Bangunan", "keywords": ["toko bangunan", "hardware store"]},
    {"name": "Toko Kelontong", "keywords": ["toko kelontong", "toko sembako", "warung", "toko grosir", "toko klontong"]},
    {"name": "Toko Elektronik", "keywords": ["toko elektronik", "toko handphone", "toko laptop", "service elektronik"]},
    {"name": "Toko Fashion", "keywords": ["toko fashion", "butik", "toko baju", "toko sepatu", "toko tas"]},
    {"name": "Toko Obat / Apotek", "keywords": ["apotek", "apotik", "toko obat", "farmasi"]},
    {"name": "Restoran", "keywords": ["restoran", "rumah makan", "restaurant", "food court"]},
    {"name": "Cafe / Kopi", "keywords": ["cafe", "kopi", "coffee shop", "kedai kopi"]},
    {"name": "Rumah Sakit / Klinik", "keywords": ["rumah sakit", "klinik", "puskesmas", "praktik dokter"]},
    {"name": "Sekolah", "keywords": ["sekolah dasar", "sekolah menengah pertama", "sekolah menengah atas", "tk", "paud"]},
    {"name": "Universitas / Kampus", "keywords": ["universitas", "kampus", "institut", "akademi", "politeknik"]},
    {"name": "Perusahaan / Kantor", "keywords": ["kantor perusahaan", "PT", "CV", "pabrik", "kantor"]},
    {"name": "Bengkel / Otomotif", "keywords": ["bengkel", "bengkel motor", "bengkel mobil", "toko spare part", "toko ban"]},
    {"name": "Percetakan / Fotocopy", "keywords": ["percetakan", "fotocopy", "warnet", "toko ATK", "toko alat tulis"]},
    {"name": "Masjid / Tempat Ibadah", "keywords": ["masjid", "musholla", "gereja", "pura", "vihara"]},
    {"name": "Hotel / Penginapan", "keywords": ["hotel", "penginapan", "guest house", "hostel", "villa"]},
    {"name": "Minimarket / Supermarket", "keywords": ["minimarket", "supermarket", "hypermarket", "toko serba ada"]},
    {"name": "Pertanian / Perkebunan", "keywords": ["toko pertanian", "toko pupuk", "toko benih", "alat pertanian"]},
    {"name": "Fotografi / Videografi", "keywords": ["fotografer", "studio foto", "video shooting", "percetakan foto"]},
    {"name": "Salon / Barbershop", "keywords": ["salon", "barbershop", "potong rambut", "spa", "perawatan"]},
]


@scraper_bp.route("/scrape")
@login_required
def scrape_form():
    tasks = ScrapingTask.query.filter_by(user_id=current_user.id)\
        .order_by(ScrapingTask.created_at.desc()).limit(20).all()
    return render_template(
        "scraper/form.html",
        categories=CATEGORIES,
        tasks=tasks,
    )


@scraper_bp.route("/api/wilayah/provinces")
@login_required
def api_provinces():
    try:
        resp = http_requests.get(f"{WILAYAH_API}/regions/provinces", timeout=10)
        raw = resp.json()
        items = [{"code": p["kode_prov"], "name": p["nama_provinsi"]} for p in raw.get("data", [])]
        return jsonify({"data": items})
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@scraper_bp.route("/api/wilayah/regencies/<province_code>")
@login_required
def api_regencies(province_code):
    try:
        resp = http_requests.get(f"{WILAYAH_API}/regions/regencies", params={"province_code": province_code}, timeout=10)
        raw = resp.json()
        items = [{"code": r["kode_kab"], "name": r["nama_kabupaten"]} for r in raw.get("data", [])]
        return jsonify({"data": items})
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@scraper_bp.route("/api/wilayah/districts/<regency_code>")
@login_required
def api_districts(regency_code):
    try:
        resp = http_requests.get(f"{WILAYAH_API}/regions/districts", params={"regency_code": regency_code}, timeout=10)
        raw = resp.json()
        items = [{"code": d["kode_kec"], "name": d["nama_kecamatan"]} for d in raw.get("data", [])]
        return jsonify({"data": items})
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@scraper_bp.route("/api/wilayah/geocode")
@login_required
def api_geocode():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "Query required"}), 400
    try:
        resp = http_requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": q + ", Indonesia", "format": "json", "limit": 1},
            headers={"User-Agent": "Roro JonggrangScraper/1.0"},
            timeout=10,
        )
        data = resp.json()
        if data:
            return jsonify({"lat": float(data[0]["lat"]), "lng": float(data[0]["lon"]), "display": data[0].get("display_name", "")})
        return jsonify({"error": "Lokasi tidak ditemukan"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@scraper_bp.route("/scrape", methods=["POST"])
@login_required
def start_scrape():
    keyword = request.form.get("keyword", "").strip()
    category = request.form.get("category", "").strip()
    radius = request.form.get("radius", "5").strip()
    country = request.form.get("country", "Indonesia").strip()
    province = request.form.get("province", "").strip()
    regency = request.form.get("regency", "").strip()
    district = request.form.get("district", "").strip()
    center_lat = request.form.get("center_lat", "0").strip()
    center_lng = request.form.get("center_lng", "0").strip()

    if not keyword:
        return jsonify({"error": "Keyword harus diisi"}), 400

    location_parts = [p for p in [district, regency, province] if p]
    location = ", ".join(location_parts) if location_parts else ""
    if not location:
        return jsonify({"error": "Lokasi harus dipilih (minimal provinsi)"}), 400

    try:
        radius = int(radius)
    except (ValueError, TypeError):
        radius = 5

    try:
        lat = float(center_lat)
        lng = float(center_lng)
    except (ValueError, TypeError):
        lat, lng = 0.0, 0.0

    task = ScrapingTask(
        user_id=current_user.id,
        keyword=keyword,
        location=location,
        category=category,
        country=country,
        province=province,
        regency=regency,
        district=district,
        center_lat=lat,
        center_lng=lng,
        status="pending",
    )
    task.search_radius = radius
    db.session.add(task)
    db.session.commit()

    from services.scraping_service import run_scraping
    try:
        celery_result = run_scraping.delay(
            task.id,
            radius=radius,
            center_lat=lat,
            center_lng=lng,
        )
    except Exception as exc:
        task.status = "failed"
        task.error_message = f"Gagal antre task ke Redis/Celery: {exc}"
        db.session.commit()
        return jsonify({
            "error": "Gagal memulai scraping. Pastikan Redis dan Celery berjalan.",
            "detail": str(exc),
        }), 503

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


@scraper_bp.route("/scrape/<int:task_id>/delete", methods=["POST"])
@login_required
def delete_scrape(task_id):
    task = ScrapingTask.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    if task.status in ("pending", "running"):
        if task.celery_task_id:
            try:
                from celery_worker import celery
                celery.control.revoke(task.celery_task_id, terminate=True)
            except Exception:
                pass
    Business.query.filter_by(task_id=task_id).delete()
    db.session.delete(task)
    db.session.commit()
    return jsonify({"status": "deleted"})


@scraper_bp.route("/results/<int:task_id>")
@login_required
def results(task_id):
    task = ScrapingTask.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    return render_template("scraper/results.html", task=task)


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
