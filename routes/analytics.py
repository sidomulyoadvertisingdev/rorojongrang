import io
import os
import pandas as pd
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import db
from models.data_upload import DataUpload
from models.data_record import DataRecord

analytics_bp = Blueprint("analytics", __name__)

ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls"}

TEMPLATE_DATA = {
    "product": [
        {"nama_produk": "Kopi Arabika Gayo", "harga": 85000, "stok": 150, "kategori": "Minuman"},
        {"nama_produk": "Teh Hijau Premium", "harga": 45000, "stok": 200, "kategori": "Minuman"},
        {"nama_produk": "Madu Hutan Asli", "harga": 120000, "stok": 50, "kategori": "Makanan"},
        {"nama_produk": "Keripik Singkong", "harga": 25000, "stok": 300, "kategori": "Makanan"},
        {"nama_produk": "Sambal Nusantara", "harga": 35000, "stok": 80, "kategori": "Makanan"},
    ],
    "sales": [
        {"tanggal": "2026-07-01", "produk": "Kopi Arabika Gayo", "jumlah": 10, "total_harga": 850000, "pelanggan": "Budi Santoso"},
        {"tanggal": "2026-07-01", "produk": "Teh Hijau Premium", "jumlah": 5, "total_harga": 225000, "pelanggan": "Siti Rahayu"},
        {"tanggal": "2026-07-02", "produk": "Madu Hutan Asli", "jumlah": 3, "total_harga": 360000, "pelanggan": "Ahmad Hidayat"},
        {"tanggal": "2026-07-03", "produk": "Keripik Singkong", "jumlah": 20, "total_harga": 500000, "pelanggan": "Dewi Lestari"},
        {"tanggal": "2026-07-04", "produk": "Sambal Nusantara", "jumlah": 8, "total_harga": 280000, "pelanggan": "Rizki Pratama"},
    ],
    "customer": [
        {"nama": "Budi Santoso", "email": "budi@email.com", "telepon": "081234567890", "alamat": "Jakarta Selatan", "total_beli": 2500000},
        {"nama": "Siti Rahayu", "email": "siti@email.com", "telepon": "081234567891", "alamat": "Bandung", "total_beli": 1800000},
        {"nama": "Ahmad Hidayat", "email": "ahmad@email.com", "telepon": "081234567892", "alamat": "Surabaya", "total_beli": 3200000},
        {"nama": "Dewi Lestari", "email": "dewi@email.com", "telepon": "081234567893", "alamat": "Yogyakarta", "total_beli": 950000},
        {"nama": "Rizki Pratama", "email": "rizki@email.com", "telepon": "081234567894", "alamat": "Semarang", "total_beli": 4100000},
    ],
    "finance": [
        {"tanggal": "2026-07-01", "jenis": "pemasukan", "keterangan": "Penjualan Kopi", "jumlah": 850000, "kategori": "Penjualan"},
        {"tanggal": "2026-07-01", "jenis": "pengeluaran", "keterangan": "Beli Bahan Baku", "jumlah": 300000, "kategori": "Bahan Baku"},
        {"tanggal": "2026-07-02", "jenis": "pemasukan", "keterangan": "Penjualan Teh", "jumlah": 225000, "kategori": "Penjualan"},
        {"tanggal": "2026-07-02", "jenis": "pengeluaran", "keterangan": "Bayar Karyawan", "jumlah": 500000, "kategori": "Gaji"},
        {"tanggal": "2026-07-03", "jenis": "pemasukan", "keterangan": "Penjualan Madu", "jumlah": 360000, "kategori": "Penjualan"},
    ],
}

