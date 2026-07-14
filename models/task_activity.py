from datetime import datetime
from models import db


class TaskActivity(db.Model):
    __tablename__ = "task_activities"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("board_tasks.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    action = db.Column(db.String(50), nullable=False)  # moved, checklist, comment, assigned, progress, created
    detail = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="task_activities")
