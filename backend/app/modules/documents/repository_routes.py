"""app/routes/repository.py — Document Repository 2.0 API"""

import os
import time
import shutil
import uuid
from flask import Blueprint, request, jsonify, send_file, session
from app.auth_helpers import login_required
from app.db import SessionLocal
from app.models import (
    Folder, RepositoryDocument, DocumentVersion, DocumentComment,
    DocumentCategory, Department,
)
from sqlalchemy import func
from app.services.storage import store_version, get_version_path, delete_doc_storage, duplicate_exists
from app.services.file_parser import extract_text
from app.services.rag import register_and_index_for_user
from app.services.vector_store import ChromaStore
from app.services.persistence import delete_document as delete_rag_document, remove_file_chunks

repo_bp = Blueprint("repository", __name__, url_prefix="/api/repository")


def _user_key():
    return session.get("user", "")


def _doc_to_dict(doc):
    return {
        "id": doc.id,
        "name": doc.name,
        "folder_id": doc.folder_id,
        "file_hash": doc.file_hash,
        "size": doc.size,
        "mime_type": doc.mime_type,
        "current_version": doc.current_version,
        "file_id": doc.file_id,
        "indexed": bool(doc.file_id),
        "category_id": doc.category_id,
        "department_id": doc.department_id,
        "tags": doc.tags or [],
        "owner_email": doc.owner_email,
        "description": doc.description,
        "is_favorite": bool(doc.is_favorite),
        "is_archived": bool(doc.is_archived),
        "status": doc.status,
        "trashed_at": doc.trashed_at,
        "expiry_date": doc.expiry_date,
        "created_at": doc.created_at,
        "updated_at": doc.updated_at,
    }


def _folder_to_dict(f):
    return {
        "id": f.id,
        "name": f.name,
        "parent_id": f.parent_id,
        "created_at": f.created_at,
    }


# ─── Folders ─────────────────────────────────────────────────────────────


@repo_bp.route("/folders", methods=["GET"])
@login_required
def list_folders():
    user_key = _user_key()
    db = SessionLocal()
    try:
        folders = db.query(Folder).filter(
            Folder.created_by == user_key
        ).order_by(Folder.name).all()
        return jsonify({"folders": [_folder_to_dict(f) for f in folders]})
    finally:
        db.close()


@repo_bp.route("/folders", methods=["POST"])
@login_required
def create_folder():
    data = request.json or {}
    name = (data.get("name") or "").strip()
    parent_id = data.get("parent_id") or None

    if not name:
        return jsonify({"error": "Folder name is required"}), 400

    user_key = _user_key()
    db = SessionLocal()
    try:
        folder = Folder(
            name=name,
            parent_id=parent_id,
            created_by=user_key,
        )
        db.add(folder)
        db.commit()
        db.refresh(folder)
        return jsonify({"success": True, "folder": _folder_to_dict(folder)}), 201
    finally:
        db.close()


@repo_bp.route("/folders/<folder_id>", methods=["PATCH"])
@login_required
def rename_folder(folder_id):
    data = request.json or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Folder name is required"}), 400

    db = SessionLocal()
    try:
        folder = db.query(Folder).filter(Folder.id == folder_id).first()
        if not folder:
            return jsonify({"error": "Folder not found"}), 404
        folder.name = name
        folder.updated_at = time.time()
        db.commit()
        return jsonify({"success": True, "folder": _folder_to_dict(folder)})
    finally:
        db.close()


@repo_bp.route("/folders/<folder_id>", methods=["DELETE"])
@login_required
def delete_folder(folder_id):
    db = SessionLocal()
    try:
        folder = db.query(Folder).filter(Folder.id == folder_id).first()
        if not folder:
            return jsonify({"error": "Folder not found"}), 404

        # Move child docs to parent folder (or root)
        child_docs = db.query(RepositoryDocument).filter(
            RepositoryDocument.folder_id == folder_id
        ).all()
        for doc in child_docs:
            doc.folder_id = folder.parent_id

        # Reparent child folders
        child_folders = db.query(Folder).filter(Folder.parent_id == folder_id).all()
        for cf in child_folders:
            cf.parent_id = folder.parent_id

        db.delete(folder)
        db.commit()
        return jsonify({"success": True})
    finally:
        db.close()


