"""File storage service for Document Repository 2.0."""

import os
import shutil
import hashlib
import time
import uuid
from pathlib import Path

STORAGE_BASE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "storage",
)


def init_storage():
    _ensure_dir(STORAGE_BASE)
    _ensure_dir(os.path.join(STORAGE_BASE, "docs"))


def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def get_doc_dir(doc_id: str) -> str:
    return os.path.join(STORAGE_BASE, "docs", doc_id[:2], doc_id)


def compute_hash(file_path: str) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def store_version(doc_id: str, version: int, file_obj, filename: str) -> dict:
    doc_dir = get_doc_dir(doc_id)
    ver_dir = os.path.join(doc_dir, f"v{version}")
    _ensure_dir(ver_dir)

    dest_path = os.path.join(ver_dir, filename)

    if hasattr(file_obj, "save"):
        file_obj.save(dest_path)
    else:
        with open(dest_path, "wb") as f:
            shutil.copyfileobj(file_obj, f)

    file_size = os.path.getsize(dest_path)
    file_hash = compute_hash(dest_path)

    return {
        "file_path": dest_path,
        "file_size": file_size,
        "file_hash": file_hash,
    }


def get_version_path(doc_id: str, version: int, filename: str) -> str:
    doc_dir = get_doc_dir(doc_id)
    return os.path.join(doc_dir, f"v{version}", filename)


def list_version_files(doc_id: str) -> list:
    doc_dir = get_doc_dir(doc_id)
    if not os.path.exists(doc_dir):
        return []
    versions = []
    for entry in sorted(os.listdir(doc_dir), key=lambda x: int(x[1:]) if x.startswith("v") else 0):
        ver_dir = os.path.join(doc_dir, entry)
        if os.path.isdir(ver_dir):
            files = os.listdir(ver_dir)
            versions.append({
                "version_dir": entry,
                "files": files,
            })
    return versions


def delete_doc_storage(doc_id: str):
    doc_dir = get_doc_dir(doc_id)
    if os.path.exists(doc_dir):
        shutil.rmtree(doc_dir)


def duplicate_exists(file_hash: str) -> str | None:
    from app.db import SessionLocal
    from app.models import RepositoryDocument

    db = SessionLocal()
    try:
        existing = (
            db.query(RepositoryDocument)
            .filter(RepositoryDocument.file_hash == file_hash)
            .first()
        )
        if existing:
            return existing.id
        return None
    finally:
        db.close()
