import json
import threading
from flask import Blueprint, Response, jsonify
from flask_login import login_required, current_user
from models import db
from models.task import ScrapingTask

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/task/<int:task_id>/status")
@login_required
def task_status(task_id):
    task = ScrapingTask.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    return jsonify(task.to_dict())


@api_bp.route("/task/<int:task_id>/progress")
@login_required
def task_progress(task_id):
    import redis as redis_lib
    redis_client = redis_lib.Redis(host="localhost", port=6379, db=0, decode_responses=True)

    def generate():
        pubsub = redis_client.pubsub()
        pubsub.subscribe(f"task:{task_id}")

        task = ScrapingTask.query.filter_by(id=task_id).first()
        if task:
            yield f"data: {json.dumps(task.to_dict())}\n\n"

        last_yield = 0
        for _ in range(600):
            task = ScrapingTask.query.filter_by(id=task_id).first()
            if not task:
                break

            now = int(__import__('time').time())
            if now - last_yield >= 1:
                yield f"data: {json.dumps(task.to_dict())}\n\n"
                last_yield = now

            if task.status in ("completed", "failed", "cancelled"):
                yield f"data: {json.dumps(task.to_dict())}\n\n"
                break

            message = pubsub.get_message(timeout=0.1)
            if message and message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    yield f"data: {json.dumps(data)}\n\n"
                except (json.JSONDecodeError, TypeError):
                    pass

        pubsub.unsubscribe()
        pubsub.close()

    return Response(generate(), mimetype="text/event-stream")


@api_bp.route("/tasks/active")
@login_required
def active_tasks():
    tasks = ScrapingTask.query.filter(
        ScrapingTask.user_id == current_user.id,
        ScrapingTask.status.in_(["pending", "running"])
    ).all()
    return jsonify([t.to_dict() for t in tasks])