@repo_bp.route("/folders/move", methods=["POST"])
@login_required
def move_folder():
    data = request.json or {}
    folder_id = data.get("folder_id")
    new_parent_id = data.get("parent_id") or None

    db = SessionLocal()
    try:
        folder = db.query(Folder).filter(Folder.id == folder_id).first()
        if not folder:
            return jsonify({"error": "Folder not found"}), 404
        folder.parent_id = new_parent_id
        folder.updated_at = time.time()
        db.commit()
        return jsonify({"success": True})
    finally:
        db.close()


# ─── Documents ────────────────────────────────────────────────────────────


@repo_bp.route("/documents", methods=["GET"])
@login_required
def list_documents():
    user_key = _user_key()
    folder_id = request.args.get("folder_id")
    status = request.args.get("status", "active")
    favorite = request.args.get("favorite")
    archived = request.args.get("archived")
    indexed = request.args.get("indexed")
    recent = request.args.get("recent")
    search = request.args.get("search", "").strip()

    db = SessionLocal()
    try:
        query = db.query(RepositoryDocument).filter(
            RepositoryDocument.user_key == user_key,
        )

        if status == "trashed":
            query = query.filter(RepositoryDocument.status == "trashed")
        else:
            query = query.filter(RepositoryDocument.status == "active")

        if folder_id:
            query = query.filter(RepositoryDocument.folder_id == folder_id)
        if favorite == "1":
            query = query.filter(RepositoryDocument.is_favorite == 1)
        if archived == "1":
            query = query.filter(RepositoryDocument.is_archived == 1)
        if indexed == "1":
            query = query.filter(RepositoryDocument.file_id.isnot(None))
        elif indexed == "0":
            query = query.filter(RepositoryDocument.file_id.is_(None))

        if recent == "1":
            cutoff = time.time() - 30 * 86400
            query = query.filter(RepositoryDocument.updated_at >= cutoff)

        if search:
            query = query.filter(RepositoryDocument.name.ilike(f"%{search}%"))

        docs = query.order_by(
            RepositoryDocument.is_favorite.desc(),
            RepositoryDocument.updated_at.desc(),
        ).all()

        return jsonify({"documents": [_doc_to_dict(d) for d in docs]})
    finally:
        db.close()


@repo_bp.route("/documents/upload", methods=["POST"])
@login_required
def upload_document():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400

    folder_id = request.form.get("folder_id") or None
    category_id = request.form.get("category_id") or None
    department_id = request.form.get("department_id") or None
    tags_raw = request.form.get("tags", "[]")
    description = request.form.get("description", "")

    import json
    try:
        tags = json.loads(tags_raw) if isinstance(tags_raw, str) else tags_raw
    except (json.JSONDecodeError, TypeError):
        tags = []

    user_key = _user_key()
    filename = file.filename

    # Check duplicate via SHA256
    import tempfile
    tmp = tempfile.NamedTemporaryFile(delete=False)
    try:
        file.save(tmp.name)
        tmp.close()

        from app.services.storage import compute_hash
        file_hash = compute_hash(tmp.name)
        file_size = os.path.getsize(tmp.name)
        existing_id = duplicate_exists(file_hash)
        if existing_id:
            os.unlink(tmp.name)
            return jsonify({
                "success": False,
                "error": "Duplicate document detected",
                "existing_id": existing_id,
                "file_hash": file_hash,
            }), 409

        import mimetypes
        mime_type, _ = mimetypes.guess_type(filename)

        db = SessionLocal()
        try:
            doc = RepositoryDocument(
                user_key=user_key,
                name=filename,
                folder_id=folder_id,
                file_hash=file_hash,
                size=file_size,
                mime_type=mime_type or "application/octet-stream",
                current_version=1,
                category_id=category_id,
                department_id=department_id,
                tags=tags,
                description=description,
                owner_email=user_key,
            )
            db.add(doc)
            db.flush()

            # Store file and create version record
            result = store_version(doc.id, 1, open(tmp.name, "rb"), filename)

            version = DocumentVersion(
                document_id=doc.id,
                version_number=1,
                file_name=filename,
                file_path=result["file_path"],
                file_size=result["file_size"],
                file_hash=result["file_hash"],
                mime_type=mime_type or "application/octet-stream",
                uploaded_by=user_key,
                change_notes="Initial upload",
            )
            db.add(version)

            doc.size = result["file_size"]
            db.commit()
            db.refresh(doc)

            # Index for RAG chat (non-blocking on failure)
            try:
                text = extract_text(result["file_path"], filename)
                if text:
                    rag_entry = register_and_index_for_user(
                        user_key=user_key,
                        name=filename,
                        text=text,
                        size=doc.size,
                        source="repository",
                        source_ref=doc.id,
                        category_id=category_id,
                    )
                    doc.file_id = rag_entry["file_id"]
                    db.commit()
            except Exception:
                pass

            return jsonify({"success": True, "document": _doc_to_dict(doc)}), 201
        finally:
            db.close()
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


