import os
import requests as http_requests
from urllib.parse import urlencode
from app.config import GoogleDriveConfig

DRIVE_BASE = "https://www.googleapis.com/drive/v3"
TOKEN_URL = "https://oauth2.googleapis.com/token"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
FOLDER_MIME = "application/vnd.google-apps.folder"


def _session_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def build_auth_url(state: str) -> str:
    params = {
        "client_id": GoogleDriveConfig.CLIENT_ID,
        "redirect_uri": GoogleDriveConfig.REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(GoogleDriveConfig.SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def exchange_code(code: str) -> dict:
    resp = http_requests.post(
        TOKEN_URL,
        data={
            "code": code,
            "client_id": GoogleDriveConfig.CLIENT_ID,
            "client_secret": GoogleDriveConfig.CLIENT_SECRET,
            "redirect_uri": GoogleDriveConfig.REDIRECT_URI,
            "grant_type": "authorization_code",
        },
        timeout=30,
    )
    return resp.json()


def drive_request(endpoint: str, token: str, **kwargs):
    resp = http_requests.get(
        f"{DRIVE_BASE}{endpoint}",
        headers=_session_headers(token),
        params=kwargs.get("params"),
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Drive API {resp.status_code}: {resp.text[:200]}")
    return resp.json()


def drive_download(file_id: str, token: str, mime_type: str | None = None):
    if mime_type:
        url = f"{DRIVE_BASE}/files/{file_id}/export?mimeType={mime_type}"
    else:
        url = f"{DRIVE_BASE}/files/{file_id}?alt=media"
    resp = http_requests.get(
        url, headers=_session_headers(token), timeout=60
    )
    return resp.content if resp.status_code == 200 else None


def get_user_info(token: str) -> dict:
    resp = http_requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers=_session_headers(token),
        timeout=30,
    )
    return resp.json() if resp.status_code == 200 else {}


def _export_mime(mime_type: str) -> str | None:
    return {
        "application/vnd.google-apps.document": "text/plain",
        "application/vnd.google-apps.spreadsheet": "text/csv",
        "application/vnd.google-apps.slides": "text/plain",
    }.get(mime_type)


def list_drive_files(token: str, folder_id: str | None = None) -> list:
    """List immediate children of a folder, not the entire drive tree."""
    SUPPORTED = {".pdf", ".docx", ".xlsx", ".xls", ".csv", ".txt"}
    page_token = None
    results = []

    while True:
        query = f"'{folder_id}' in parents and trashed = false" if folder_id else "root in parents and trashed = false"
        params = {
            "q": query,
            "pageSize": 100,
            "fields": "nextPageToken, files(id, name, mimeType, size)",
            "pageToken": page_token,
        }
        data = drive_request("/files", token, params=params)
        if not data:
            return results

        for item in data.get("files", []):
            name = item.get("name", "")
            mime_type = item.get("mimeType", "")
            if mime_type == FOLDER_MIME:
                results.append(
                    {
                        "id": item["id"],
                        "name": name,
                        "size": 0,
                        "parent_id": folder_id or "root",
                        "path": name,
                        "isFolder": True,
                    }
                )
                continue

            export_mime = _export_mime(mime_type)
            if not export_mime:
                ext = os.path.splitext(name)[1].lower()
                if ext not in SUPPORTED:
                    continue
                export_mime = None

            results.append(
                {
                    "id": item["id"],
                    "name": name,
                    "size": int(item.get("size", 0) or 0),
                    "parent_id": folder_id or "root",
                    "path": name,
                    "ext": export_mime and ".txt" or os.path.splitext(name)[1].lower(),
                    "export_mime": export_mime,
                    "isFolder": False,
                }
            )

        page_token = data.get("nextPageToken")
        if not page_token:
            return results