from datetime import datetime
from models import db


class TeamBoard(db.Model):
    __tablename__ = "team_boards"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    creator = db.relationship("User", backref="created_boards", foreign_keys=[created_by])
    columns = db.relationship("BoardColumn", backref="board", lazy="dynamic", order_by="BoardColumn.position")
    tasks = db.relationship("BoardTask", backref="board", lazy="dynamic")

    def get_column(self, name):
        return BoardColumn.query.filter_by(board_id=self.id, name=name).first()

    def task_count(self):
        return BoardTask.query.filter_by(board_id=self.id).count()

    def tasks_by_column(self, column_id):
        return BoardTask.query.filter_by(board_id=self.id, column_id=column_id).order_by(BoardTask.created_at.desc()).all()

    def assigned_users(self):
        from models.user import User
        user_ids = db.session.query(BoardTask.assigned_to).filter_by(board_id=self.id).distinct().all()
        return User.query.filter(User.id.in_([u[0] for u in user_ids if u[0]])).all()
