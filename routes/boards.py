from datetime import datetime
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from models import db
from models.team_board import TeamBoard
from models.board_column import BoardColumn
from models.board_task import BoardTask
from models.task_checklist import TaskChecklist
from models.task_activity import TaskActivity
from models.task_attachment import TaskAttachment
from models.user_drive_token import UserDriveToken
from models.business import Business
from models.user import User

boards_bp = Blueprint("boards", __name__)


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            flash("Akses ditolak.", "danger")
            return redirect(url_for("boards.board_list"))
        return f(*args, **kwargs)
    return decorated


def _log_activity(task_id, action, detail=""):
    log = TaskActivity(task_id=task_id, user_id=current_user.id, action=action, detail=detail)
    db.session.add(log)


def _can_access_board(board):
    if current_user.is_admin:
        return True
    assigned_ids = [t.assigned_to for t in BoardTask.query.filter_by(board_id=board.id).all() if t.assigned_to]
    return current_user.id in assigned_ids


def _can_access_task(task):
    if current_user.is_admin:
        return True
    return task.assigned_to == current_user.id


DEFAULT_COLUMNS = [
    {"name": "Backlog", "position": 0, "color": "#6b6480", "icon": "inbox"},
    {"name": "To Do", "position": 1, "color": "#f59e0b", "icon": "circle"},
    {"name": "In Progress", "position": 2, "color": "#3b82f6", "icon": "play"},
    {"name": "Review", "position": 3, "color": "#a855f7", "icon": "eye"},
    {"name": "Done", "position": 4, "color": "#22c55e", "icon": "check"},
]

DEFAULT_CHECKLIST = [
    "Hubungi via WhatsApp",
    "Kirim penawaran",
    "Follow up",
    "Survey lokasi",
    "Closing",
]


@boards_bp.route("/boards")
@login_required
def board_list():
    if current_user.is_admin:
        boards = TeamBoard.query.filter_by(is_active=True).order_by(TeamBoard.created_at.desc()).all()
    else:
        task_board_ids = db.session.query(BoardTask.board_id).filter_by(assigned_to=current_user.id).distinct().all()
        board_ids = [b[0] for b in task_board_ids]
        boards = TeamBoard.query.filter(TeamBoard.id.in_(board_ids), TeamBoard.is_active == True).all()
    users = User.query.filter_by(is_active=True).all()
    return render_template("boards/list.html", boards=boards, users=users)


@boards_bp.route("/boards/create", methods=["POST"])
@admin_required
def create_board():
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    if not name:
        flash("Nama board tidak boleh kosong.", "danger")
        return redirect(url_for("boards.board_list"))

    board = TeamBoard(name=name, description=description, created_by=current_user.id)
    db.session.add(board)
    db.session.flush()

    for col in DEFAULT_COLUMNS:
        c = BoardColumn(board_id=board.id, name=col["name"], position=col["position"], color=col["color"], icon=col["icon"])
        db.session.add(c)

    db.session.commit()
    flash(f"Board '{name}' berhasil dibuat!", "success")
    return redirect(url_for("boards.view_board", board_id=board.id))


@boards_bp.route("/boards/<int:board_id>")
@login_required
def view_board(board_id):
    board = TeamBoard.query.get_or_404(board_id)
    if not _can_access_board(board):
        flash("Akses ditolak.", "danger")
        return redirect(url_for("boards.board_list"))
    columns = BoardColumn.query.filter_by(board_id=board.id).order_by(BoardColumn.position).all()
    tasks_by_col = {}
    for col in columns:
        tasks_by_col[col.id] = BoardTask.query.filter_by(board_id=board.id, column_id=col.id).order_by(BoardTask.created_at.desc()).all()
    users = User.query.filter_by(is_active=True).all()
    return render_template("boards/board.html", board=board, columns=columns, tasks_by_col=tasks_by_col, users=users)


