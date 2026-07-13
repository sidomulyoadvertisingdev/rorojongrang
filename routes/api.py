import json
import threading
from flask import Blueprint, Response, current_app, jsonify, request
from flask_login import login_required, current_user
from models import db
from models.task import ScrapingTask
from models.business import Business
from models.wa_template import WaTemplate
from models.wa_link import WaLink
from models.wa_click import WaClick

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/task/<int:task_id>/status")
@login_required
def task_status(task_id):
    task = ScrapingTask.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    return jsonify(task.to_dict())


@api_bp.route("/task/<int:task_id>/businesses")
@login_required
def task_businesses(task_id):
    task = ScrapingTask.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    page = request.args.get("page", 1, type=int)
    search = request.args.get("q", "").strip()
    query = Business.query.filter_by(task_id=task_id)
    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(
                Business.name.ilike(like),
                Business.phone.ilike(like),
                Business.address.ilike(like),
                Business.category.ilike(like),
            )
        )
    query = query.order_by(Business.id.asc())
    paginated = query.paginate(page=page, per_page=25, error_out=False)
    return jsonify({
        "businesses": [b.to_dict() for b in paginated.items],
        "total": paginated.total,
        "page": paginated.page,
        "pages": paginated.pages,
    })


@api_bp.route("/task/<int:task_id>/wa-data")
@login_required
def task_wa_data(task_id):
    task = ScrapingTask.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    templates = WaTemplate.query.filter_by(user_id=current_user.id, is_active=True).all()
    template_list = []
    for t in templates:
        links = WaLink.query.filter_by(template_id=t.id, is_active=True).all()
        template_list.append({
            "id": t.id,
            "name": t.name,
            "message": t.message,
            "links": [{"id": l.id, "name": l.name, "url": l.url} for l in links],
        })
    clicks = WaClick.query.filter_by(user_id=current_user.id, task_id=task_id)\
        .order_by(WaClick.clicked_at.desc()).all()
    click_list = []
    for c in clicks:
        click_list.append({
            "business_id": c.business_id,
            "template_id": c.template_id,
            "template_name": c.template.name if c.template else None,
            "link_id": c.link_id,
            "link_name": c.link.name if c.link else None,
            "phone": c.phone,
            "clicked_at": c.clicked_at.isoformat() if c.clicked_at else None,
        })
    return jsonify({"templates": template_list, "clicks": click_list})


@api_bp.route("/task/<int:task_id>/stream")
@login_required
def task_stream(task_id):
    import redis as redis_lib
    redis_client = redis_lib.Redis(host="localhost", port=6379, db=0, decode_responses=True)
    app = current_app._get_current_object()

    def generate():
        with app.app_context():
            pubsub = redis_client.pubsub()
            pubsub.subscribe(f"task:{task_id}")
            pubsub.subscribe(f"task:{task_id}:logs")

            task = ScrapingTask.query.filter_by(id=task_id).first()
            if task:
                yield f"data: {json.dumps(task.to_dict())}\n\n"

            for _ in range(600):
                task = ScrapingTask.query.filter_by(id=task_id).first()
                if not task:
                    break

                if task.status in ("completed", "failed", "cancelled"):
                    yield f"data: {json.dumps(task.to_dict())}\n\n"
                    break

                message = pubsub.get_message(timeout=0.5)
                if message and message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        yield f"data: {json.dumps(data)}\n\n"
                    except (json.JSONDecodeError, TypeError):
                        pass

            pubsub.unsubscribe()
            pubsub.close()

    response = Response(generate(), mimetype="text/event-stream")
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    response.headers['Connection'] = 'keep-alive'
    return response


@api_bp.route("/task/<int:task_id>/progress")
@login_required
def task_progress(task_id):
    import redis as redis_lib
    redis_client = redis_lib.Redis(host="localhost", port=6379, db=0, decode_responses=True)
    app = current_app._get_current_object()

    def generate():
        with app.app_context():
            pubsub = redis_client.pubsub()
            pubsub.subscribe(f"task:{task_id}")

            task = ScrapingTask.query.filter_by(id=task_id).first()
            if task:
                yield f"data: {json.dumps(task.to_dict())}\n\n"

            last_yield = 0
            for _ in range(3600):
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

    response = Response(generate(), mimetype="text/event-stream")
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    response.headers['Connection'] = 'keep-alive'
    return response


@api_bp.route("/tasks/active")
@login_required
def active_tasks():
    tasks = ScrapingTask.query.filter(
        ScrapingTask.user_id == current_user.id,
        ScrapingTask.status.in_(["pending", "running"])
    ).all()
    return jsonify([t.to_dict() for t in tasks])


@api_bp.route("/businesses/delete", methods=["POST"])
@login_required
def delete_businesses():
    data = request.get_json()
    ids = data.get("ids", [])
    if not ids:
        return jsonify({"error": "No IDs provided"}), 400
    deleted = Business.query.filter(
        Business.id.in_(ids),
        Business.user_id == current_user.id,
    ).delete(synchronize_session=False)
    db.session.commit()
    return jsonify({"deleted": deleted})