DATA_TYPE_FIELDS = {
    "product": {
        "label": "Produk",
        "fields": {
            "name": {"label": "Nama Produk", "detect": ["nama", "name", "product", "barang", "item", "produk"]},
            "price": {"label": "Harga", "detect": ["harga", "price", "harga_jual", "sell_price"]},
            "stock": {"label": "Stok", "detect": ["stok", "stock", "qty", "quantity", "jumlah"]},
            "category": {"label": "Kategori", "detect": ["kategori", "category", "jenis", "tipe"]},
        },
    },
    "sales": {
        "label": "Penjualan",
        "fields": {
            "date": {"label": "Tanggal", "detect": ["tanggal", "date", "tgl", "dates", "waktu"]},
            "product_name": {"label": "Produk", "detect": ["produk", "product", "barang", "nama_produk", "item"]},
            "quantity": {"label": "Jumlah", "detect": ["jumlah", "qty", "quantity", "banyak"]},
            "total_price": {"label": "Total Harga", "detect": ["total", "harga", "amount", "total_harga", "nominal", "bayar"]},
            "customer_name": {"label": "Pelanggan", "detect": ["pelanggan", "customer", "nama_pelanggan", "buyer"]},
        },
    },
    "customer": {
        "label": "Pelanggan",
        "fields": {
            "name": {"label": "Nama", "detect": ["nama", "name", "customer", "pelanggan", "nama_pelanggan"]},
            "email": {"label": "Email", "detect": ["email", "e-mail", "mail"]},
            "phone": {"label": "Telepon", "detect": ["telepon", "phone", "hp", "telp", "no_hp", "nomor"]},
            "address": {"label": "Alamat", "detect": ["alamat", "address", "domisili", "location"]},
            "total_purchase": {"label": "Total Beli", "detect": ["total_beli", "total_purchase", "total", "omzet"]},
        },
    },
    "finance": {
        "label": "Keuangan",
        "fields": {
            "date": {"label": "Tanggal", "detect": ["tanggal", "date", "tgl", "periode", "waktu"]},
            "type": {"label": "Jenis", "detect": ["jenis", "type", "tipe", "kategori"]},
            "description": {"label": "Deskripsi", "detect": ["deskripsi", "description", "keterangan", "note", "nama"]},
            "amount": {"label": "Jumlah", "detect": ["jumlah", "amount", "nominal", "nilai", "harga"]},
            "category": {"label": "Kategori", "detect": ["kategori", "category", "jenis"]},
        },
    },
}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def auto_detect_mapping(columns, data_type):
    fields = DATA_TYPE_FIELDS.get(data_type, {}).get("fields", {})
    mapping = {}
    cols_lower = {c.lower().strip(): c for c in columns}
    for field_key, field_info in fields.items():
        for detect_word in field_info["detect"]:
            for col_lower, col_orig in cols_lower.items():
                if detect_word in col_lower:
                    mapping[field_key] = col_orig
                    break
            if field_key in mapping:
                break
    return mapping


@analytics_bp.route("/analytics/template/<data_type>")
@login_required
def download_template(data_type):
    if data_type not in TEMPLATE_DATA:
        flash("Tipe data tidak valid", "error")
        return redirect(url_for("analytics.upload"))

    sample_rows = TEMPLATE_DATA[data_type]
    df = pd.DataFrame(sample_rows)

    buf = io.BytesIO()
    df.to_csv(buf, index=False, encoding="utf-8-sig")
    buf.seek(0)

    label = DATA_TYPE_FIELDS[data_type]["label"].lower()
    return send_file(
        buf,
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"template_{label}.csv",
    )


@analytics_bp.route("/analytics")
@login_required
def index():
    uploads = DataUpload.query.filter_by(user_id=current_user.id)\
        .order_by(DataUpload.created_at.desc()).all()
    return render_template("analytics/index.html", uploads=uploads, data_types=DATA_TYPE_FIELDS)


@analytics_bp.route("/analytics/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        data_type = request.form.get("data_type", "").strip()
        if data_type not in DATA_TYPE_FIELDS:
            flash("Tipe data tidak valid", "error")
            return redirect(url_for("analytics.upload"))

        if "file" not in request.files:
            flash("File tidak ditemukan", "error")
            return redirect(url_for("analytics.upload"))

        file = request.files["file"]
        if file.filename == "":
            flash("File tidak dipilih", "error")
            return redirect(url_for("analytics.upload"))

        if not allowed_file(file.filename):
            flash("Format file tidak didukung. Gunakan CSV atau Excel (.xlsx)", "error")
            return redirect(url_for("analytics.upload"))

        filename = secure_filename(file.filename)
        upload_dir = os.path.join(current_app.config.get("UPLOAD_FOLDER", "data/output"), "analytics")
        os.makedirs(upload_dir, exist_ok=True)
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)

        try:
            ext = filename.rsplit(".", 1)[1].lower()
            if ext == "csv":
                df = pd.read_csv(filepath, nrows=5, sep=None, engine="python", on_bad_lines="skip", encoding="utf-8-sig")
            else:
                df = pd.read_excel(filepath, nrows=5)
            df.columns = [c.strip().lstrip("\ufeff") for c in df.columns]
            columns = list(df.columns)
            detected = auto_detect_mapping(columns, data_type)

            upload = DataUpload(
                user_id=current_user.id,
                data_type=data_type,
                filename=filename,
                column_mapping={"columns": columns, "mapping": detected},
                status="pending",
            )
            db.session.add(upload)
            db.session.commit()

            return redirect(url_for("analytics.confirm_mapping", upload_id=upload.id))

        except Exception as e:
            flash(f"Gagal membaca file: {str(e)}", "error")
            return redirect(url_for("analytics.upload"))

    return render_template("analytics/upload.html", data_types=DATA_TYPE_FIELDS)


