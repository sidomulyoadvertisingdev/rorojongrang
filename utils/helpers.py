import re
import unicodedata

from functools import wraps

from flask import redirect, url_for, flash, jsonify
from flask_login import login_required, current_user


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_phone(text: str) -> str:
    if not text:
        return ""
    text = clean_text(text)
    text = text.replace(" ", "").replace("-", "")
    match = re.search(r"(\+?62|0)[0-9]{9,13}", text)
    return match.group(0) if match else ""


def normalize_phone_for_wa(phone: str) -> str:
    if not phone:
        return ""
    digits = re.sub(r"[^0-9]", "", phone)
    if digits.startswith("62"):
        return digits
    if digits.startswith("0"):
        return "62" + digits[1:]
    if digits.startswith("+62"):
        return digits[1:]
    return digits


def extract_rating(text: str) -> float:
    if not text:
        return 0.0
    match = re.search(r"(\d+[.,]?\d*)", text)
    if match:
        return float(match.group(1).replace(",", "."))
    return 0.0


def extract_review_count(text: str) -> int:
    if not text:
        return 0
    text = text.replace(".", "").replace(",", "")
    match = re.search(r"(\d+)", text)
    return int(match.group(1)) if match else 0


RADIUS_ZOOM = {
    1: 16, 2: 15, 5: 14, 10: 13, 20: 12, 0: 11,
}


def build_search_url(keyword: str, location: str, radius_km: int = 0, lat: float = 0, lng: float = 0) -> str:
    from config.settings import GOOGLE_MAPS_BASE_URL
    query = f"{keyword} {location}"
    encoded = query.replace(" ", "+")
    zoom = RADIUS_ZOOM.get(radius_km, 14)
    if lat and lng:
        return f"{GOOGLE_MAPS_BASE_URL}/{encoded}/@{lat},{lng},{zoom}z"
    return f"{GOOGLE_MAPS_BASE_URL}/{encoded}"


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            if _wants_json():
                return jsonify({"error": "Akses ditolak."}), 403
            flash("Akses ditolak. Hanya admin yang bisa mengakses halaman ini.", "danger")
            return redirect(url_for("dashboard.index"))
        return f(*args, **kwargs)
    return decorated


def platform_admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_platform_admin:
            if _wants_json():
                return jsonify({"error": "Akses ditolak."}), 403
            flash("Akses ditolak. Hanya Admin Platform yang bisa mengakses halaman ini.", "danger")
            return redirect(url_for("dashboard.index"))
        return f(*args, **kwargs)
    return decorated


def _wants_json():
    from flask import request
    return (
        request.path.startswith("/api/")
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or "application/json" in (request.headers.get("Accept", "") or "")
    )

