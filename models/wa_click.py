from datetime import datetime
from models import db


class WaClick(db.Model):
    __tablename__ = "wa_clicks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    business_id = db.Column(db.Integer, db.ForeignKey("businesses.id"), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey("scraping_tasks.id"), nullable=True)
    template_id = db.Column(db.Integer, db.ForeignKey("wa_templates.id"), nullable=False)
    link_id = db.Column(db.Integer, db.ForeignKey("wa_links.id"), nullable=True)
    phone = db.Column(db.String(50))
    clicked_at = db.Column(db.DateTime, default=datetime.utcnow)

    business = db.relationship("Business", backref="wa_clicks")
    link = db.relationship("WaLink", backref="clicks")

    def to_dict(self):
        return {
            "id": self.id,
            "business_id": self.business_id,
            "template_id": self.template_id,
            "link_id": self.link_id,
            "phone": self.phone,
            "clicked_at": self.clicked_at.isoformat() if self.clicked_at else None,
            "template_name": self.template.name if self.template else None,
            "link_name": self.link.name if self.link else None,
        }
