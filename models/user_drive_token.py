from datetime import datetime
from models import db


class UserDriveToken(db.Model):
    __tablename__ = "user_drive_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    access_token = db.Column(db.Text, nullable=False)
    refresh_token = db.Column(db.Text, nullable=False)
    token_expiry = db.Column(db.DateTime, nullable=False)
    drive_email = db.Column(db.String(255))
    folder_id = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("drive_token", uselist=False))

    def is_expired(self):
        return datetime.utcnow() >= self.token_expiry
