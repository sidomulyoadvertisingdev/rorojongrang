"""Create admin user if not exists."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db
from models.user import User

ADMIN_EMAIL = "admin@admin.com"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
ADMIN_NAME = "Administrator"


def seed():
    app = create_app()
    with app.app_context():
        existing = User.query.filter(
            db.or_(User.email == ADMIN_EMAIL, User.username == ADMIN_USERNAME)
        ).first()
        if existing:
            print(f"  [=] Admin sudah ada: {existing.email} (username: {existing.username})")
            if existing.email != ADMIN_EMAIL or not existing.is_admin:
                existing.email = ADMIN_EMAIL
                existing.full_name = ADMIN_NAME
                existing.is_admin = True
                existing.set_password(ADMIN_PASSWORD)
                db.session.commit()
                print(f"  [~] Admin diupdate: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
            return

        user = User(
            username=ADMIN_USERNAME,
            email=ADMIN_EMAIL,
            full_name=ADMIN_NAME,
            is_admin=True,
        )
        user.set_password(ADMIN_PASSWORD)
        db.session.add(user)
        db.session.commit()
        print(f"  [+] Admin dibuat: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")


if __name__ == "__main__":
    seed()