@boards_bp.route("/boards/<int:board_id>/files")
@login_required
def view_board_files(board_id):
    board = TeamBoard.query.get_or_404(board_id)
    if not _can_access_board(board):
        flash("Akses ditolak.", "danger")
        return redirect(url_for("boards.board_list"))
    task_ids = db.session.query(BoardTask.id).filter_by(board_id=board.id).subquery()
    attachments = TaskAttachment.query.filter(TaskAttachment.task_id.in_(db.session.query(task_ids))).order_by(TaskAttachment.created_at.desc()).all()
    task_map = {t.id: t for t in BoardTask.query.filter_by(board_id=board.id).all()}
    users = User.query.filter_by(is_active=True).all()
    drive_token = UserDriveToken.query.filter_by(user_id=current_user.id).first()
    return render_template("boards/board_files.html", board=board, attachments=attachments, task_map=task_map, users=users, drive_token=drive_token)


@boards_bp.route("/boards/<int:board_id>/task/create", methods=["GET", "POST"])
@admin_required
def create_task(board_id):
    board = TeamBoard.query.get_or_404(board_id)

    if request.method == "POST":
        source = request.form.get("source", "manual")
        column_id = request.form.get("column_id", type=int)
        assigned_to = request.form.get("assigned_to", type=int)
        priority = request.form.get("priority", "medium")
        due_date_str = request.form.get("due_date", "")
        due_date = datetime.strptime(due_date_str, "%Y-%m-%d") if due_date_str else None

        if not column_id:
            backlog = BoardColumn.query.filter_by(board_id=board.id, name="Backlog").first()
            column_id = backlog.id if backlog else BoardColumn.query.filter_by(board_id=board.id).first().id

        if source == "scraping":
            business_id = request.form.get("business_id", type=int)
            business = Business.query.get(business_id)
            if not business:
                flash("Data bisnis tidak ditemukan.", "danger")
                return redirect(url_for("boards.create_task", board_id=board.id))
            title = business.name
            desc_parts = []
            if business.address:
                desc_parts.append(f"Alamat: {business.address}")
            if business.phone:
                desc_parts.append(f"Telp: {business.phone}")
            if business.rating:
                desc_parts.append(f"Rating: {business.rating}")
            description = "\n".join(desc_parts)
        else:
            title = request.form.get("title", "").strip()
            description = request.form.get("description", "").strip()
            business_id = None
            if not title:
                flash("Judul task tidak boleh kosong.", "danger")
                return redirect(url_for("boards.create_task", board_id=board.id))

        task = BoardTask(
            board_id=board.id,
            column_id=column_id,
            business_id=business_id,
            title=title,
            description=description,
            priority=priority,
            assigned_to=assigned_to,
            assigned_by=current_user.id,
            due_date=due_date,
        )
        db.session.add(task)
        db.session.flush()

        for i, item in enumerate(DEFAULT_CHECKLIST):
            cl = TaskChecklist(task_id=task.id, title=item, position=i)
            db.session.add(cl)

        _log_activity(task.id, "created", f"Task '{title}' dibuat")
        if assigned_to:
            _log_activity(task.id, "assigned", f"Di-assign ke {User.query.get(assigned_to).username}")

        db.session.commit()
        flash(f"Task '{title}' berhasil dibuat!", "success")
        return redirect(url_for("boards.view_board", board_id=board.id))

    default_col = BoardColumn.query.filter_by(board_id=board.id, name="Backlog").first()
    users = User.query.filter_by(is_active=True).all()
    return render_template("boards/create_task.html", board=board, default_col=default_col, users=users)


