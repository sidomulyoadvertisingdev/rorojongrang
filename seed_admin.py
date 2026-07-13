"""Create default admin user if not exists."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db
from models.user import User

def seed():
    admin_username = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
    admin_email = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@rorojonggrang.com")
    admin_password = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")
    admin_name = os.getenv("DEFAULT_ADMIN_FULL_NAME", "Administrator")

    app = create_app()
    with app.app_context():
        existing = User.query.filter(
            db.or_(User.email == admin_email, User.username == admin_username)
        ).first()
        if existing:
            print(f"  [=] Admin sudah ada: {existing.email} (username: {existing.username})")
            if existing.email != admin_email or not existing.is_admin:
                existing.email = admin_email
                existing.full_name = admin_name
                existing.is_admin = True
                existing.set_password(admin_password)
                db.session.commit()
                print(f"  [~] Admin diupdate: {admin_email} / {admin_password}")
            return

        user = User(
            username=admin_username,
            email=admin_email,
            full_name=admin_name,
            is_admin=True,
        )
        user.set_password(admin_password)
        db.session.add(user)
        db.session.commit()
        print(f"  [+] Admin dibuat: {admin_email} / {admin_password}")


if __name__ == "__main__":
    seed()
