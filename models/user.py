from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from models import db, login_manager


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
    full_name = db.Column(db.String(100))
    avatar_url = db.Column(db.String(500))
    google_id = db.Column(db.String(100), unique=True, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    role = db.Column(db.String(20), default="user", nullable=False)
    is_banned = db.Column(db.Boolean, default=False)
    banned_at = db.Column(db.DateTime)
    banned_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    ROLE_USER = "user"
    ROLE_ADMIN = "admin"
    ROLE_PLATFORM_ADMIN = "platform_admin"

    tasks = db.relationship("ScrapingTask", backref="user", lazy="dynamic")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256")

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role in (self.ROLE_ADMIN, self.ROLE_PLATFORM_ADMIN)

    @property
    def is_platform_admin(self):
        return self.role == self.ROLE_PLATFORM_ADMIN

    def can_manage(self, target):
        if not self.is_admin:
            return False
        if self.is_platform_admin:
            return True
        return not target.is_admin

    def get_task_count(self):
        return self.tasks.count()

    def get_total_scraped(self):
        from models.task import ScrapingTask
        result = db.session.query(
            db.func.coalesce(db.func.sum(ScrapingTask.scraped_results), 0)
        ).filter(ScrapingTask.user_id == self.id, ScrapingTask.status == "completed").scalar()
        return result

    def get_running_tasks(self):
        return self.tasks.filter(
            ScrapingTask.status.in_(["pending", "running"])
        ).count()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