@boards_bp.route("/boards/<int:board_id>/task/<int:task_id>")
@login_required
def task_detail(board_id, task_id):
    board = TeamBoard.query.get_or_404(board_id)
    task = BoardTask.query.get_or_404(task_id)
    if not _can_access_task(task):
        flash("Akses ditolak.", "danger")
        return redirect(url_for("boards.view_board", board_id=board.id))
    columns = BoardColumn.query.filter_by(board_id=board.id).order_by(BoardColumn.position).all()
    activities = TaskActivity.query.filter_by(task_id=task.id).order_by(TaskActivity.created_at.desc()).all()
    attachments = TaskAttachment.query.filter_by(task_id=task.id).order_by(TaskAttachment.created_at.desc()).all()
    users = User.query.filter_by(is_active=True).all()
    drive_token = UserDriveToken.query.filter_by(user_id=current_user.id).first()
    return render_template("boards/task_detail.html", board=board, task=task, columns=columns, activities=activities, attachments=attachments, drive_token=drive_token, users=users, now=datetime.utcnow())


@boards_bp.route("/api/boards/<int:board_id>/task/move", methods=["POST"])
@login_required
def move_task(board_id):
    data = request.get_json()
    task_id = data.get("task_id")
    column_id = data.get("column_id")
    task = BoardTask.query.get_or_404(task_id)
    if not _can_access_task(task):
        return jsonify({"error": "Akses ditolak"}), 403
    old_col = BoardColumn.query.get(task.column_id)
    new_col = BoardColumn.query.get(column_id)
    task.column_id = column_id
    _log_activity(task.id, "moved", f"Dipindah dari '{old_col.name}' ke '{new_col.name}'")
    db.session.commit()
    return jsonify({"ok": True})


@boards_bp.route("/api/boards/<int:board_id>/task/<int:task_id>/checklist", methods=["POST"])
@login_required
def toggle_checklist(board_id, task_id):
    data = request.get_json()
    item_id = data.get("item_id")
    item = TaskChecklist.query.get_or_404(item_id)
    if item.task_id != task_id:
        return jsonify({"error": "Invalid"}), 400
    item.is_done = not item.is_done
    if item.is_done:
        item.done_at = datetime.utcnow()
        item.done_by = current_user.id
        _log_activity(task_id, "checklist", f"Centang '{item.title}'")
    else:
        item.done_at = None
        item.done_by = None
        _log_activity(task_id, "checklist", f"Batal centang '{item.title}'")

    task = BoardTask.query.get(task_id)
    task.progress_percent = task.checklist_progress()
    db.session.commit()
    return jsonify({"ok": True, "is_done": item.is_done, "progress": task.progress_percent})


@boards_bp.route("/api/boards/<int:board_id>/task/<int:task_id>/checklist/add", methods=["POST"])
@login_required
def add_checklist(board_id, task_id):
    data = request.get_json()
    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "Judul kosong"}), 400
    task = BoardTask.query.get_or_404(task_id)
    max_pos = db.session.query(db.func.max(TaskChecklist.position)).filter_by(task_id=task.id).scalar() or 0
    item = TaskChecklist(task_id=task.id, title=title, position=max_pos + 1)
    db.session.add(item)
    _log_activity(task_id, "checklist", f"Tambah checklist '{title}'")
    db.session.commit()
    return jsonify({"ok": True, "id": item.id, "title": item.title})


@boards_bp.route("/api/boards/<int:board_id>/task/<int:task_id>/comment", methods=["POST"])
@login_required
def add_comment(board_id, task_id):
    task = BoardTask.query.get_or_404(task_id)
    message = ""
    file = request.files.get("file")

    if request.content_type and "multipart/form-data" in request.content_type:
        message = request.form.get("message", "").strip()
    else:
        data = request.get_json(silent=True) or {}
        message = data.get("message", "").strip()

    if not message and not file:
        return jsonify({"error": "Pesan kosong"}), 400

    detail = message if message else "Melampirkan file"

    if file and file.filename:
        token = UserDriveToken.query.filter_by(user_id=current_user.id).first()
        if not token:
            return jsonify({"error": "Google Drive belum terhubung"}), 400
        file_data = file.read()
        if len(file_data) > MAX_FILE_SIZE:
            return jsonify({"error": "File terlalu besar (maks 25MB)"}), 400
        try:
            from helpers.drive import upload_file_to_drive, share_file_anyone
            board = TeamBoard.query.get(board_id)
            result = upload_file_to_drive(token, file_data, file.filename, file.content_type, board_name=board.name if board else None)
            drive_file_id = result.get("id", "")
            share_file_anyone(token, drive_file_id)
            att = TaskAttachment(
                task_id=task.id,
                uploaded_by=current_user.id,
                drive_file_id=drive_file_id,
                filename=file.filename,
                mime_type=file.content_type,
                file_size=len(file_data),
                drive_url=f"https://drive.google.com/file/d/{drive_file_id}/view",
            )
            db.session.add(att)
            if message:
                detail = f"{message} [file: {file.filename}]"
            else:
                detail = f"Lampirkan file '{file.filename}'"
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"Gagal upload: {str(e)}"}), 500

    _log_activity(task_id, "comment", detail)
    db.session.commit()
    return jsonify({"ok": True, "user": current_user.full_name or current_user.username})


