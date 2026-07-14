from datetime import datetime
from models import db


class DataUpload(db.Model):
    __tablename__ = "data_uploads"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    data_type = db.Column(db.String(20), nullable=False)  # product, sales, customer, finance
    filename = db.Column(db.String(255), nullable=False)
    row_count = db.Column(db.Integer, default=0)
    column_mapping = db.Column(db.JSON)
    status = db.Column(db.String(20), default="pending")  # pending, processed, error
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    records = db.relationship("DataRecord", backref="upload", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "data_type": self.data_type,
            "filename": self.filename,
            "row_count": self.row_count,
            "column_mapping": self.column_mapping,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
