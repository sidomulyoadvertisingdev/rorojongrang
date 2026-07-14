from datetime import datetime
from models import db


class LeadPipeline(db.Model):
    __tablename__ = "lead_pipelines"

    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey("businesses.id"), nullable=False)
    status = db.Column(db.String(20), default="new")  # new, contacted, negotiation, won, lost
    assigned_to = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    assigned_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    priority = db.Column(db.String(10), default="medium")  # low, medium, high, urgent
    notes = db.Column(db.Text)
    value = db.Column(db.Float, default=0)
    due_date = db.Column(db.DateTime, nullable=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("campaigns.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = db.Column(db.DateTime, nullable=True)

    business = db.relationship("Business", backref="leads")
    assignee = db.relationship("User", foreign_keys=[assigned_to], backref="assigned_leads")
    assigner = db.relationship("User", foreign_keys=[assigned_by], backref="created_leads")
    activities = db.relationship("LeadActivity", backref="lead", lazy="dynamic", order_by="LeadActivity.created_at.desc()")
    followups = db.relationship("FollowUp", backref="lead", lazy="dynamic")

    def activity_count(self):
        return LeadActivity.query.filter_by(lead_id=self.id).count()

    def last_activity(self):
        return LeadActivity.query.filter_by(lead_id=self.id).order_by(LeadActivity.created_at.desc()).first()
