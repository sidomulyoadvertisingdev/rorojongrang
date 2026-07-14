import os
import sys
import json
from flask import Flask, jsonify, redirect, request, url_for

from storage.bootstrap import bootstrap_database
from models import db, login_manager
from config.web_settings import Config


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.unauthorized_handler
    def unauthorized():
        wants_json = (
            request.path.startswith("/api/")
            or request.path == "/scrape"
            or request.accept_mimetypes.accept_json
            or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        )
        if wants_json:
            return jsonify({"error": "Sesi login habis. Silakan login ulang."}), 401
        return redirect(url_for("auth.login"))

    bootstrap_database(app)

    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.scraper import scraper_bp
    from routes.api import api_bp
    from routes.blog import blog_bp
    from routes.wa_templates import wa_templates_bp
    from routes.analytics import analytics_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(scraper_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(blog_bp)
    app.register_blueprint(wa_templates_bp)
    app.register_blueprint(analytics_bp)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5001)
