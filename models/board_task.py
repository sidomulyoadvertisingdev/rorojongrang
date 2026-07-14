from datetime import datetime
from models import db


class BoardTask(db.Model):
    __tablename__ = "board_tasks"

    id = db.Column(db.Integer, primary_key=True)
    board_id = db.Column(db.Integer, db.ForeignKey("team_boards.id"), nullable=False)
    column_id = db.Column(db.Integer, db.ForeignKey("board_columns.id"), nullable=False)
    business_id = db.Column(db.Integer, db.ForeignKey("businesses.id"), nullable=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    priority = db.Column(db.String(10), default="medium")  # low, medium, high, urgent
    assigned_to = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    assigned_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    progress_percent = db.Column(db.Float, default=0)
    due_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    assignee = db.relationship("User", foreign_keys=[assigned_to], backref="assigned_tasks")
    assigner = db.relationship("User", foreign_keys=[assigned_by], backref="created_tasks")
    business = db.relationship("Business", backref="board_tasks")
    checklists = db.relationship("TaskChecklist", backref="task", lazy="dynamic", order_by="TaskChecklist.position")
    activities = db.relationship("TaskActivity", backref="task", lazy="dynamic", order_by="TaskActivity.created_at.desc()")

    def checklist_progress(self):
        total = self.checklists.count()
        if total == 0:
            return 0
        done = self.checklists.filter_by(is_done=True).count()
        return round((done / total) * 100)

    def checklist_done_count(self):
        return self.checklists.filter_by(is_done=True).count()

    def checklist_total(self):
        return self.checklists.count()
