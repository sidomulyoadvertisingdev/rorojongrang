import time
import requests
from datetime import datetime, timedelta
from flask import current_app

DRIVE_API_BASE = "https://www.googleapis.com/drive/v3"
DRIVE_UPLOAD_BASE = "https://www.googleapis.com/upload/drive/v3"
APP_FOLDER_NAME = "RoroJonggrang"


def _get_headers(token_record):
    return {"Authorization": f"Bearer {token_record.access_token}"}


def refresh_access_token(token_record):
    resp = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": current_app.config.get("GOOGLE_CLIENT_ID", ""),
        "client_secret": current_app.config.get("GOOGLE_CLIENT_SECRET", ""),
        "refresh_token": token_record.refresh_token,
        "grant_type": "refresh_token",
    })
    if resp.status_code != 200:
        raise Exception("Failed to refresh Google Drive token")
    data = resp.json()
    token_record.access_token = data["access_token"]
    token_record.token_expiry = datetime.utcnow() + timedelta(seconds=data.get("expires_in", 3600))
    from models import db
    db.session.commit()
    return token_record


def ensure_valid_token(token_record):
    if token_record.is_expired():
        token_record = refresh_access_token(token_record)
    return token_record


def get_or_create_folder(token_record, folder_name, parent_id=None):
    token_record = ensure_valid_token(token_record)
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    else:
        query += " and 'root' in parents"

    resp = requests.get(f"{DRIVE_API_BASE}/files", headers=_get_headers(token_record), params={
        "q": query, "fields": "files(id, name)", "pageSize": "1"
    })
    if resp.status_code == 200:
        files = resp.json().get("files", [])
        if files:
            return files[0]["id"]

    metadata = {"name": folder_name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        metadata["parents"] = [parent_id]

    resp = requests.post(f"{DRIVE_API_BASE}/files", headers={
        **_get_headers(token_record), "Content-Type": "application/json"
    }, json=metadata)
    if resp.status_code != 200:
        raise Exception(f"Failed to create folder: {resp.text}")
    return resp.json()["id"]


def get_app_folder(token_record):
    token_record = ensure_valid_token(token_record)
    if token_record.folder_id:
        return token_record.folder_id, token_record

    folder_id = get_or_create_folder(token_record, APP_FOLDER_NAME)
    token_record.folder_id = folder_id
    from models import db
    db.session.commit()
    return folder_id, token_record


def upload_file_to_drive(token_record, file_data, filename, mime_type, board_name=None):
    token_record = ensure_valid_token(token_record)
    root_folder_id, token_record = get_app_folder(token_record)

    if board_name:
        safe_name = board_name[:50].replace("'", "").replace('"', '')
        parent_id = get_or_create_folder(token_record, safe_name, root_folder_id)
    else:
        parent_id = root_folder_id

    metadata = {"name": filename, "parents": [parent_id]}
    resp = requests.post(
        f"{DRIVE_UPLOAD_BASE}/files?uploadType=multipart",
        headers=_get_headers(token_record),
        files={
            "metadata": ("", str(metadata).replace("'", '"'), "application/json"),
            "file": (filename, file_data, mime_type or "application/octet-stream"),
        }
    )
    if resp.status_code not in (200, 201):
        raise Exception(f"Failed to upload file: {resp.text}")
    return resp.json()


def share_file_anyone(token_record, drive_file_id):
    token_record = ensure_valid_token(token_record)
    resp = requests.post(
        f"{DRIVE_API_BASE}/files/{drive_file_id}/permissions",
        headers={**_get_headers(token_record), "Content-Type": "application/json"},
        json={"role": "reader", "type": "anyone"},
    )
    return resp.status_code in (200, 201)


def delete_file_from_drive(token_record, drive_file_id):
    token_record = ensure_valid_token(token_record)
    resp = requests.delete(f"{DRIVE_API_BASE}/files/{drive_file_id}", headers=_get_headers(token_record))
    return resp.status_code == 204


def get_file_info(token_record, drive_file_id):
    token_record = ensure_valid_token(token_record)
    resp = requests.get(f"{DRIVE_API_BASE}/files/{drive_file_id}", headers=_get_headers(token_record), params={
        "fields": "id,name,mimeType,size,webContentLink,webViewLink"
    })
    if resp.status_code == 200:
        return resp.json()
    return None


def get_download_url(token_record, drive_file_id):
    token_record = ensure_valid_token(token_record)
    resp = requests.get(f"{DRIVE_API_BASE}/files/{drive_file_id}", headers=_get_headers(token_record), params={
        "fields": "webContentLink"
    })
    if resp.status_code == 200:
        data = resp.json()
        url = data.get("webContentLink", "")
        if url:
            return url + "&export=download" if "?" in url else url + "?export=download"
    return f"https://drive.google.com/uc?id={drive_file_id}&export=download"
