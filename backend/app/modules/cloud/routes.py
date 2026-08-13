import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Blueprint, request, jsonify, session, redirect, url_for
from app.auth_helpers import login_required
from app.config import OneDriveConfig, GoogleDriveConfig
from app.services.onedrive import (
    get_msal_app,
    graph_request,
    graph_download,
    list_onedrive_files,
    get_fresh_token,
)
from app.services.google_drive import (
    build_auth_url,
    exchange_code,
    drive_download,
    get_user_info,
    list_drive_files as list_gdrive_files,
)
from app.services.file_parser import extract_text_from_bytes, SUPPORTED_EXTS
from app.services.persistence import get_document_by_source_ref
from app.services.vector_store import EmbeddingServiceError
from app.services.rag import current_user_key, register_and_index_async
from app.services.classifier import classify
import logging

log = logging.getLogger("cloud_import")

onedrive_bp = Blueprint("onedrive", __name__)
gdrive_bp = Blueprint("gdrive", __name__)


def run_cloud_import(token: str, items: list, source: str, **download_kwargs):
    """Shared cloud import: download -> extract -> classify -> index."""
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

        if item_id and get_document_by_source_ref(user_key, item_id, source=source):
            skipped.append({"name": name, "reason": "Already imported"})
            continue

        queued_items.append(item)

    log.info(
        "import source=%s user=%s queued=%d skipped=%d",
        source, user_key, len(queued_items), len(skipped),
    )

    def _prepare_item(item: dict) -> tuple[str, dict]:
        name = item.get("name", "")
        item_id = item.get("item_id") or item.get("id") or ""
        ext = os.path.splitext(name)[1].lower()
        if ext not in SUPPORTED_EXTS and not item.get("export_mime"):
            log.warning("import unsupported name=%s ext=%s", name, ext)
            return "error", {"name": name, "error": f"Unsupported type: {ext}"}

        try:
            if item_id and get_document_by_source_ref(user_key, item_id, source=source):
                return "skipped", {"name": name, "reason": "Already imported"}

            raw = download_kwargs["download"](token=token, item=item)
            if not raw:
                log.warning("import download_failed name=%s id=%s", name, item_id)
                return "error", {"name": name, "error": "Download failed"}

            extract_name = name if os.path.splitext(name)[1] else name + (item.get("ext") or "")
            text = extract_text_from_bytes(raw, extract_name)
            if not text:
                log.warning("import no_text name=%s id=%s", name, item_id)
                return "error", {"name": name, "error": "Empty file: no extractable text"}

            return "prepared", {
                "name": name,
                "text": text,
                "size": item.get("size", 0),
                "source_ref": item_id,
                "path": item.get("path", ""),
            }
        except Exception as e:
            log.warning("import prepare_error name=%s id=%s err=%s", name, item_id, e)
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
            dept = classify(payload["text"], payload["name"])
            entry = register_and_index_async(
                user_key,
                payload["name"],
                payload["text"],
                payload["size"],
                source=source,
                source_ref=payload["source_ref"],
                department=dept,
                file_path=payload.get("path", ""),
            )
            imported.append(entry)
        except EmbeddingServiceError as e:
            errors.append({"name": payload["name"], "error": str(e)})
        except Exception as e:
            errors.append({"name": payload["name"], "error": str(e)})

    log.info(
        "import done source=%s imported=%d errors=%d skipped=%d",
        source, len(imported), len(errors), len(skipped),
    )
    for e in errors:
        log.warning("import error item=%s reason=%s", e.get("name"), e.get("error"))

    return jsonify(
        {"success": True, "imported": imported, "errors": errors, "skipped": skipped}
    )


@onedrive_bp.route("/onedrive/connect")
@login_required
def onedrive_connect():
    redirect_url = request.args.get("redirect", "")
    if redirect_url:
        session["od_redirect"] = redirect_url
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
        prompt="select_account",
    )
    return redirect(auth_url)


@onedrive_bp.route("/auth/callback")
@login_required
def onedrive_callback():
    code = request.args.get("code")
    error = request.args.get("error")
    if error or not code:
        return redirect(url_for("auth.chat") + f"?od_error={error or 'no_code'}")

    from msal import SerializableTokenCache
    cache = SerializableTokenCache()
    cached = session.get("od_cache")
    if cached:
        try:
            cache.deserialize(cached)
        except Exception:
            pass
    app = get_msal_app(cache)
    result = app.acquire_token_by_authorization_code(
        code, scopes=OneDriveConfig.SCOPES, redirect_uri=OneDriveConfig.REDIRECT_URI
    )
    if "access_token" not in result:
        return redirect(
            url_for("auth.chat")
            + f"?od_error={result.get('error_description', 'auth_failed')}"
        )

    token = result["access_token"]
    session["od_cache"] = cache.serialize()
    me = graph_request("/me", token) or {}
    od_user = me.get("displayName", "OneDrive User")
    od_email = me.get("mail") or me.get("userPrincipalName", "")
    session["od_token"] = token
    session["od_user"] = od_user
    session["od_email"] = od_email
    target = session.pop("od_redirect", None) or url_for("auth.catch_all", path="admin")
    return redirect(
        f"{target}?od_connected=1&od_name={od_user}&od_email={od_email}"
    )


