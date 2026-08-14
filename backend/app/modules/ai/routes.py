import json
import re
import time
from flask import Blueprint, request, jsonify, Response, stream_with_context
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
    set_message_feedback,
    update_chat_session_title,
)
from app.db import SessionLocal
from app.models import Document
from app.services.rag import get_store, get_registry, _user_key
from app.services.groq_service import GeminiServiceError, generate_answer, generate_answer_stream, generate_followup_suggestions, generate_answer_with_tools
from app.services.vector_store import EmbeddingServiceError
from app.services.tools import tools_for_context

chat_bp = Blueprint("chat", __name__)

MAX_HISTORY_TURNS = 6

SYSTEM_PROMPT = """You are CEAP for Schools, an AI school knowledge assistant.

You help school administrators, principals, teachers, and staff with:
1. **School operations**: Use tools to manage staff leave, attendance, school policies, approvals, and announcements.
2. **Document analysis**: Answer questions from uploaded school documents (circulars, policies, student records, fee receipts, etc.).

When the user asks about:
- Staff matters (leave, attendance, policies, employee info, approvals) → use the appropriate tool
- Finance (fee invoices, expenses, financial summaries) → use the appropriate tool
- School admin (circulars, meetings, tickets, announcements) → use the appropriate tool
- Document content → answer from the document excerpts provided

Be concise and professional. Use markdown formatting for clarity.
When you use a tool, explain what you did in a friendly way.
For approvals, present clear Approve/Reject options when relevant."""


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
                "excerpt": (text[:220] + "...") if len(text) > 220 else text,
                "text": text,
                "size": entry.get("size", 0),
                "uploaded_at": entry.get("uploaded_at"),
            }
        )

    return sources


