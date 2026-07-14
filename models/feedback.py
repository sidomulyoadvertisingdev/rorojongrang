from datetime import datetime
from models import db


class Feedback(db.Model):
    __tablename__ = 'feedbacks'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    category = db.Column(db.String(20), nullable=False, default='feature')  # feature, complaint, suggestion
    message = db.Column(db.Text, nullable=False)
    contact_email = db.Column(db.String(120), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    admin_reply = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='feedbacks', lazy=True)

    def __repr__(self):
        return f'<Feedback {self.id}: {self.category}>'