@repo_bp.route("/documents/<doc_id>", methods=["GET"])
@login_required
def get_document(doc_id):
    db = SessionLocal()
    try:
        doc = db.query(RepositoryDocument).filter(RepositoryDocument.id == doc_id).first()
        if not doc:
            return jsonify({"error": "Document not found"}), 404
        return jsonify({"document": _doc_to_dict(doc)})
    finally:
        db.close()


@repo_bp.route("/documents/<doc_id>", methods=["PATCH"])
@login_required
def update_document(doc_id):
    data = request.json or {}
    db = SessionLocal()
    try:
        doc = db.query(RepositoryDocument).filter(RepositoryDocument.id == doc_id).first()
        if not doc:
            return jsonify({"error": "Document not found"}), 404

        updatable = ["name", "folder_id", "category_id", "department_id", "tags",
                      "description", "owner_email", "expiry_date", "is_favorite", "is_archived"]
        for field in updatable:
            if field in data:
                setattr(doc, field, data[field])

        doc.updated_at = time.time()
        db.commit()
        db.refresh(doc)
        return jsonify({"success": True, "document": _doc_to_dict(doc)})
    finally:
        db.close()


@repo_bp.route("/documents/<doc_id>/rename", methods=["PATCH"])
@login_required
def rename_document(doc_id):
    data = request.json or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400

    db = SessionLocal()
    try:
        doc = db.query(RepositoryDocument).filter(RepositoryDocument.id == doc_id).first()
        if not doc:
            return jsonify({"error": "Document not found"}), 404
        doc.name = name
        doc.updated_at = time.time()
        db.commit()
        return jsonify({"success": True, "document": _doc_to_dict(doc)})
    finally:
        db.close()


@repo_bp.route("/documents/<doc_id>/move", methods=["PATCH"])
@login_required
def move_document(doc_id):
    data = request.json or {}
    folder_id = data.get("folder_id") or None

    db = SessionLocal()
    try:
        doc = db.query(RepositoryDocument).filter(RepositoryDocument.id == doc_id).first()
        if not doc:
            return jsonify({"error": "Document not found"}), 404
        doc.folder_id = folder_id
        doc.updated_at = time.time()
        db.commit()
        return jsonify({"success": True})
    finally:
        db.close()


@repo_bp.route("/documents/<doc_id>/copy", methods=["POST"])
@login_required
def copy_document(doc_id):
    db = SessionLocal()
    try:
        src = db.query(RepositoryDocument).filter(RepositoryDocument.id == doc_id).first()
        if not src:
            return jsonify({"error": "Document not found"}), 404

        new_doc = RepositoryDocument(
            user_key=src.user_key,
            name=f"Copy of {src.name}",
            folder_id=src.folder_id,
            file_hash=src.file_hash,
            size=src.size,
            mime_type=src.mime_type,
            current_version=src.current_version,
            category_id=src.category_id,
            department_id=src.department_id,
            tags=src.tags,
            description=src.description,
            owner_email=src.owner_email,
        )
        db.add(new_doc)
        db.flush()

        # Copy all versions
        versions = db.query(DocumentVersion).filter(
            DocumentVersion.document_id == doc_id
        ).order_by(DocumentVersion.version_number).all()

        import shutil
        for v in versions:
            from app.services.storage import get_doc_dir
            import os
            src_path = v.file_path
            new_ver_dir = os.path.join(get_doc_dir(new_doc.id), f"v{v.version_number}")
            os.makedirs(new_ver_dir, exist_ok=True)

            new_file_path = os.path.join(new_ver_dir, v.file_name)
            if os.path.exists(src_path):
                shutil.copy2(src_path, new_file_path)

            new_ver = DocumentVersion(
                document_id=new_doc.id,
                version_number=v.version_number,
                file_name=v.file_name,
                file_path=new_file_path,
                file_size=v.file_size,
                file_hash=v.file_hash,
                mime_type=v.mime_type,
                uploaded_by=v.uploaded_by,
                change_notes=v.change_notes,
            )
            db.add(new_ver)

        db.commit()
        db.refresh(new_doc)
        return jsonify({"success": True, "document": _doc_to_dict(new_doc)}), 201
    finally:
        db.close()


