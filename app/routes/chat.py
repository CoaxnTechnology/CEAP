"""
app/routes/chat.py

Adds conversation memory: the frontend sends the last N turns as `history`,
which gets injected into the Gemini prompt so the AI remembers context.
"""

import time
from flask import Blueprint, request, jsonify
from app.auth_helpers import login_required
from app.config import RAGConfig
from app.services.persistence import (
    append_chat_message,
    clear_chat_messages,
    create_chat_session,
    delete_chat_session,
    ensure_chat_session,
    get_chat_session,
    list_chat_messages,
    list_chat_sessions,
    update_chat_session_title,
)
from app.services.rag import get_store, get_registry, _user_key
from app.services.gemini import GeminiServiceError, generate_answer
from app.services.vector_store import EmbeddingServiceError

chat_bp = Blueprint("chat", __name__)

# Max past turns to include (1 turn = 1 user msg + 1 assistant reply)
MAX_HISTORY_TURNS = 6


def _resolve_session(user_key: str, session_id: str | None):
    if session_id:
        return get_chat_session(user_key, session_id)
    return ensure_chat_session(user_key, None)


def _build_source_payload(top_chunks: list, registry: dict) -> list:
    sources = []
    seen = set()

    for chunk in top_chunks:
        key = (chunk["file_id"], chunk["chunk_index"])
        if key in seen:
            continue
        seen.add(key)

        entry = registry.get(chunk["file_id"], {})
        text = (chunk.get("text") or "").strip()
        sources.append(
            {
                "file_id": chunk["file_id"],
                "name": entry.get("name") or chunk["source"],
                "source": entry.get("source", "local"),
                "chunk_index": chunk["chunk_index"],
                "excerpt": (text[:220] + "…") if len(text) > 220 else text,
                "text": text,
                "size": entry.get("size", 0),
                "uploaded_at": entry.get("uploaded_at"),
            }
        )

    return sources


def _fallback_response(top_chunks: list, registry: dict, label: str) -> dict:
    source_payload = _build_source_payload(top_chunks, registry)
    return {
        "response": (
            f"{label}\n\n"
            f"**Most relevant passage:**\n\n{top_chunks[0]['text'][:300]}…"
        ),
        "sources": source_payload,
        "chunks_used": len(top_chunks),
        "timestamp": time.time(),
    }


@chat_bp.route("/api/chat/session", methods=["GET"])
@login_required
def get_current_chat_session():
    user_key = _user_key()
    session_id = request.args.get("session_id", "").strip() or None
    session_info = _resolve_session(user_key, session_id)
    if session_id and not session_info:
        return jsonify({"error": "Session not found"}), 404
    messages = list_chat_messages(user_key, session_info["session_id"])
    return jsonify({"session": session_info, "messages": messages})


@chat_bp.route("/api/chat/sessions", methods=["GET"])
@login_required
def get_chat_sessions():
    user_key = _user_key()
    sessions = list_chat_sessions(user_key)
    if not sessions:
        sessions = [create_chat_session(user_key)]
    return jsonify({"sessions": sessions})


@chat_bp.route("/api/chat/sessions", methods=["POST"])
@login_required
def create_new_chat_session():
    data = request.json or {}
    title = (data.get("title") or "").strip() or "New Chat"
    session_info = create_chat_session(_user_key(), title)
    return jsonify({"success": True, "session": session_info}), 201


@chat_bp.route("/api/chat/sessions/<session_id>", methods=["PATCH"])
@login_required
def rename_chat_session(session_id):
    data = request.json or {}
    title = (data.get("title") or "").strip()
    session_info = update_chat_session_title(_user_key(), session_id, title)
    if not session_info:
        return jsonify({"error": "Session not found"}), 404
    return jsonify({"success": True, "session": session_info})


@chat_bp.route("/api/chat/sessions/<session_id>", methods=["DELETE"])
@login_required
def remove_chat_session(session_id):
    user_key = _user_key()
    if not delete_chat_session(user_key, session_id):
        return jsonify({"error": "Session not found"}), 404

    sessions = list_chat_sessions(user_key)
    if not sessions:
        sessions = [create_chat_session(user_key)]

    return jsonify(
        {
            "success": True,
            "current_session_id": sessions[0]["session_id"],
            "sessions": sessions,
        }
    )


@chat_bp.route("/api/chat/session", methods=["DELETE"])
@login_required
def clear_current_chat_session():
    user_key = _user_key()
    session_id = request.args.get("session_id", "").strip() or None
    session_info = _resolve_session(user_key, session_id)
    if session_id and not session_info:
        return jsonify({"error": "Session not found"}), 404
    clear_chat_messages(user_key, session_info["session_id"])
    return jsonify({"success": True})