@boards_bp.route("/api/boards/<int:board_id>/task/<int:task_id>/progress", methods=["POST"])
@login_required
def update_progress(board_id, task_id):
    data = request.get_json()
    progress = data.get("progress", 0)
    task = BoardTask.query.get_or_404(task_id)
    task.progress_percent = min(100, max(0, float(progress)))
    _log_activity(task_id, "progress", f"Progress diupdate ke {task.progress_percent}%")
    db.session.commit()
    return jsonify({"ok": True, "progress": task.progress_percent})


@boards_bp.route("/api/boards/<int:board_id>/task/<int:task_id>/reassign", methods=["POST"])
@login_required
def reassign_task(board_id, task_id):
    if not current_user.is_admin:
        return jsonify({"error": "Akses ditolak"}), 403
    data = request.get_json()
    user_id = data.get("user_id")
    task = BoardTask.query.get_or_404(task_id)
    task.assigned_to = user_id
    user = User.query.get(user_id) if user_id else None
    _log_activity(task_id, "assigned", f"Di-assign ke {user.username if user else 'tidak ada'}")
    db.session.commit()
    return jsonify({"ok": True})


@boards_bp.route("/api/boards/<int:board_id>/task/<int:task_id>/priority", methods=["POST"])
@login_required
def update_priority(board_id, task_id):
    if not current_user.is_admin:
        return jsonify({"error": "Akses ditolak"}), 403
    data = request.get_json()
    priority = data.get("priority", "medium")
    task = BoardTask.query.get_or_404(task_id)
    task.priority = priority
    _log_activity(task_id, "priority", f"Prioritas diubah ke {priority}")
    db.session.commit()
    return jsonify({"ok": True})


@boards_bp.route("/api/boards/<int:board_id>/task/<int:task_id>/delete", methods=["POST"])
@login_required
def delete_task(board_id, task_id):
    if not current_user.is_admin:
        return jsonify({"error": "Akses ditolak"}), 403
    task = BoardTask.query.get_or_404(task_id)

    attachments = TaskAttachment.query.filter_by(task_id=task.id).all()
    for att in attachments:
        try:
            token = UserDriveToken.query.filter_by(user_id=att.uploaded_by).first()
            if token and att.drive_file_id:
                from helpers.drive import delete_file_from_drive
                delete_file_from_drive(token, att.drive_file_id)
        except Exception:
            pass
    TaskAttachment.query.filter_by(task_id=task.id).delete()

    TaskChecklist.query.filter_by(task_id=task.id).delete()
    TaskActivity.query.filter_by(task_id=task.id).delete()
    db.session.delete(task)
    db.session.commit()
    return jsonify({"ok": True})


@boards_bp.route("/api/boards/search-business")
@login_required
def search_business():
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify([])
    businesses = Business.query.filter(
        Business.user_id == current_user.id,
        Business.name.ilike(f"%{q}%")
    ).limit(10).all()
    results = [{"id": b.id, "name": b.name, "address": b.address or "", "phone": b.phone or "", "rating": b.rating or 0} for b in businesses]
    return jsonify(results)


MAX_FILE_SIZE = 25 * 1024 * 1024


