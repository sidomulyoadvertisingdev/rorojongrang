from datetime import datetime
from models import db


class CampaignAttachment(db.Model):
    __tablename__ = "campaign_attachments"

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("campaigns.id"), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    drive_file_id = db.Column(db.String(255), nullable=False)
    filename = db.Column(db.String(500), nullable=False)
    mime_type = db.Column(db.String(255))
    file_size = db.Column(db.BigInteger, default=0)
    drive_url = db.Column(db.Text)
    file_type = db.Column(db.String(50), default="other")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    campaign = db.relationship("Campaign", backref=db.backref("attachments", lazy="dynamic"))
    uploader = db.relationship("User", backref="uploaded_campaign_attachments")

    def size_display(self):
        if not self.file_size:
            return "0 B"
        units = ["B", "KB", "MB", "GB"]
        size = float(self.file_size)
        for unit in units:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def icon_svg(self):
        mime = self.mime_type or ""
        if "image" in mime:
            return '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/></svg>'
        if "pdf" in mime:
            return '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>'
        if "spreadsheet" in mime or "excel" in mime or "csv" in mime:
            return '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><path d="M8 13h2"/><path d="M8 17h2"/><path d="M14 13h2"/><path d="M14 17h2"/></svg>'
        return '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>'