@repo_bp.route("/documents/bulk", methods=["DELETE"])
@login_required
def bulk_delete_documents():
    data = request.json or {}
    doc_ids = data.get("doc_ids", [])
    permanent = data.get("permanent", False)

    if not doc_ids:
        return jsonify({"error": "No document IDs provided"}), 400

    db = SessionLocal()
    try:
        now = time.time()
        for doc_id in doc_ids:
            doc = db.query(RepositoryDocument).filter(RepositoryDocument.id == doc_id).first()
            if doc:
                if permanent:
                    if doc.file_id:
                        try:
                            ChromaStore(doc.user_key).remove_file(doc.file_id)
                            remove_file_chunks(doc.user_key, doc.file_id)
                            delete_rag_document(doc.user_key, doc.file_id)
                        except Exception:
                            pass
                    delete_doc_storage(doc_id)
                    db.delete(doc)
                else:
                    doc.status = "trashed"
                    doc.trashed_at = now
        db.commit()
        return jsonify({"success": True, "count": len(doc_ids)})
    finally:
        db.close()


@repo_bp.route("/documents/bulk/move", methods=["POST"])
@login_required
def bulk_move_documents():
    data = request.json or {}
    doc_ids = data.get("doc_ids", [])
    folder_id = data.get("folder_id") or None

    if not doc_ids:
        return jsonify({"error": "No document IDs provided"}), 400

    db = SessionLocal()
    try:
        now = time.time()
        for doc_id in doc_ids:
            doc = db.query(RepositoryDocument).filter(RepositoryDocument.id == doc_id).first()
            if doc:
                doc.folder_id = folder_id
                doc.updated_at = now
        db.commit()
        return jsonify({"success": True, "count": len(doc_ids)})
    finally:
        db.close()


# ─── Trash ────────────────────────────────────────────────────────────────


@repo_bp.route("/trash", methods=["GET"])
@login_required
def list_trash():
    user_key = _user_key()
    db = SessionLocal()
    try:
        docs = db.query(RepositoryDocument).filter(
            RepositoryDocument.user_key == user_key,
            RepositoryDocument.status == "trashed",
        ).order_by(RepositoryDocument.trashed_at.desc()).all()
        return jsonify({"documents": [_doc_to_dict(d) for d in docs]})
    finally:
        db.close()


@repo_bp.route("/trash/<doc_id>/restore", methods=["POST"])
@login_required
def restore_document(doc_id):
    db = SessionLocal()
    try:
        doc = db.query(RepositoryDocument).filter(
            RepositoryDocument.id == doc_id,
            RepositoryDocument.status == "trashed",
        ).first()
        if not doc:
            return jsonify({"error": "Document not found in trash"}), 404
        doc.status = "active"
        doc.trashed_at = None
        doc.updated_at = time.time()
        db.commit()
        return jsonify({"success": True})
    finally:
        db.close()


@repo_bp.route("/trash/empty", methods=["POST"])
@login_required
def empty_trash():
    user_key = _user_key()
    db = SessionLocal()
    try:
        docs = db.query(RepositoryDocument).filter(
            RepositoryDocument.user_key == user_key,
            RepositoryDocument.status == "trashed",
        ).all()
        for doc in docs:
            delete_doc_storage(doc.id)
            db.delete(doc)
        db.commit()
        return jsonify({"success": True, "count": len(docs)})
    finally:
        db.close()


# ─── Versions ─────────────────────────────────────────────────────────────