def _fallback_response(top_chunks: list, registry: dict, label: str) -> dict:
    source_payload = _build_source_payload(top_chunks, registry)
    raw = top_chunks[0].get('text', '')
    first_line = raw.strip().split('\n')[0] if raw.strip() else '(no text)'
    return {
        "response": (
            f"{label}\n\n"
            f"I found a matching document but couldn't generate a full answer. "
            f"**Preview:** _{first_line}_\n\n"
            f"Try again shortly or check the document directly in your files."
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
    department = (data.get("department") or "").strip()
    session_id = (data.get("session_id") or "").strip() or None
    history  = data.get("history", [])
    agent_scope = (data.get("agent_scope") or "").strip()

    if not question:
        return jsonify({"error": "No question provided"}), 400

    user_key = _user_key()
    chat_session = _resolve_session(user_key, session_id)
    if session_id and not chat_session:
        return jsonify({"error": "Session not found"}), 404

    t0 = time.time()
    store    = get_store()
    registry = get_registry()
    indexed_file_ids = store.indexed_file_ids()

    context = ""
    if indexed_file_ids:
        source_filter = (
            [fid for fid in file_ids if fid in registry and fid in indexed_file_ids]
            if file_ids else None
        )
        try:
            top_chunks = store.search(
                question, top_k=RAGConfig.TOP_K, source_filter=source_filter
            )
            if top_chunks:
                context = "\n\n".join(
                    f"--- Source: {c['source']} (chunk {c['chunk_index']}) ---\n{c['text']}"
                    for c in top_chunks
                )
        except EmbeddingServiceError:
            top_chunks = []
    else:
        top_chunks = []

    recent = history[-(MAX_HISTORY_TURNS * 2):]
    history_block = ""
    if recent:
        lines = []
        for msg in recent:
            role    = "User" if msg.get("role") == "user" else "Assistant"
            content = msg.get("content", "").strip()
            if content:
                lines.append(f"{role}: {content}")
        if lines:
            history_block = "\n".join(lines)

    history_for_tools = [{"role": msg["role"], "content": msg["content"]} for msg in recent] if recent else None

    system_prompt = SYSTEM_PROMPT
    if agent_scope:
        system_prompt = f"You are an AI agent with the following role and scope: {agent_scope}\n\n{system_prompt}"

    tool_calls = []
    text = ""
    tool_defs = tools_for_context(department, agent_scope)

    try:
        doc_context = ""
        if top_chunks:
            doc_context = (
                "RELEVANT DOCUMENTS (use these as your primary source of truth):\n"
                f"{context}\n\n"
            )

        result = generate_answer_with_tools(
            system_prompt=system_prompt,
            user_message=f"{doc_context}{history_block}\n\nUser question: {question}",
            tool_defs=tool_defs,
            history=history_for_tools,
        )
        tool_calls = result.get("tool_calls", [])
        text = result.get("text", "")

        if tool_calls:
            tool_summary = "\n".join(
                f"- {tc['name']}({json.dumps(tc.get('args', {}))}) -> "
                f"{json.dumps(tc['result'].get('data', tc['result']))[:600]}"
                for tc in tool_calls
            )
            synthesis = generate_answer_with_tools(
                system_prompt=(
                    "You are CEAP for Schools. Answer the user's question using the "
                    "tool results and documents provided. Be concise and cite the "
                    "source filename when relevant."
                ),
                user_message=(
                    f"{doc_context}"
                    f"TOOL RESULTS:\n{tool_summary}\n\n"
                    f"User question: {question}\n\n"
                    "Answer based on the tool results and documents above. "
                    "If they don't answer the question, say so clearly."
                ),
                tool_defs=[],
                history=history_for_tools,
            )
            text = synthesis.get("text") or tool_summary

    except GeminiServiceError as exc:
        if top_chunks:
            response = _fallback_response(
                top_chunks, registry,
                "[Service temporarily unavailable. Showing relevant document passages instead.]",
            )
        else:
            return jsonify({"response": f"Sorry, I'm having trouble connecting. Please try again. ({str(exc)})"})
        append_chat_message(user_key, "user", question, session_id=chat_session["session_id"])
        assistant_msg_id = append_chat_message(
            user_key, "assistant", response["response"],
            sources=response.get("sources"),
            session_id=chat_session["session_id"],
        )
        response["session_id"] = chat_session["session_id"]
        response["message_id"] = assistant_msg_id
        return jsonify(response)

    if not text:
        if top_chunks:
            response = _fallback_response(top_chunks, registry, "")
            text = response["response"]
        else:
            text = "I'm not sure how to help with that. You can ask me about staff matters (leaves, attendance, policies), finance (fee invoices, expenses), or school admin (circulars, meetings, announcements)."

    response_payload = {
        "response": text,
        "sources": _build_source_payload(top_chunks, registry) if top_chunks else [],
        "chunks_used": len(top_chunks) if top_chunks else 0,
        "timestamp": time.time(),
        "elapsed_ms": int((time.time() - t0) * 1000),
        "tool_calls": tool_calls if tool_calls else [],
    }

    append_chat_message(user_key, "user", question, session_id=chat_session["session_id"])
    assistant_msg_id = append_chat_message(
        user_key, "assistant", text,
        sources=response_payload["sources"],
        session_id=chat_session["session_id"],
    )
    response_payload["session_id"] = chat_session["session_id"]
    response_payload["message_id"] = assistant_msg_id

    if text and data.get("want_suggestions", True):
        try:
            response_payload["suggestions"] = generate_followup_suggestions(question, text)
        except Exception:
            response_payload["suggestions"] = []

    return jsonify(response_payload)


@chat_bp.route("/api/chat/stream", methods=["POST"])
@login_required
def api_chat_stream():
    data     = request.json or {}
    question = data.get("question", "").strip()
    file_ids = data.get("file_ids", [])
    department = (data.get("department") or "").strip()
    session_id = (data.get("session_id") or "").strip() or None
    history  = data.get("history", [])
    agent_scope = (data.get("agent_scope") or "").strip()

    if not question:
        return jsonify({"error": "No question provided"}), 400

    user_key = _user_key()
    chat_session = _resolve_session(user_key, session_id)
    if session_id and not chat_session:
        return jsonify({"error": "Session not found"}), 404

    store    = get_store()
    registry = get_registry()
    indexed_file_ids = store.indexed_file_ids()

    context = ""
    top_chunks = []
    if indexed_file_ids:
        source_filter = (
            [fid for fid in file_ids if fid in registry and fid in indexed_file_ids]
            if file_ids else None
        )
        if not source_filter and department:
            db = SessionLocal()
            doc_file_ids = [
                r[0] for r in db.query(Document.file_id)
                .filter(Document.user_key == user_key, Document.department == department)
                .all()
            ]
            db.close()
            source_filter = [fid for fid in doc_file_ids if fid in indexed_file_ids]
        try:
            top_chunks = store.search(
                question, top_k=RAGConfig.TOP_K, source_filter=source_filter
            )
        except EmbeddingServiceError:
            top_chunks = []
        if top_chunks:
            context = "\n\n".join(
                f"--- Source: {c['source']} (chunk {c['chunk_index']}) ---\n{c['text']}"
                for c in top_chunks
            )

    recent = history[-(MAX_HISTORY_TURNS * 2):]
    history_block = ""
    if recent:
        lines = []
        for msg in recent:
            role    = "User"      if msg.get("role") == "user"      else "Assistant"
            content = msg.get("content", "").strip()
            if content:
                lines.append(f"{role}: {content}")
        if lines:
            history_block = "CONVERSATION HISTORY:\n" + "\n".join(lines) + "\n\n"
    history_for_tools = [{"role": msg["role"], "content": msg["content"]} for msg in recent] if recent else None

    system_prompt = SYSTEM_PROMPT
    if agent_scope:
        system_prompt = f"You are an AI agent with the following role and scope: {agent_scope}\n\n{system_prompt}"

    tool_text = ""
    tool_calls = []
    if context:
        doc_context = (
            "RELEVANT DOCUMENTS (use these as your primary source of truth):\n"
            f"{context}\n\n"
        )
    else:
        doc_context = ""
    try:
        result = generate_answer_with_tools(
            system_prompt=system_prompt,
            user_message=f"{doc_context}{history_block}\n\nUser question: {question}",
            tool_defs=tools_for_context(department, agent_scope),
            history=history_for_tools,
        )
        tool_calls = result.get("tool_calls", [])
        tool_text = result.get("text", "")
        if tool_calls:
            tool_summary = "\n".join(
                f"- {tc['name']}({json.dumps(tc.get('args', {}))}) -> "
                f"{json.dumps(tc['result'].get('data', tc['result']))[:600]}"
                for tc in tool_calls
            )
            synthesis = generate_answer_with_tools(
                system_prompt=system_prompt,
                user_message=(
                    f"{doc_context}"
                    f"TOOL RESULTS:\n{tool_summary}\n\n"
                    f"{history_block}User question: {question}\n\n"
                    "Answer based on the tool results and documents above. "
                    "If they don't answer the question, say so clearly."
                ),
                tool_defs=[],
                history=history_for_tools,
            )
            tool_text = synthesis.get("text") or tool_summary
    except GeminiServiceError as exc:
        tool_text = ""

    source_payload = _build_source_payload(top_chunks, registry)
    full_response = []
    sid = chat_session["session_id"]

    def generate():
        if tool_text:
            yield f"event: token\ndata: {json.dumps(tool_text)}\n\n"
            answer = tool_text
            append_chat_message(user_key, "user", question, session_id=sid)
            assistant_msg_id = append_chat_message(user_key, "assistant", answer, sources=source_payload, session_id=sid)
            suggestions = []
            try:
                suggestions = generate_followup_suggestions(question, answer)
            except Exception:
                suggestions = []
            yield f"event: done\ndata: {json.dumps({
                'response': answer,
                'sources': source_payload,
                'chunks_used': len(top_chunks),
                'session_id': sid,
                'suggestions': suggestions,
                'message_id': assistant_msg_id,
                'tool_calls': tool_calls,
            })}\n\n"
            return

        if not top_chunks:
            msg = (
                "Your saved files are not searchable right now. Re-upload them to rebuild the index, then ask again."
                if registry else
                "No documents indexed yet. Upload local files or import from OneDrive first."
            )
            yield f"event: done\ndata: {json.dumps({'response': msg, 'sources': [], 'chunks_used': 0, 'session_id': sid})}\n\n"
            return

        prompt = f"""You are CEAP for Schools, an expert school document analyst AI.

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

        saw_first_token = False
        try:
            for token in generate_answer_stream(prompt):
                if not saw_first_token:
                    saw_first_token = True
                full_response.append(token)
                yield f"event: token\ndata: {json.dumps(token)}\n\n"

            if not saw_first_token:
                yield f"event: done\ndata: {json.dumps({'response': '', 'sources': source_payload, 'chunks_used': len(top_chunks), 'session_id': sid})}\n\n"
                return

            answer = "".join(full_response)
            append_chat_message(user_key, "user", question, session_id=sid)
            assistant_msg_id = append_chat_message(user_key, "assistant", answer, sources=source_payload, session_id=sid)

            suggestions = generate_followup_suggestions(question, answer)

            done_data = json.dumps({
                "response": answer,
                "sources": source_payload,
                "chunks_used": len(top_chunks),
                "session_id": sid,
                "suggestions": suggestions,
                "message_id": assistant_msg_id,
            })
            yield f"event: done\ndata: {done_data}\n\n"

        except GeminiServiceError:
            fallback = _fallback_response(
                top_chunks, registry,
                "[AI temporarily unavailable. Showing the top retrieved passage instead.]"
            )
            yield f"event: done\ndata: {json.dumps({**fallback, 'session_id': sid})}\n\n"
        except Exception as exc:
            yield f"event: error\ndata: {json.dumps({'message': str(exc)})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@chat_bp.route("/api/chat/feedback", methods=["POST"])
@login_required
def api_chat_feedback():
    data = request.json or {}
    message_id = data.get("message_id")
    feedback = data.get("feedback")

    if not isinstance(message_id, int):
        return jsonify({"success": False, "error": "message_id is required"}), 400
    if feedback not in (-1, 1, None):
        return jsonify({"success": False, "error": "feedback must be -1, 1, or null"}), 400

    try:
        set_message_feedback(message_id, _user_key(), feedback)
        return jsonify({"success": True})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
