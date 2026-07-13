import os
import sys
import json
from flask import Flask

from models import db, login_manager
from config.web_settings import Config


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.scraper import scraper_bp
    from routes.api import api_bp
    from routes.blog import blog_bp
    from routes.wa_templates import wa_templates_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(scraper_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(blog_bp)
    app.register_blueprint(wa_templates_bp)

    with app.app_context():
        db.create_all()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5001)