@repo_bp.route("/documents/<doc_id>/versions", methods=["GET"])
@login_required
def list_versions(doc_id):
    db = SessionLocal()
    try:
        versions = db.query(DocumentVersion).filter(
            DocumentVersion.document_id == doc_id
        ).order_by(DocumentVersion.version_number.desc()).all()

        return jsonify({
            "versions": [
                {
                    "id": v.id,
                    "version_number": v.version_number,
                    "file_name": v.file_name,
                    "file_size": v.file_size,
                    "file_hash": v.file_hash,
                    "uploaded_by": v.uploaded_by,
                    "change_notes": v.change_notes,
                    "created_at": v.created_at,
                }
                for v in versions
            ]
        })
    finally:
        db.close()


@repo_bp.route("/documents/<doc_id>/versions", methods=["POST"])
@login_required
def upload_version(doc_id):
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    change_notes = request.form.get("change_notes", "")

    db = SessionLocal()
    try:
        doc = db.query(RepositoryDocument).filter(RepositoryDocument.id == doc_id).first()
        if not doc:
            return jsonify({"error": "Document not found"}), 404

        new_version = doc.current_version + 1
        filename = file.filename or doc.name

        import tempfile
        tmp = tempfile.NamedTemporaryFile(delete=False)
        try:
            file.save(tmp.name)
            tmp.close()

            from app.services.storage import compute_hash, store_version
            result = store_version(doc.id, new_version, open(tmp.name, "rb"), filename)

            ver = DocumentVersion(
                document_id=doc.id,
                version_number=new_version,
                file_name=filename,
                file_path=result["file_path"],
                file_size=result["file_size"],
                file_hash=result["file_hash"],
                uploaded_by=_user_key(),
                change_notes=change_notes or f"Version {new_version}",
            )
            db.add(ver)
            doc.current_version = new_version
            doc.size = result["file_size"]
            doc.file_hash = result["file_hash"]
            doc.updated_at = time.time()
            db.commit()

            return jsonify({
                "success": True,
                "version": {
                    "id": ver.id,
                    "version_number": ver.version_number,
                    "file_name": ver.file_name,
                    "file_size": ver.file_size,
                    "file_hash": ver.file_hash,
                    "change_notes": ver.change_notes,
                    "created_at": ver.created_at,
                }
            }), 201
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass
    finally:
        db.close()


@repo_bp.route("/documents/<doc_id>/versions/<int:version>/download", methods=["GET"])
@login_required
def download_version(doc_id, version):
    db = SessionLocal()
    try:
        ver = db.query(DocumentVersion).filter(
            DocumentVersion.document_id == doc_id,
            DocumentVersion.version_number == version,
        ).first()
        if not ver:
            return jsonify({"error": "Version not found"}), 404

        if not os.path.exists(ver.file_path):
            return jsonify({"error": "File not found on disk"}), 404

        return send_file(
            ver.file_path,
            as_attachment=True,
            download_name=ver.file_name,
        )
    finally:
        db.close()