@onedrive_bp.route("/api/onedrive/disconnect", methods=["POST"])
@onedrive_bp.route("/onedrive/disconnect", methods=["GET", "POST"])
@login_required
def onedrive_disconnect():
    session.pop("od_token", None)
    session.pop("od_cache", None)
    session.pop("od_user", None)
    session.pop("od_email", None)
    if request.method == "GET":
        return redirect(url_for("auth.catch_all", path="admin"))
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
    token, new_cache = get_fresh_token(session.get("od_cache"), session.get("od_token"))
    if new_cache:
        session["od_cache"] = new_cache
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
    token, new_cache = get_fresh_token(session.get("od_cache"), session.get("od_token"))
    if new_cache:
        session["od_cache"] = new_cache
    if not token:
        return jsonify({"error": "OneDrive not connected"}), 401

    items = (request.json or {}).get("files", [])

    def _download(**kw):
        item = kw["item"]
        download_url = (item.get("download_url") or "").strip()
        item_id = item.get("item_id") or item.get("id") or ""
        if not download_url:
            if not item_id:
                return None
            download_url = (
                f"https://graph.microsoft.com/v1.0/me/drive/items/{item_id}/content"
            )
        return graph_download(download_url, kw["token"])

    return run_cloud_import(token, items, source="onedrive", download=_download)


@gdrive_bp.route("/gdrive/connect")
@login_required
def gdrive_connect():
    redirect_url = request.args.get("redirect", "")
    if redirect_url:
        session["gd_redirect"] = redirect_url
    if not GoogleDriveConfig.is_enabled():
        return jsonify(
            {
                "error": "Google Drive not configured. Set GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET in .env"
            }
        ), 503
    auth_url = build_auth_url(state=session.get("user_key", ""))
    return redirect(auth_url)


@gdrive_bp.route("/gdrive/callback")
@login_required
def gdrive_callback():
    code = request.args.get("code")
    error = request.args.get("error")
    if error or not code:
        return redirect(url_for("auth.chat") + f"?gd_error={error or 'no_code'}")

    result = exchange_code(code)
    token = result.get("access_token")
    if not token:
        return redirect(
            url_for("auth.chat")
            + f"?gd_error={result.get('error_description', 'auth_failed')}"
        )

    me = get_user_info(token)
    gd_user = me.get("name", "Google Drive User")
    gd_email = me.get("email", "")
    session["gd_token"] = token
    session["gd_user"] = gd_user
    session["gd_email"] = gd_email
    session["gd_expires"] = int(result.get("expires_in", 3600)) + 60
    target = session.pop("gd_redirect", None) or url_for("auth.catch_all", path="admin")
    return redirect(
        f"{target}?gd_connected=1&gd_name={gd_user}&gd_email={gd_email}"
    )


@gdrive_bp.route("/api/gdrive/disconnect", methods=["POST"])
@gdrive_bp.route("/gdrive/disconnect", methods=["GET", "POST"])
@login_required
def gdrive_disconnect():
    session.pop("gd_token", None)
    session.pop("gd_user", None)
    session.pop("gd_email", None)
    session.pop("gd_expires", None)
    if request.method == "GET":
        return redirect(url_for("auth.catch_all", path="admin"))
    return jsonify({"success": True})


@gdrive_bp.route("/api/gdrive/status")
@login_required
def gdrive_status():
    return jsonify(
        {
            "enabled": GoogleDriveConfig.is_enabled(),
            "connected": bool(session.get("gd_token")),
            "user": session.get("gd_user", ""),
            "email": session.get("gd_email", ""),
        }
    )


@gdrive_bp.route("/api/gdrive/files")
@login_required
def gdrive_files():
    token = session.get("gd_token")
    if not token:
        return jsonify({"error": "Google Drive not connected"}), 401
    folder_id = (request.args.get("folder") or "root").strip() or "root"
    try:
        files = list_gdrive_files(token, folder_id)
        return jsonify({"success": True, "files": files})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@gdrive_bp.route("/api/gdrive/import", methods=["POST"])
@login_required
def gdrive_import():
    token = session.get("gd_token")
    if not token:
        return jsonify({"error": "Google Drive not connected"}), 401

    items = (request.json or {}).get("files", [])

    def _download(**kw):
        item = kw["item"]
        return drive_download(
            item.get("id") or item.get("item_id") or "", kw["token"],
            item.get("export_mime"),
        )

    return run_cloud_import(token, items, source="gdrive", download=_download)
