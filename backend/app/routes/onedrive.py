import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Blueprint, request, jsonify, session, redirect, url_for
from app.auth_helpers import login_required
from app.config import OneDriveConfig
from app.services.onedrive import (
    get_msal_app,
    graph_request,
    graph_download,
    list_onedrive_files,
)
from app.services.file_parser import extract_text_from_bytes, SUPPORTED_EXTS
from app.services.persistence import get_document_by_source_ref
from app.services.vector_store import EmbeddingServiceError
from app.services.rag import current_user_key, register_and_index_for_user

onedrive_bp = Blueprint("onedrive", __name__)


@onedrive_bp.route("/onedrive/connect")
@login_required
def onedrive_connect():
    if not OneDriveConfig.is_enabled():
        return jsonify(
            {
                "error": "OneDrive not configured. Set AZURE_CLIENT_ID / AZURE_CLIENT_SECRET in .env"
            }
        ), 503
    auth_url = get_msal_app().get_authorization_request_url(
        OneDriveConfig.SCOPES,
        redirect_uri=OneDriveConfig.REDIRECT_URI,
        state=session.get("user_key", ""),
    )
    return redirect(auth_url)


@onedrive_bp.route("/auth/callback")
@login_required
def onedrive_callback():
    code = request.args.get("code")
    error = request.args.get("error")
    if error or not code:
        return redirect(url_for("auth.chat") + f"?od_error={error or 'no_code'}")

    result = get_msal_app().acquire_token_by_authorization_code(
        code, scopes=OneDriveConfig.SCOPES, redirect_uri=OneDriveConfig.REDIRECT_URI
    )
    if "access_token" not in result:
        return redirect(
            url_for("auth.chat")
            + f"?od_error={result.get('error_description', 'auth_failed')}"
        )

    token = result["access_token"]
    me = graph_request("/me", token) or {}
    od_user = me.get("displayName", "OneDrive User")
    od_email = me.get("mail") or me.get("userPrincipalName", "")
    session["od_token"] = token
    session["od_user"] = od_user
    session["od_email"] = od_email
    return redirect(
        url_for("auth.chat") + f"?od_connected=1&od_name={od_user}&od_email={od_email}"
    )


@onedrive_bp.route("/onedrive/disconnect", methods=["POST"])
@login_required
def onedrive_disconnect():
    session.pop("od_token", None)
    session.pop("od_user", None)
    session.pop("od_email", None)
    return jsonify({"success": True})


@onedrive_bp.route("/api/onedrive/status")
@login_required
def onedrive_status():
    return jsonify(
        {
            "enabled": OneDriveConfig.is_enabled(),
            "connected": bool(session.get("od_token")),
            "user": session.get("od_user", ""),
            "email": session.get("od_email", ""),
        }
    )


@onedrive_bp.route("/api/onedrive/files")
@login_required
def onedrive_files():
    token = session.get("od_token")
    if not token:
        return jsonify({"error": "OneDrive not connected"}), 401
    folder_id = (request.args.get("folder") or "root").strip() or "root"
    try:
        files = list_onedrive_files(token, folder_id)
        return jsonify({"success": True, "files": files})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@onedrive_bp.route("/api/onedrive/import", methods=["POST"])
@login_required
def onedrive_import():
    token = session.get("od_token")
    if not token:
        return jsonify({"error": "OneDrive not connected"}), 401

    items = (request.json or {}).get("files", [])
    user_key = current_user_key()
    imported, errors, skipped = [], [], []
    queued_items = []
    seen_item_ids = set()

    for item in items:
        name = item.get("name", "")
        item_id = item.get("item_id") or item.get("id") or ""
        dedupe_key = item_id or name

        if dedupe_key and dedupe_key in seen_item_ids:
            skipped.append({"name": name, "reason": "Already queued in this import"})
            continue
        if dedupe_key:
            seen_item_ids.add(dedupe_key)

        if item_id and get_document_by_source_ref(user_key, item_id, source="onedrive"):
            skipped.append({"name": name, "reason": "Already imported"})
            continue

        queued_items.append(item)

    def _prepare_item(item: dict) -> tuple[str, dict]:
        name = item.get("name", "")
        item_id = item.get("item_id") or item.get("id") or ""
        download_url = (item.get("download_url") or "").strip()
        ext = os.path.splitext(name)[1].lower()
        if ext not in SUPPORTED_EXTS:
            return "error", {"name": name, "error": f"Unsupported type: {ext}"}

        try:
            if item_id and get_document_by_source_ref(user_key, item_id, source="onedrive"):
                return "skipped", {"name": name, "reason": "Already imported"}

            if not download_url:
                if not item_id:
                    return "error", {
                        "name": name,
                        "error": "Missing OneDrive download URL and item id",
                    }
                download_url = (
                    f"https://graph.microsoft.com/v1.0/me/drive/items/{item_id}/content"
                )

            raw = graph_download(download_url, token)
            if not raw:
                return "error", {"name": name, "error": "Download failed"}

            text = extract_text_from_bytes(raw, name)
            if not text:
                return "error", {"name": name, "error": "No text extracted"}

            return "prepared", {
                "name": name,
                "text": text,
                "size": item.get("size", 0),
                "source_ref": item_id,
            }
        except Exception as e:
            return "error", {"name": name, "error": str(e)}

    prepared_items = []
    max_workers = min(4, len(queued_items)) if queued_items else 0
    if max_workers:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(_prepare_item, item) for item in queued_items]
            for future in as_completed(futures):
                status, payload = future.result()
                if status == "prepared":
                    prepared_items.append(payload)
                elif status == "skipped":
                    skipped.append(payload)
                else:
                    errors.append(payload)

    for payload in prepared_items:
        try:
            entry = register_and_index_for_user(
                user_key,
                payload["name"],
                payload["text"],
                payload["size"],
                source="onedrive",
                source_ref=payload["source_ref"],
            )
            imported.append(entry)
        except EmbeddingServiceError as e:
            errors.append({"name": payload["name"], "error": str(e)})
        except Exception as e:
            errors.append({"name": payload["name"], "error": str(e)})

    return jsonify(
        {"success": True, "imported": imported, "errors": errors, "skipped": skipped}
    )
