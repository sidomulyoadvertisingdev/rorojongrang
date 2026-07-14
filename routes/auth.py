from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, session
from flask_login import login_user, logout_user, login_required, current_user
from authlib.integrations.flask_client import OAuth
from models import db
from models.user import User

auth_bp = Blueprint("auth", __name__)
oauth = OAuth()

oauth.register(
    name="google",
    client_id="",
    client_secret="",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


def _init_google_oauth(app):
    oauth.init_app(app)
    oauth.register(
        name="google",
        client_id=app.config.get("GOOGLE_CLIENT_ID", ""),
        client_secret=app.config.get("GOOGLE_CLIENT_SECRET", ""),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if user and user.is_banned:
            flash("Akun Anda telah dibanned. Hubungi admin untuk informasi lebih lanjut.", "danger")
            return render_template("auth/login.html")

        if user and user.check_password(password):
            login_user(user, remember=True)
            user.last_login = datetime.utcnow()
            db.session.commit()
            flash("Selamat datang kembali!", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("dashboard.index"))
        else:
            flash("Email atau password salah", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        full_name = request.form.get("full_name", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        errors = []
        if len(username) < 3:
            errors.append("Username minimal 3 karakter")
        if len(password) < 6:
            errors.append("Password minimal 6 karakter")
        if password != confirm:
            errors.append("Password tidak cocok")
        if User.query.filter_by(username=username).first():
            errors.append("Username sudah digunakan")
        if User.query.filter_by(email=email).first():
            errors.append("Email sudah terdaftar")

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template("auth/register.html")

        user = User(username=username, email=email, full_name=full_name)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash("Registrasi berhasil! Silakan login", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Anda telah logout", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/login/google")
def google_login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    google = oauth.create_client("google")
    redirect_uri = url_for("auth.google_callback", _external=True)
    return google.authorize_redirect(redirect_uri)


@auth_bp.route("/login/google/callback")
def google_callback():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    google = oauth.create_client("google")
    try:
        token = google.authorize_access_token()
    except Exception:
        flash("Gagal login dengan Google. Silakan coba lagi.", "danger")
        return redirect(url_for("auth.login"))

    user_info = token.get("userinfo")
    if not user_info:
        try:
            user_info = google.get("userinfo").json()
        except Exception:
            flash("Gagal mengambil data dari Google.", "danger")
            return redirect(url_for("auth.login"))

    google_id = user_info.get("sub") or user_info.get("id")
    email = user_info.get("email")
    name = user_info.get("name", "")
    avatar = user_info.get("picture", "")

    if not email:
        flash("Email tidak ditemukan dari akun Google.", "danger")
        return redirect(url_for("auth.login"))

    user = User.query.filter_by(google_id=google_id).first()

    if not user:
        user = User.query.filter_by(email=email).first()

    if user and user.is_banned:
        flash("Akun Anda telah dibanned. Hubungi admin untuk informasi lebih lanjut.", "danger")
        return redirect(url_for("auth.login"))

    if user:
        user.google_id = google_id
        if avatar:
            user.avatar_url = avatar
        if name and not user.full_name:
            user.full_name = name
        user.last_login = datetime.utcnow()
        db.session.commit()
    else:
        base_username = email.split("@")[0]
        username = base_username
        counter = 1
        while User.query.filter_by(username=username).first():
            username = f"{base_username}{counter}"
            counter += 1

        user = User(
            username=username,
            email=email,
            full_name=name,
            avatar_url=avatar,
            google_id=google_id,
        )
        db.session.add(user)
        db.session.commit()

    login_user(user, remember=True)
    flash("Selamat datang, " + (user.full_name or user.username) + "!", "success")
    next_page = request.args.get("next")
    return redirect(next_page or url_for("dashboard.index"))