@repo_bp.route("/documents/<doc_id>/versions/<int:version>/restore", methods=["POST"])
@login_required
def restore_version(doc_id, version):
    db = SessionLocal()
    try:
        doc = db.query(RepositoryDocument).filter(RepositoryDocument.id == doc_id).first()
        if not doc:
            return jsonify({"error": "Document not found"}), 404

        ver = db.query(DocumentVersion).filter(
            DocumentVersion.document_id == doc_id,
            DocumentVersion.version_number == version,
        ).first()
        if not ver:
            return jsonify({"error": "Version not found"}), 404

        # Create a new version as a copy of this one
        new_version = doc.current_version + 1

        import shutil
        from app.services.storage import get_doc_dir
        new_ver_dir = os.path.join(get_doc_dir(doc_id), f"v{new_version}")
        os.makedirs(new_ver_dir, exist_ok=True)

        new_file_path = os.path.join(new_ver_dir, ver.file_name)
        if os.path.exists(ver.file_path):
            shutil.copy2(ver.file_path, new_file_path)

        import hashlib
        new_hash = ""
        if os.path.exists(new_file_path):
            h = hashlib.sha256()
            with open(new_file_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            new_hash = h.hexdigest()

        new_ver = DocumentVersion(
            document_id=doc_id,
            version_number=new_version,
            file_name=ver.file_name,
            file_path=new_file_path,
            file_size=ver.file_size,
            file_hash=new_hash,
            uploaded_by=_user_key(),
            change_notes=f"Restored from v{version}",
        )
        db.add(new_ver)
        doc.current_version = new_version
        doc.file_hash = new_hash
        doc.size = ver.file_size
        doc.updated_at = time.time()
        db.commit()

        return jsonify({
            "success": True,
            "version": {
                "id": new_ver.id,
                "version_number": new_ver.version_number,
                "file_name": new_ver.file_name,
                "file_size": new_ver.file_size,
                "change_notes": new_ver.change_notes,
                "created_at": new_ver.created_at,
            }
        })
    finally:
        db.close()


# ─── Comments ─────────────────────────────────────────────────────────────


@repo_bp.route("/documents/<doc_id>/comments", methods=["GET"])
@login_required
def list_comments(doc_id):
    db = SessionLocal()
    try:
        comments = db.query(DocumentComment).filter(
            DocumentComment.document_id == doc_id
        ).order_by(DocumentComment.created_at.asc()).all()

        return jsonify({
            "comments": [
                {
                    "id": c.id,
                    "user_email": c.user_email,
                    "content": c.content,
                    "created_at": c.created_at,
                }
                for c in comments
            ]
        })
    finally:
        db.close()


@repo_bp.route("/documents/<doc_id>/comments", methods=["POST"])
@login_required
def add_comment(doc_id):
    data = request.json or {}
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"error": "Comment content is required"}), 400

    user_key = _user_key()
    db = SessionLocal()
    try:
        doc = db.query(RepositoryDocument).filter(RepositoryDocument.id == doc_id).first()
        if not doc:
            return jsonify({"error": "Document not found"}), 404

        comment = DocumentComment(
            document_id=doc_id,
            user_email=user_key,
            content=content,
        )
        db.add(comment)
        db.commit()
        db.refresh(comment)

        return jsonify({
            "success": True,
            "comment": {
                "id": comment.id,
                "user_email": comment.user_email,
                "content": comment.content,
                "created_at": comment.created_at,
            }
        }), 201
    finally:
        db.close()


@repo_bp.route("/documents/<doc_id>/comments/<comment_id>", methods=["DELETE"])
@login_required
def delete_comment(doc_id, comment_id):
    user_key = _user_key()
    db = SessionLocal()
    try:
        comment = db.query(DocumentComment).filter(
            DocumentComment.id == comment_id,
            DocumentComment.document_id == doc_id,
        ).first()
        if not comment:
            return jsonify({"error": "Comment not found"}), 404
        if comment.user_email != user_key:
            return jsonify({"error": "Not authorized to delete this comment"}), 403
        db.delete(comment)
        db.commit()
        return jsonify({"success": True})
    finally:
        db.close()


# ─── Metadata helpers ────────────────────────────────────────────────────


@repo_bp.route("/categories", methods=["GET"])
@login_required
def list_categories():
    db = SessionLocal()
    try:
        cats = db.query(DocumentCategory).order_by(DocumentCategory.name).all()
        return jsonify({
            "categories": [
                {"id": c.id, "name": c.name, "icon": c.icon, "parent_id": c.parent_id}
                for c in cats
            ]
        })
    finally:
        db.close()


@repo_bp.route("/departments", methods=["GET"])
@login_required
def list_departments():
    db = SessionLocal()
    try:
        depts = db.query(Department).order_by(Department.name).all()
        return jsonify({
            "departments": [
                {"id": d.id, "name": d.name, "code": d.code}
                for d in depts
            ]
        })
    finally:
        db.close()


@repo_bp.route("/stats", methods=["GET"])
@login_required
def repo_stats():
    user_key = _user_key()
    db = SessionLocal()
    try:
        total = db.query(RepositoryDocument).filter(
            RepositoryDocument.user_key == user_key,
            RepositoryDocument.status == "active",
        ).count()
        trashed = db.query(RepositoryDocument).filter(
            RepositoryDocument.user_key == user_key,
            RepositoryDocument.status == "trashed",
        ).count()
        favorites = db.query(RepositoryDocument).filter(
            RepositoryDocument.user_key == user_key,
            RepositoryDocument.is_favorite == 1,
            RepositoryDocument.status == "active",
        ).count()
        total_size = db.query(
            func.coalesce(func.sum(RepositoryDocument.size), 0)
        ).filter(
            RepositoryDocument.user_key == user_key,
            RepositoryDocument.status == "active",
        ).scalar()

        return jsonify({
            "total": total,
            "trashed": trashed,
            "favorites": favorites,
            "total_size": total_size,
        })
    finally:
        db.close()
