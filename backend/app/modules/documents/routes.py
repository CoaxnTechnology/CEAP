"""app/routes/files.py"""

import os
import time
import tempfile
from flask import Blueprint, request, jsonify, current_app, make_response
from app.auth_helpers import login_required
from app.services.file_parser import (
    SUPPORTED_EXTS,
    TextExtractionError,
    extract_text,
)
from app.services.vector_store import EmbeddingServiceError
from app.services.rag import (
    current_user_key,
    get_registry,
    get_store,
    register_and_index,
    remove_from_index,
    remove_from_vector_store_only,
)
from app.services.persistence import delete_document, list_categories

files_bp = Blueprint("files", __name__)


@files_bp.route("/api/upload", methods=["POST"])
@login_required
def api_upload():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file provided"}), 400
    file = request.files["file"]
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in SUPPORTED_EXTS:
        return jsonify({"success": False, "error": f"Unsupported type: {ext}"}), 400

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name
    started = time.monotonic()
    current_app.logger.info("upload.start name=%s ext=%s", file.filename, ext)
    try:
        text = extract_text(tmp_path, file.filename)
        extract_ms = int((time.monotonic() - started) * 1000)
        current_app.logger.info(
            "upload.extracted name=%s extract_ms=%s text_len=%s",
            file.filename,
            extract_ms,
            len(text or ""),
        )
        if not text:
            current_app.logger.warning("upload.no_text name=%s", file.filename)
            return jsonify({"success": False, "error": "Could not extract text"}), 400
        category_id = request.form.get("category_id") or None
        entry = register_and_index(
            file.filename, text, os.path.getsize(tmp_path), "local", category_id=category_id
        )
        total_ms = int((time.monotonic() - started) * 1000)
        current_app.logger.info(
            "upload.indexed name=%s file_id=%s chunks=%s total_ms=%s",
            file.filename,
            entry.get("file_id"),
            entry.get("chunks"),
            total_ms,
        )
        return jsonify({"success": True, **entry})
    except TextExtractionError as e:
        current_app.logger.warning(
            "upload.extract_error name=%s error=%s", file.filename, e
        )
        return jsonify({"success": False, "error": str(e)}), 400
    except EmbeddingServiceError as e:
        current_app.logger.warning(
            "upload.embedding_error name=%s error=%s", file.filename, e
        )
        return jsonify({"success": False, "error": str(e)}), 503
    except Exception as e:
        current_app.logger.exception("upload.failed name=%s", file.filename)
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


@files_bp.route("/api/remove", methods=["POST"])
@login_required
def api_remove():
    raw_file_id = ((request.json or {}).get("file_id") or "").strip()
    if not raw_file_id:
        return jsonify({"success": False, "error": "File id is required"}), 400

    file_id = raw_file_id[4:] if raw_file_id.startswith("srv_") else raw_file_id
    if remove_from_index(file_id):
        return jsonify({"success": True})

    user_key = current_user_key()
    indexed_ids = get_store().indexed_file_ids()
    in_vector = file_id in indexed_ids
    removed_vector = remove_from_vector_store_only(file_id) if in_vector else False
    removed_db = delete_document(user_key, file_id)

    if removed_db or removed_vector:
        current_app.logger.info(
            "remove.forced file_id=%s removed_db=%s removed_vector=%s",
            file_id,
            removed_db,
            removed_vector,
        )
        return jsonify(
            {
                "success": True,
                "forced": True,
                "removed_from_db": bool(removed_db),
                "removed_from_vector": bool(removed_vector),
            }
        )

    return jsonify({"success": False, "error": "File not found"}), 404


@files_bp.route("/api/reindex", methods=["POST"])
@login_required
def api_reindex():
    """Re-index a file that has database entry but no ChromaDB chunks."""
    file_id = (request.json or {}).get("file_id")
    registry = get_registry()

    if not file_id or file_id not in registry:
        return jsonify({"success": False, "error": "File not found"}), 404

    entry = registry[file_id]
    source = entry.get("source", "local")
    source_ref = entry.get("source_ref", "")

    # For OneDrive files, we need to re-download
    if source == "onedrive" and source_ref:
        from flask import session
        from app.services.onedrive import graph_download
        from app.services.file_parser import extract_text_from_bytes

        token = session.get("od_token")
        if token:
            try:
                download_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{source_ref}/content"
                raw = graph_download(download_url, token)
                if raw:
                    text = extract_text_from_bytes(raw, entry["name"])
                    if text:
                        remove_from_index(file_id)
                        new_entry = register_and_index(
                            entry["name"],
                            text,
                            entry.get("size", 0),
                            source,
                            source_ref,
                        )
                        return jsonify({"success": True, **new_entry})
            except EmbeddingServiceError as e:
                return jsonify({"success": False, "error": str(e)}), 503
            except Exception as e:
                return jsonify(
                    {"success": False, "error": f"Failed to re-download: {str(e)}"}
                ), 500

    return jsonify(
        {
            "success": False,
            "error": "This file cannot be rebuilt automatically. Please remove it and upload/import it again.",
        }
    ), 400


@files_bp.route("/api/cleanup", methods=["POST"])
@login_required
def api_cleanup():
    """Clean up orphaned ChromaDB entries only.
    Does NOT remove DB entries - those files will show as 'error' and user can remove manually.
    """
    registry = get_registry()
    indexed_file_ids = get_store().indexed_file_ids()
    db_file_ids = set(registry.keys())

    removed_chroma = []

    # Remove orphaned ChromaDB entries (in ChromaDB but not in DB)
    orphaned_chroma = indexed_file_ids - db_file_ids
    for file_id in orphaned_chroma:
        try:
            remove_from_vector_store_only(file_id)
            removed_chroma.append(file_id)
        except:
            pass

    return jsonify(
        {
            "success": True,
            "removed_from_chroma": removed_chroma,
            "count": len(removed_chroma),
            "message": f"Cleaned {len(removed_chroma)} orphaned ChromaDB entries.",
        }
    )


@files_bp.route("/api/files")
@login_required
def api_files():
    registry = get_registry()
    indexed_file_ids = get_store().indexed_file_ids()
    files = {}

    for file_id, entry in registry.items():
        files[file_id] = {
            **entry,
            "indexed": file_id in indexed_file_ids,
        }

    resp = make_response(jsonify({"files": files}))
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    return resp


@files_bp.route("/api/categories", methods=["GET"])
@login_required
def api_categories():
    categories = list_categories()
    return jsonify({"categories": categories})
