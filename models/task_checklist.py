from datetime import datetime
from models import db


class TaskChecklist(db.Model):
    __tablename__ = "task_checklists"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("board_tasks.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    is_done = db.Column(db.Boolean, default=False)
    position = db.Column(db.Integer, default=0)
    done_at = db.Column(db.DateTime, nullable=True)
    done_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    user = db.relationship("User", foreign_keys=[done_by])
