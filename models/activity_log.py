from datetime import datetime
from models import db


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    target = db.Column(db.String(255))
    detail = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", foreign_keys=[user_id], backref="activity_logs_received")
    admin = db.relationship("User", foreign_keys=[admin_id], backref="activity_logs_performed")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "admin_id": self.admin_id,
            "action": self.action,
            "target": self.target,
            "detail": self.detail,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
