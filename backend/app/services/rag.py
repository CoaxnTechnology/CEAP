"""
app/services/rag.py

RAG orchestration layer.
- Uses ChromaStore (persistent ChromaDB) instead of in-memory VectorStore.
- File metadata is persisted in PostgreSQL.
- Legacy JSON registries are migrated on first access.
"""

import os
import re
import json
import time
import uuid
import hashlib

from flask import session, g

from app.services.persistence import (
    delete_document,
    delete_all_documents,
    delete_all_chat_data,
    list_documents,
    save_document,
)
from app.services.vector_store import ChromaStore
from app.services.chunker import chunk_text

# ── Registry persistence ──────────────────────────────────────────────────
# Each user gets a small JSON file: chroma_db/registries/<user_key>.json
# It stores file metadata (name, size, chunk count, upload time, source).

REGISTRY_DIR = os.getenv("REGISTRY_PATH", "./chroma_db/registries")
os.makedirs(REGISTRY_DIR, exist_ok=True)


def _registry_path(user_key: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9\-_]", "_", user_key)
    return os.path.join(REGISTRY_DIR, f"{safe}.json")


def _load_registry(user_key: str) -> dict:
    path = _registry_path(user_key)
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_registry(user_key: str, registry: dict):
    with open(_registry_path(user_key), "w") as f:
        json.dump(registry, f, indent=2)


def _clear_legacy_registry(user_key: str):
    path = _registry_path(user_key)
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            _save_registry(user_key, {})


# ── Per-request helpers ───────────────────────────────────────────────────


def _clear_request_cache():
    for key in ("user_key_cache", "registry_cache"):
        try:
            g.pop(key, None)
        except Exception:
            pass


def _user_key() -> str:
    """Return current user_key from session, deriving a stable one for logged-in users."""
    try:
        cached = getattr(g, "user_key_cache", None)
        if cached:
            return cached
    except Exception:
        pass

    user_key = session.get("user_key")
    if user_key:
        try:
            g.user_key_cache = user_key
        except Exception:
            pass
        return user_key

    user = (session.get("user") or "").strip().lower()
    if user:
        user_key = hashlib.sha256(user.encode("utf-8")).hexdigest()[:32]
        session["user_key"] = user_key
        try:
            g.user_key_cache = user_key
        except Exception:
            pass
        return user_key

    user_key = str(uuid.uuid4())
    session["user_key"] = user_key
    try:
        g.user_key_cache = user_key
    except Exception:
        pass
    return user_key


def current_user_key() -> str:
    return _user_key()


def get_store() -> ChromaStore:
    """Return a ChromaStore scoped to the current user."""
    return ChromaStore(_user_key())


def get_registry() -> dict:
    """Return the current user's file registry, cached per-request."""
    try:
        cached = getattr(g, "registry_cache", None)
        if cached is not None:
            return cached
    except Exception:
        pass

    user_key = _user_key()
    registry = list_documents(user_key)
    if registry:
        try:
            g.registry_cache = registry
        except Exception:
            pass
        return registry

    legacy_registry = _load_registry(user_key)
    if legacy_registry:
        for file_id, entry in legacy_registry.items():
            save_document(user_key, file_id, entry)
        _clear_legacy_registry(user_key)
        registry = list_documents(user_key)
        try:
            g.registry_cache = registry
        except Exception:
            pass
        return registry

    return {}


# ── Core indexing helper (called by upload + OneDrive import routes) ───────


def register_and_index(
    name: str,
    text: str,
    size: int,
    source: str = "local",
    source_ref: str = "",
    category_id: str = None,
    department: str = None,
    file_path: str = "",
) -> dict:
    return register_and_index_for_user(
        _user_key(), name, text, size, source=source, source_ref=source_ref, category_id=category_id, department=department, file_path=file_path
    )


def register_and_index_for_user(
    user_key: str,
    name: str,
    text: str,
    size: int,
    source: str = "local",
    source_ref: str = "",
    category_id: str = None,
    department: str = None,
    file_path: str = "",
) -> dict:
    """
    Chunk text → embed → upsert into Chroma → persist registry entry.
    Returns the registry entry dict (including file_id).
    """
    _clear_request_cache()

    file_id = str(uuid.uuid4())
    chunks = chunk_text(text, name, file_id)

    ChromaStore(user_key).add_chunks(chunks)

    entry = {
        "name": name,
        "source_name": name,
        "size": size,
        "chunks": len(chunks),
        "uploaded_at": time.time(),
        "source": source,
        "source_ref": source_ref,
        "category_id": category_id,
        "department": department,
        "file_path": file_path,
    }

    save_document(user_key, file_id, entry)

    return {"file_id": file_id, **entry}


def remove_from_index(file_id: str) -> bool:
    """Remove a file from Chroma and the registry. Returns True on success."""
    _clear_request_cache()
    user_key = _user_key()
    registry = get_registry()
    if file_id not in registry:
        return False
    ChromaStore(user_key).remove_file(file_id)
    deleted = delete_document(user_key, file_id)

    legacy_registry = _load_registry(user_key)
    if file_id in legacy_registry:
        legacy_registry.pop(file_id, None)
        if legacy_registry:
            _save_registry(user_key, legacy_registry)
        else:
            _clear_legacy_registry(user_key)

    return deleted


def remove_from_vector_store_only(file_id: str) -> bool:
    """Remove a file from Chroma ONLY (not from registry). Returns True on success."""
    try:
        ChromaStore(_user_key()).remove_file(file_id)
        return True
    except Exception:
        return False


def cleanup_user_store():
    """
    Called on logout.
    ChromaDB data is intentionally kept on disk so files persist across
    login sessions. This is a no-op — just here for backwards compatibility.
    To fully delete a user's data, call delete_user_data() instead.
    """
    pass


def delete_user_data():
    """Hard-delete all Chroma chunks + registry for the current user."""
    from app.services.vector_store import _chroma_client, _collection_name

    user_key = session.get("user_key")
    if not user_key:
        return
    try:
        _chroma_client.delete_collection(_collection_name(user_key))
    except Exception:
        pass
    delete_all_documents(user_key)
    delete_all_chat_data(user_key)
    _clear_legacy_registry(user_key)
