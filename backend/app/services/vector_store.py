"""
app/services/vector_store.py

ChromaDB-backed hybrid store:
  - Chroma HNSW (cosine)  →  semantic ranked list
  - BM25 over candidates  →  keyword ranked list
  - Reciprocal Rank Fusion → final top-k

One persistent Chroma collection per user_key.
Data survives restarts — no re-uploading needed.
"""

import os
import re
import math
from pathlib import Path
from collections import Counter

import chromadb
from chromadb.config import Settings
from flask import g
from sentence_transformers import SentenceTransformer

from app.config import RAGConfig
from app.services.persistence import add_file_chunks, list_file_chunks, remove_file_chunks

# ── Embedding model (loaded lazily to avoid startup failure before first use) ──
EMBED_MODEL = None


class EmbeddingServiceError(Exception):
    pass

# ── Single global ChromaDB client (writes to disk) ────────────────────────
# Resolve a relative CHROMA_PATH against the repo root, not the container CWD
# (/app/backend), so "./chroma_db" always means the mounted volume /app/chroma_db.
_BASE = Path(__file__).parent.parent.parent.parent
_raw = os.getenv("CHROMA_PATH", "").strip()
CHROMA_PATH = str(_BASE / _raw) if _raw and not os.path.isabs(_raw) else (_raw or str(_BASE / "chroma_db"))

_chroma_client = chromadb.PersistentClient(
    path=CHROMA_PATH,
    settings=Settings(anonymized_telemetry=False),
)


def _collection_name(user_key: str) -> str:
    """Chroma names must be 3-63 chars, alphanumeric + hyphens only."""
    safe = re.sub(r"[^a-zA-Z0-9\-]", "-", user_key)
    return f"u-{safe[:60]}"


def get_collection(user_key: str):
    """Get or create a persistent per-user Chroma collection."""
    return _chroma_client.get_or_create_collection(
        name=_collection_name(user_key),
        metadata={"hnsw:space": "cosine"},
    )


# ── Embed helper ──────────────────────────────────────────────────────────


def _embed(texts: list) -> list:
    global EMBED_MODEL
    try:
        if EMBED_MODEL is None:
            EMBED_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
        vecs = EMBED_MODEL.encode(
            texts, normalize_embeddings=True, batch_size=64, show_progress_bar=False
        )
        return vecs.tolist()
    except Exception as exc:
        raise EmbeddingServiceError(
            "The local embedding model is unavailable. On first run, ensure the model can be downloaded or is already cached."
        ) from exc


# ── ChromaStore ───────────────────────────────────────────────────────────