@analytics_bp.route("/analytics/<int:upload_id>/mapping", methods=["GET", "POST"])
@login_required
def confirm_mapping(upload_id):
    upload = DataUpload.query.filter_by(id=upload_id, user_id=current_user.id).first_or_404()

    if request.method == "POST":
        mapping = {}
        fields = DATA_TYPE_FIELDS.get(upload.data_type, {}).get("fields", {})
        for field_key in fields:
            col = request.form.get(f"map_{field_key}", "").strip()
            if col:
                mapping[field_key] = col

        upload.column_mapping["mapping"] = mapping
        upload.status = "processing"
        db.session.commit()

        upload_dir = os.path.join(current_app.config.get("UPLOAD_FOLDER", "data/output"), "analytics")
        filepath = os.path.join(upload_dir, upload.filename)

        try:
            ext = upload.filename.rsplit(".", 1)[1].lower()
            if ext == "csv":
                df = pd.read_csv(filepath, sep=None, engine="python", on_bad_lines="skip", encoding="utf-8-sig")
            else:
                df = pd.read_excel(filepath)
            df.columns = [c.strip().lstrip("\ufeff") for c in df.columns]

            records = []
            for _, row in df.iterrows():
                record_data = {}
                for field_key, col_name in mapping.items():
                    val = row.get(col_name, None)
                    if pd.isna(val):
                        val = None
                    elif isinstance(val, (int, float)):
                        val = float(val)
                    else:
                        val = str(val)
                    record_data[field_key] = val
                records.append(DataRecord(
                    upload_id=upload.id,
                    user_id=current_user.id,
                    data_type=upload.data_type,
                    data=record_data,
                ))

            db.session.bulk_save_objects(records)
            upload.row_count = len(records)
            upload.status = "processed"
            db.session.commit()

            flash(f"Berhasil import {len(records)} data!", "success")
            return redirect(url_for("analytics.dashboard", upload_id=upload.id))

        except Exception as e:
            upload.status = "error"
            upload.error_message = str(e)
            db.session.commit()
            flash(f"Gagal memproses data: {str(e)}", "error")
            return redirect(url_for("analytics.confirm_mapping", upload_id=upload.id))

    fields = DATA_TYPE_FIELDS.get(upload.data_type, {}).get("fields", {})
    columns = upload.column_mapping.get("columns", [])
    mapping = upload.column_mapping.get("mapping", {})
    return render_template("analytics/mapping.html", upload=upload, fields=fields, columns=columns, mapping=mapping)


@analytics_bp.route("/analytics/<int:upload_id>/dashboard")
@login_required
def dashboard(upload_id):
    upload = DataUpload.query.filter_by(id=upload_id, user_id=current_user.id).first_or_404()
    return render_template("analytics/dashboard.html", upload=upload, data_types=DATA_TYPE_FIELDS)


@analytics_bp.route("/analytics/<int:upload_id>/delete", methods=["POST"])
@login_required
def delete_upload(upload_id):
    upload = DataUpload.query.filter_by(id=upload_id, user_id=current_user.id).first_or_404()
    DataRecord.query.filter_by(upload_id=upload_id).delete()
    db.session.delete(upload)
    db.session.commit()
    flash("Data berhasil dihapus", "success")
    return redirect(url_for("analytics.index"))
