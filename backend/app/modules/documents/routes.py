"""app/routes/files.py"""

import hashlib
import os
import time
import tempfile
from flask import Blueprint, request, jsonify, current_app, make_response, send_file
from app.auth_helpers import login_required
from app.db import SessionLocal
from app.models import User
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
from app.services.persistence import delete_document, list_categories, save_document, get_document_by_source_ref
from app.models import Document, RepositoryDocument, Student
from app.services.classifier import classify

files_bp = Blueprint("files", __name__)

STUDENT_UPLOADS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "uploads", "students")
os.makedirs(STUDENT_UPLOADS, exist_ok=True)


def _user_key_for(email: str) -> str:
    return hashlib.sha256(email.encode("utf-8")).hexdigest()[:32]


def _db_key(db):
    admin = db.query(User).filter(User.is_admin == 1).first()
    return _user_key_for(admin.email) if admin else _user_key_for("admin@ceap.school")


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
        department = classify(text, file.filename)
        entry = register_and_index(
            file.filename, text, os.path.getsize(tmp_path), "local",
            category_id=category_id, department=department,
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


@files_bp.route("/api/students/<student_id>/documents", methods=["GET"])
@login_required
def api_student_documents(student_id):
    db = SessionLocal()
    try:
        user_key = _db_key(db)
        docs = (
            db.query(Document)
            .filter(Document.student_id == student_id, Document.user_key == user_key)
            .order_by(Document.uploaded_at.desc())
            .all()
        )
        return jsonify({"documents": [
            {
                "file_id": d.file_id,
                "name": d.name,
                "source_name": d.source_name,
                "size": d.size,
                "chunks": d.chunks,
                "uploaded_at": d.uploaded_at,
                "source": d.source,
                "source_ref": d.source_ref,
                "file_path": d.file_path or "",
                "student_id": d.student_id or "",
                "tags": d.tags or [],
            }
            for d in docs
        ]})
    finally:
        db.close()


@files_bp.route("/api/students/<student_id>/documents/upload", methods=["POST"])
@login_required
def api_student_document_upload(student_id):
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file provided"}), 400
    file = request.files["file"]
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in SUPPORTED_EXTS:
        return jsonify({"success": False, "error": f"Unsupported type: {ext}"}), 400

    db = SessionLocal()
    try:
        user_key = _db_key(db)
        student_dir = os.path.join(STUDENT_UPLOADS, student_id)
        os.makedirs(student_dir, exist_ok=True)

        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name

        started = time.monotonic()
        try:
            text = extract_text(tmp_path, file.filename)
            if not text:
                return jsonify({"success": False, "error": "Could not extract text"}), 400

            category_id = request.form.get("category_id") or None
            department = classify(text, file.filename)

            dest_path = os.path.join(student_dir, file.filename)
            shutil.copy2(tmp_path, dest_path)

            entry = register_and_index(
                file.filename, text, os.path.getsize(tmp_path), "local",
                category_id=category_id, department=department,
                file_path=dest_path, source_ref=student_id,
            )
            entry["student_id"] = student_id
            save_document(user_key, entry["file_id"], entry)

            total_ms = int((time.monotonic() - started) * 1000)
            current_app.logger.info(
                "student.upload name=%s student_id=%s file_id=%s chunks=%s ms=%s",
                file.filename, student_id, entry.get("file_id"), entry.get("chunks"), total_ms,
            )
            return jsonify({"success": True, **entry}), 201
        except TextExtractionError as e:
            return jsonify({"success": False, "error": str(e)}), 400
        except EmbeddingServiceError as e:
            return jsonify({"success": False, "error": str(e)}), 503
        except Exception as e:
            current_app.logger.exception("student.upload.failed name=%s", file.filename)
            return jsonify({"success": False, "error": str(e)}), 500
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    finally:
        db.close()


@files_bp.route("/api/students/<student_id>/documents/<file_id>/download", methods=["GET"])
@login_required
def api_student_document_download(student_id, file_id):
    db = SessionLocal()
    try:
        user_key = _db_key(db)
        doc = (
            db.query(Document)
            .filter(
                Document.file_id == file_id,
                Document.student_id == student_id,
                Document.user_key == user_key,
            )
            .first()
        )
        if not doc:
            return jsonify({"error": "Document not found"}), 404
        file_path = doc.file_path or ""
        if not file_path or not os.path.exists(file_path):
            return jsonify({"error": "File not found on disk"}), 404
        return send_file(file_path, download_name=doc.name, as_attachment=True)
    finally:
        db.close()


@files_bp.route("/api/students/<student_id>/documents/<file_id>", methods=["DELETE"])
@login_required
def api_student_document_delete(student_id, file_id):
    db = SessionLocal()
    try:
        user_key = _db_key(db)
        doc = (
            db.query(Document)
            .filter(
                Document.file_id == file_id,
                Document.student_id == student_id,
                Document.user_key == user_key,
            )
            .first()
        )
        if not doc:
            return jsonify({"error": "Document not found"}), 404
        file_path = doc.file_path or ""
        if file_path and os.path.exists(file_path):
            os.unlink(file_path)
        db.delete(doc)
        db.commit()
        remove_from_index(file_id)
        return jsonify({"success": True})
    finally:
        db.close()


@files_bp.route("/api/students/<student_id>/documents/sync", methods=["POST"])
@login_required
def api_student_documents_sync(student_id):
    db = SessionLocal()
    try:
        user_key = _db_key(db)
        student = db.query(Student).filter(Student.id == student_id, Student.user_key == user_key).first()
        if not student:
            return jsonify({"error": "Student not found"}), 404

        repo_docs = db.query(RepositoryDocument).filter(
            RepositoryDocument.user_key == user_key,
            RepositoryDocument.status == "active",
        ).all()

        synced = []
        skipped = []
        for repo_doc in repo_docs:
            existing = db.query(Document).filter(
                Document.file_id == repo_doc.file_id,
                Document.student_id == student_id,
            ).first()
            if existing:
                skipped.append(repo_doc.name)
                continue

            entry = {
                "name": repo_doc.name,
                "source_name": repo_doc.name,
                "size": repo_doc.size or 0,
                "chunks": 0,
                "uploaded_at": time.time(),
                "source": "repository",
                "source_ref": student_id,
                "category_id": repo_doc.category_id,
                "department": repo_doc.department.name if repo_doc.department else "",
                "tags": repo_doc.tags or [],
                "student_id": student_id,
            }
            save_document(user_key, repo_doc.file_id or repo_doc.id, entry)
            synced.append(repo_doc.name)

        db.commit()
        return jsonify({"success": True, "synced": synced, "skipped": skipped})
    finally:
        db.close()