@boards_bp.route("/api/boards/<int:board_id>/task/<int:task_id>/upload", methods=["POST"])
@login_required
def upload_attachment(board_id, task_id):
    task = BoardTask.query.get_or_404(task_id)
    if not _can_access_task(task):
        return jsonify({"error": "Akses ditolak"}), 403

    token = UserDriveToken.query.filter_by(user_id=current_user.id).first()
    if not token:
        return jsonify({"error": "Google Drive belum terhubung. Hubungkan di profil Anda."}), 400

    if "file" not in request.files:
        return jsonify({"error": "Tidak ada file"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Filename kosong"}), 400

    file_data = file.read()
    if len(file_data) > MAX_FILE_SIZE:
        return jsonify({"error": "File terlalu besar (maks 25MB)"}), 400

    try:
        from helpers.drive import upload_file_to_drive, share_file_anyone
        board = TeamBoard.query.get(board_id)
        result = upload_file_to_drive(
            token, file_data, file.filename, file.content_type,
            board_name=board.name if board else None
        )

        drive_file_id = result.get("id", "")
        share_file_anyone(token, drive_file_id)

        att = TaskAttachment(
            task_id=task.id,
            uploaded_by=current_user.id,
            drive_file_id=drive_file_id,
            filename=file.filename,
            mime_type=file.content_type,
            file_size=len(file_data),
            drive_url=f"https://drive.google.com/file/d/{drive_file_id}/view",
        )
        db.session.add(att)
        _log_activity(task.id, "upload", f"Lampirkan file '{file.filename}'")
        db.session.commit()

        return jsonify({
            "ok": True,
            "id": att.id,
            "filename": att.filename,
            "size": att.size_display(),
            "mime_type": att.mime_type,
            "url": att.drive_url,
            "uploaded_by": current_user.full_name or current_user.username,
            "created_at": att.created_at.strftime("%d %b %Y %H:%M"),
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Gagal upload: {str(e)}"}), 500


@boards_bp.route("/api/boards/<int:board_id>/task/<int:task_id>/attachments")
@login_required
def list_attachments(board_id, task_id):
    task = BoardTask.query.get_or_404(task_id)
    if not _can_access_task(task):
        return jsonify({"error": "Akses ditolak"}), 403

    attachments = TaskAttachment.query.filter_by(task_id=task.id).order_by(TaskAttachment.created_at.desc()).all()
    result = []
    for att in attachments:
        result.append({
            "id": att.id,
            "filename": att.filename,
            "size": att.size_display(),
            "mime_type": att.mime_type,
            "url": att.drive_url,
            "uploaded_by": att.uploader.full_name or att.uploader.username if att.uploader else "Unknown",
            "created_at": att.created_at.strftime("%d %b %Y %H:%M"),
        })
    return jsonify(result)


@boards_bp.route("/api/boards/<int:board_id>/task/<int:task_id>/attachment/<int:att_id>/delete", methods=["POST"])
@login_required
def delete_attachment(board_id, task_id, att_id):
    task = BoardTask.query.get_or_404(task_id)
    if not _can_access_task(task):
        return jsonify({"error": "Akses ditolak"}), 403

    att = TaskAttachment.query.get_or_404(att_id)
    if att.task_id != task.id:
        return jsonify({"error": "Invalid"}), 400

    if att.uploaded_by != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Hanya uploader atau admin yang bisa menghapus"}), 403

    try:
        token = UserDriveToken.query.filter_by(user_id=att.uploaded_by).first()
        if not token and current_user.is_admin:
            token = UserDriveToken.query.filter_by(user_id=current_user.id).first()
        if token and att.drive_file_id:
            from helpers.drive import delete_file_from_drive
            delete_file_from_drive(token, att.drive_file_id)
    except Exception:
        pass

    _log_activity(task.id, "attachment_delete", f"Hapus file '{att.filename}'")
    db.session.delete(att)
    db.session.commit()
    return jsonify({"ok": True})
