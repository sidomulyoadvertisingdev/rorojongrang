from models import db


class BoardColumn(db.Model):
    __tablename__ = "board_columns"

    id = db.Column(db.Integer, primary_key=True)
    board_id = db.Column(db.Integer, db.ForeignKey("team_boards.id"), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    position = db.Column(db.Integer, default=0)
    color = db.Column(db.String(20), default="#6b6480")
    icon = db.Column(db.String(30), default="circle")

    tasks = db.relationship("BoardTask", backref="column", lazy="dynamic")

    def task_count(self):
        return BoardTask.query.filter_by(column_id=self.id).count()