@chat_bp.route("/api/chat", methods=["POST"])
@login_required
def api_chat():
    data     = request.json or {}
    question = data.get("question", "").strip()
    file_ids = data.get("file_ids", [])
    session_id = (data.get("session_id") or "").strip() or None
    history  = data.get("history", [])   # list of {role, content}

    if not question:
        return jsonify({"error": "No question provided"}), 400

    user_key = _user_key()
    chat_session = _resolve_session(user_key, session_id)
    if session_id and not chat_session:
        return jsonify({"error": "Session not found"}), 404

    store    = get_store()
    registry = get_registry()
    indexed_file_ids = store.indexed_file_ids()

    if not indexed_file_ids:
        if registry:
            return jsonify({
                "response": "Your saved files are not searchable right now. Re-upload them to rebuild the index, then ask again."
            })
        return jsonify({
            "response": "No documents indexed yet. Upload local files or import from OneDrive first."
        })

    source_filter = (
        [fid for fid in file_ids if fid in registry and fid in indexed_file_ids]
        if file_ids else None
    )

    if file_ids and not source_filter:
        return jsonify({
            "response": "The selected files are not indexed yet. Re-upload them to rebuild the index, or clear the selection and use files that are ready."
        })

    try:
        top_chunks = store.search(
            question, top_k=RAGConfig.TOP_K, source_filter=source_filter
        )
    except EmbeddingServiceError as exc:
        return jsonify({"error": str(exc)}), 503

    if not top_chunks:
        return jsonify({
            "response": "Couldn't find relevant information in the indexed documents."
        })

    # ── Build document context ─────────────────────────────────────────────
    context = "\n\n".join(
        f"--- Source: {c['source']} (chunk {c['chunk_index']}) ---\n{c['text']}"
        for c in top_chunks
    )

    # ── Build conversation history block ──────────────────────────────────
    # Keep only the last MAX_HISTORY_TURNS turns to stay within token limits
    recent = history[-(MAX_HISTORY_TURNS * 2):]  # 2 entries per turn (user + assistant)
    history_block = ""
    if recent:
        lines = []
        for msg in recent:
            role    = "User"      if msg.get("role") == "user"      else "Assistant"
            content = msg.get("content", "").strip()
            if content:
                lines.append(f"{role}: {content}")
        if lines:
            history_block = "CONVERSATION HISTORY (most recent first):\n" + "\n".join(lines) + "\n\n"

    # ── Build final prompt ────────────────────────────────────────────────
    prompt = f"""You are DocuMind, an expert document analyst AI.

{history_block}DOCUMENT EXCERPTS (use these as your primary source of truth):
{context}

INSTRUCTIONS:
- Answer using ONLY the document excerpts above.
- If the conversation history provides relevant context, use it to give a more coherent answer.
- Be concise and accurate. Cite the source filename when relevant.
- If the answer is not in the documents, say so clearly.
- Use markdown formatting: bullet points, bold, tables, and code blocks where they improve clarity.

CURRENT QUESTION: {question}

ANSWER:"""

    try:
        answer = generate_answer(prompt)
    except GeminiServiceError:
        response = _fallback_response(
            top_chunks,
            registry,
            "[Gemini temporarily unavailable. Showing the top retrieved passage instead.]",
        )
        append_chat_message(user_key, "user", question, session_id=chat_session["session_id"])
        append_chat_message(
            user_key,
            "assistant",
            response["response"],
            sources=response["sources"],
            session_id=chat_session["session_id"],
        )
        response["session_id"] = chat_session["session_id"]
        return jsonify(response)

    if answer is None:
        response = _fallback_response(top_chunks, registry, "[Demo — no Gemini key set]")
        append_chat_message(user_key, "user", question, session_id=chat_session["session_id"])
        append_chat_message(
            user_key,
            "assistant",
            response["response"],
            sources=response["sources"],
            session_id=chat_session["session_id"],
        )
        response["session_id"] = chat_session["session_id"]
        return jsonify(response)

    response = {
        "response":    answer,
        "sources":     _build_source_payload(top_chunks, registry),
        "chunks_used": len(top_chunks),
        "timestamp":   time.time(),
    }
    append_chat_message(user_key, "user", question, session_id=chat_session["session_id"])
    append_chat_message(
        user_key,
        "assistant",
        answer,
        sources=response["sources"],
        session_id=chat_session["session_id"],
    )
    response["session_id"] = chat_session["session_id"]
    return jsonify(response)
