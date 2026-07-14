from datetime import datetime
from models import db


class Campaign(db.Model):
    __tablename__ = "campaigns"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    start_date = db.Column(db.DateTime, nullable=True)
    end_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default="active")  # active, paused, completed
    target_leads = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    creator = db.relationship("User", backref="campaigns")
    leads = db.relationship("LeadPipeline", backref="campaign", lazy="dynamic")
    metrics = db.relationship("CampaignMetric", backref="campaign", uselist=False)

    def get_or_create_metrics(self):
        if not self.metrics:
            m = CampaignMetric(campaign_id=self.id)
            db.session.add(m)
            db.session.commit()
        return self.metrics

    def recalculate_metrics(self):
        m = self.get_or_create_metrics()
        all_leads = LeadPipeline.query.filter_by(campaign_id=self.id).all()
        m.total_leads = len(all_leads)
        m.contacted_leads = len([l for l in all_leads if l.status in ("contacted", "negotiation", "won", "lost")])
        m.responded_leads = len([l for l in all_leads if l.status in ("negotiation", "won")])
        m.won_leads = len([l for l in all_leads if l.status == "won"])
        m.lost_leads = len([l for l in all_leads if l.status == "lost"])
        m.total_value = sum(l.value or 0 for l in all_leads if l.status == "won")
        m.conversion_rate = round((m.won_leads / m.total_leads * 100) if m.total_leads > 0 else 0, 1)
        db.session.commit()
        return m


class CampaignMetric(db.Model):
    __tablename__ = "campaign_metrics"

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("campaigns.id"), unique=True, nullable=False)
    total_leads = db.Column(db.Integer, default=0)
    contacted_leads = db.Column(db.Integer, default=0)
    responded_leads = db.Column(db.Integer, default=0)
    won_leads = db.Column(db.Integer, default=0)
    lost_leads = db.Column(db.Integer, default=0)
    total_value = db.Column(db.Float, default=0)
    conversion_rate = db.Column(db.Float, default=0)
    avg_response_time = db.Column(db.Float, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
