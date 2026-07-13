from datetime import datetime
from models import db


class Business(db.Model):
    __tablename__ = "businesses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    task_id = db.Column(db.Integer, db.ForeignKey("scraping_tasks.id"))
    name = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100))
    subcategory = db.Column(db.String(100))
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    district = db.Column(db.String(100))
    regency = db.Column(db.String(100))
    province = db.Column(db.String(100))
    postal_code = db.Column(db.String(10))
    phone = db.Column(db.String(50))
    website = db.Column(db.String(255))
    email = db.Column(db.String(255))
    rating = db.Column(db.Float)
    review_count = db.Column(db.Integer, default=0)
    google_maps_url = db.Column(db.Text)
    place_id = db.Column(db.String(255))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    operating_hours = db.Column(db.Text)
    scraped_at = db.Column(db.DateTime, default=datetime.utcnow)
    source_keyword = db.Column(db.String(255))
    source_location = db.Column(db.String(255))
    is_verified = db.Column(db.Boolean, default=False)
    lead_status = db.Column(db.String(30), default="new")
    lead_note = db.Column(db.Text)
    lead_score = db.Column(db.Integer, default=0)
    last_contacted_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "name": self.name,
            "category": self.category,
            "address": self.address,
            "phone": self.phone,
            "website": self.website,
            "email": self.email,
            "rating": self.rating,
            "review_count": self.review_count,
            "google_maps_url": self.google_maps_url,
            "place_id": self.place_id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "operating_hours": self.operating_hours,
            "source_keyword": self.source_keyword,
            "source_location": self.source_location,
            "lead_status": self.lead_status or "new",
            "lead_note": self.lead_note,
            "lead_score": self.lead_score or 0,
            "last_contacted_at": self.last_contacted_at.isoformat() if self.last_contacted_at else None,
            "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None,
        }