class ChromaStore:
    """
    Drop-in replacement for the old VectorStore class.
    All data persists in ChromaDB on disk — survives server restarts.
    """

    def __init__(self, user_key: str):
        self.user_key = user_key

    @property
    def _col(self):
        return get_collection(self.user_key)

    @property
    def chunks(self):
        """
        Backwards-compat shim: routes check `if not store.chunks`.
        Returns a truthy/falsy proxy based on Chroma collection count.
        """
        return _ChunkProxy(self._col.count())

    def add_chunks(self, new_chunks: list):
        if not new_chunks:
            return
        col = self._col
        texts = [c["text"] for c in new_chunks]
        ids = [f"{c['file_id']}__chunk__{c['chunk_index']}" for c in new_chunks]
        metas = [
            {
                "source": c["source"],
                "file_id": c["file_id"],
                "chunk_index": c["chunk_index"],
            }
            for c in new_chunks
        ]
        embeds = _embed(texts)

        # Upsert in batches of 500 (Chroma per-call limit)
        for i in range(0, len(ids), 500):
            col.upsert(
                ids=ids[i : i + 500],
                embeddings=embeds[i : i + 500],
                documents=texts[i : i + 500],
                metadatas=metas[i : i + 500],
            )

        # Track file IDs in DB cache
        seen = set()
        for c in new_chunks:
            fid = c["file_id"]
            if fid not in seen:
                seen.add(fid)
                add_file_chunks(self.user_key, fid, 0)

    def remove_file(self, file_id: str):
        self._col.delete(where={"file_id": file_id})
        remove_file_chunks(self.user_key, file_id)

    def count(self) -> int:
        return self._col.count()

    def get_file_text(self, file_id: str) -> str:
        col = self._col
        if col.count() == 0:
            return ""
        try:
            results = col.get(where={"file_id": file_id}, include=["documents", "metadatas"])
        except Exception:
            return ""
        docs = results.get("documents") or []
        metas = results.get("metadatas") or []
        chunks = sorted(
            ((m.get("chunk_index", 0), d) for m, d in zip(metas, docs) if isinstance(m, dict)),
            key=lambda x: x[0],
        )
        parts = []
        for i, (_, d) in enumerate(chunks):
            if i == 0:
                parts.append(d)
                continue
            prev = parts[-1]
            overlap = RAGConfig.CHUNK_OVERLAP
            tail = prev[-overlap:]
            if tail and d.startswith(tail):
                parts.append(d[overlap:])
            elif tail and tail.strip() and d.strip().startswith(tail.strip()):
                idx = d.find(tail.strip())
                parts.append(d[idx + len(tail.strip()):])
            else:
                parts.append("\n\n" + d)
        return "".join(p for p in parts if p)

    def indexed_file_ids(self) -> set[str]:
        try:
            key = f"idx_ids_{self.user_key}"
            cached = getattr(g, key, None)
            if cached is not None:
                return cached
        except Exception:
            pass

        result = list_file_chunks(self.user_key)
        if result:
            try:
                setattr(g, key, result)
            except Exception:
                pass
            return result

        if self._col.count() == 0:
            result = set()
            try:
                setattr(g, key, result)
            except Exception:
                pass
            return result

        results = self._col.get()
        metadatas = results.get("metadatas") or []
        ids = results.get("ids") or []
        file_ids = set()

        for i, meta in enumerate(metadatas):
            file_id = None
            if isinstance(meta, dict) and meta.get("file_id"):
                file_id = meta.get("file_id")
            elif i < len(ids):
                parts = ids[i].split("__chunk__")
                if len(parts) >= 1:
                    file_id = parts[0]
            if file_id:
                file_ids.add(file_id)
                add_file_chunks(self.user_key, file_id, 0)

        try:
            setattr(g, key, file_ids)
        except Exception:
            pass

        return file_ids

    def search(self, query: str, top_k: int = None, source_filter: list = None) -> list:
        top_k = top_k or RAGConfig.TOP_K
        col = self._col
        if col.count() == 0:
            return []

        if source_filter is not None and len(source_filter) == 0:
            return []

        if source_filter is not None and len(source_filter) > 1:
            # ponytail: per-file round-robin — cap total to top_k, not len*per_k (was 58*2=116 → 20k tokens → 413)
            per_k = max(2, -(-top_k // len(source_filter)))
            pools = [
                self.search(query, top_k=per_k, source_filter=[fid])
                for fid in source_filter
            ]
            merged = []
            for i in range(per_k):
                for pool in pools:
                    if i < len(pool):
                        merged.append(pool[i])
                        if len(merged) >= top_k:
                            return merged[:top_k]
            return merged[:top_k]

        candidate_k = min(top_k * 6, col.count())
        where = {"file_id": {"$in": source_filter}} if source_filter else None

        # ── Step 1: Chroma semantic (HNSW cosine) ────────────────────────
        qvec = _embed([query])[0]
        results = col.query(
            query_embeddings=[qvec],
            n_results=candidate_k,
            where=where,
            include=["documents", "metadatas"],
        )
        sem_chunks = [
            {
                "text": doc,
                "source": m["source"],
                "file_id": m["file_id"],
                "chunk_index": m["chunk_index"],
            }
            for doc, m in zip(results["documents"][0], results["metadatas"][0])
        ]

        if not sem_chunks:
            return []

        # ── Step 2: BM25 re-rank over the same candidate pool ────────────
        bm25_chunks = _bm25_rank(query, sem_chunks, candidate_k)

        # ── Step 3: Reciprocal Rank Fusion ───────────────────────────────
        return _rrf_merge(sem_chunks, bm25_chunks, top_k)


# ── Chunk proxy (truthy/falsy list) ───────────────────────────────────────


class _ChunkProxy(list):
    def __init__(self, count: int):
        super().__init__(range(count))  # empty list = falsy, non-empty = truthy


# ── BM25 ──────────────────────────────────────────────────────────────────


def _bm25_rank(query: str, pool: list, k: int) -> list:
    terms = set(re.findall(r"\w+", query.lower()))
    if not terms:
        return pool[:k]

    N, df = len(pool), Counter()
    tok_cache = []
    for c in pool:
        toks = re.findall(r"\w+", c["text"].lower())
        tok_cache.append(toks)
        for t in terms & set(toks):
            df[t] += 1

    k1, b = 1.5, 0.75
    avg_len = sum(len(t) for t in tok_cache) / max(N, 1)
    scored = []

    for c, toks in zip(pool, tok_cache):
        tf, dl = Counter(toks), len(toks)
        sc = sum(
            math.log((N - df[t] + 0.5) / (df[t] + 0.5) + 1)
            * tf[t]
            * (k1 + 1)
            / (tf[t] + k1 * (1 - b + b * dl / avg_len))
            for t in terms
            if tf[t]
        )
        scored.append((sc, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:k]]


# ── Reciprocal Rank Fusion ────────────────────────────────────────────────


def _rrf_merge(list_a: list, list_b: list, top_k: int) -> list:
    scores, chunk_map = {}, {}

    for rank, c in enumerate(list_a):
        key = (c["file_id"], c["chunk_index"])
        scores[key] = scores.get(key, 0.0) + 1.0 / (RAGConfig.RRF_K + rank + 1)
        chunk_map[key] = c

    for rank, c in enumerate(list_b):
        key = (c["file_id"], c["chunk_index"])
        scores[key] = scores.get(key, 0.0) + 1.0 / (RAGConfig.RRF_K + rank + 1)
        chunk_map.setdefault(key, c)

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [chunk_map[k] for k, _ in ranked[:top_k]]


# ── Backwards-compat alias & flag ────────────────────────────────────────
VectorStore = ChromaStore  # old code that imports VectorStore still works
USE_FAISS = True  # run.py imports this; ChromaDB's HNSW replaces FAISS
