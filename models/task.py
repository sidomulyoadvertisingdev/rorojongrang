from datetime import datetime
from models import db


class ScrapingTask(db.Model):
    __tablename__ = "scraping_tasks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    keyword = db.Column(db.String(255), nullable=False)
    location = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100))
    status = db.Column(
        db.Enum("pending", "running", "completed", "failed", "cancelled"),
        default="pending",
    )
    total_results = db.Column(db.Integer, default=0)
    scraped_results = db.Column(db.Integer, default=0)
    progress_percent = db.Column(db.Float, default=0)
    current_log = db.Column(db.Text)
    error_message = db.Column(db.Text)
    celery_task_id = db.Column(db.String(255))
    search_radius = db.Column(db.Integer, default=5)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    businesses = db.relationship("Business", backref="task", lazy="dynamic")

    def get_business_count(self):
        return self.businesses.count()

    def update_progress(self, scraped, total):
        self.scraped_results = scraped
        self.total_results = total
        self.progress_percent = (scraped / total * 100) if total > 0 else 0
        db.session.commit()

    def to_dict(self):
        return {
            "id": self.id,
            "keyword": self.keyword,
            "location": self.location,
            "category": self.category,
            "search_radius": self.search_radius,
            "status": self.status,
            "total_results": self.total_results,
            "scraped_results": self.scraped_results,
            "progress_percent": self.progress_percent,
            "current_log": self.current_log,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
