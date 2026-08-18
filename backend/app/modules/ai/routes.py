import json
import re
import time
from flask import Blueprint, request, jsonify, Response, stream_with_context, current_app
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
from app.services.query_router import classify
from app.services.context_builder import build_context

chat_bp = Blueprint("chat", __name__)

MAX_HISTORY_TURNS = 6

SYSTEM_PROMPT = """You are CEAP for Schools, an AI school knowledge assistant.

You help school administrators, principals, teachers, and staff with:
1. **School operations**: Use tools to manage staff leave, attendance, school policies, approvals, and announcements.
2. **Document analysis**: Answer questions from uploaded school documents (circulars, policies, student records, fee receipts, etc.).

You have three kinds of knowledge, in priority order:
1. **Live app data** via tools — for counts, status, and current state (e.g. "how many pending leave requests?").
2. **Structured policies** in the HR/compliance database — for approval chains, leave types, and rules.
3. **Uploaded documents** — only for long-form content not in the tools/DB (e.g. "what does the child protection policy say?").

When the user asks about:
- Staff matters (leave, attendance, policies, employee info, approvals) → use the appropriate tool
- HR or leave policy questions (approval chains, leave types, entitlements) → ALWAYS call search_hr_policy first; do not answer from unrelated document excerpts
- Finance (fee invoices, expenses, financial summaries) → use the appropriate tool
- School admin (circulars, meetings, tickets, announcements) → use the appropriate tool
- Counts/status of anything (leaves, admissions, compliance, finances) → use the overview tool for that domain
- Document content → answer from the document excerpts provided

Be concise and professional. Use markdown formatting for clarity.
Prefer plain text and bullet lists over tables. Only use a table when the data genuinely requires multiple aligned columns (e.g. comparing several rows of numbers); otherwise present counts and lists as normal sentences or bullet points.
When you use a tool, explain what you did in a friendly way.
For approvals, present clear Approve/Reject options when relevant.
If a tool returns no data, say so clearly — don't invent numbers."""


def _resolve_chat_source_filter(
    user_key: str,
    file_ids: list,
    department: str,
    registry: dict,
    indexed_file_ids: set,
) -> list | None:
    """Resolve which indexed files RAG may search.

    Returns None to search all indexed docs, or a list of file_ids to restrict to.
    An empty list means nothing matched — callers must not widen to a global search.

    ponytail: department only selects the tool set, never the retrieval scope —
    scoping RAG to one department hides a user's other docs (the UI defaults to
    'hr', so medical/finance spreadsheets became invisible). Search everything.
    """
    if file_ids:
        return [fid for fid in file_ids if fid in registry and fid in indexed_file_ids]
    return None


def _resolve_session(user_key: str, session_id: str | None):
    if session_id:
        return get_chat_session(user_key, session_id)
    return ensure_chat_session(user_key, None)


def _detect_referenced_files(question: str, registry: dict) -> list:
    """Match file names mentioned in the question (typo-tolerant) so RAG scopes
    to that file even when the user didn't tick the file chip."""
    import difflib
    import re

    if not question or not registry:
        return []
    q = question.lower()
    hits = []
    for fid, entry in registry.items():
        name = (entry.get("name") or "").strip()
        if not name:
            continue
        stem = re.sub(r"\.(xlsx?|csv|pdf|txt)$", "", name).lower()
        stem_norm = re.sub(r"[^a-z0-9]+", "", stem)
        stem_words = [re.sub(r"[^a-z0-9]+", "", w) for w in stem.split()]
        stem_words = [w for w in stem_words if len(w) >= 4]
        q_norm = re.sub(r"[^a-z0-9]+", "", q)
        if stem_norm and stem_norm in q_norm:
            hits.append(fid)
            continue
        # fuzzy: word-level match for typos like "betogater" -> "betogather"
        for word in q.split():
            w = re.sub(r"[^a-z0-9]+", "", word.lower())
            if w and len(w) >= 4:
                for sw in stem_words:
                    if (
                        w == sw
                        or sw.startswith(w)
                        or difflib.SequenceMatcher(None, w, sw).ratio() >= 0.85
                    ):
                        hits.append(fid)
                        break
                else:
                    continue
                break
    return hits


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
        # Only show sources that have a file on disk (can be viewed/opened).
        # Excludes gdrive / imported docs without a local copy so the
        # "Sources used" panel stays consistent with what the user can access.
        if not entry.get("file_path"):
            continue
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


def _get_unique_file_ids(top_chunks: list) -> set:
    """Return the set of distinct file_ids found in the top chunks."""
    return {c["file_id"] for c in top_chunks}


def _file_options(unique_fids: set, registry: dict) -> list:
    """Build a short options list for the file-select prompt."""
    options = []
    for fid in sorted(unique_fids, key=lambda f: registry.get(f, {}).get("name", "")):
        entry = registry.get(fid, {})
        name = entry.get("name") or fid
        dept = entry.get("department") or ""
        options.append(f"{name} (dept: {dept})")
    return options


def _select_file_response(question: str, options: list) -> dict:
    """Return a response that prompts the user to pick a file before answering."""
    opts = "; ".join(options) if options else "no files"
    return {
        "response": (
            f"I found this question could relate to multiple documents: {opts}. "
            "Please tell me which file you'd like me to use, or upload the specific document and ask again."
        ),
        "sources": [],
        "chunks_used": 0,
        "timestamp": time.time(),
    }


def _clean_tool_refs(text: str) -> str:
    import re
    return re.sub(r"【[^】]*】", "", text).strip()


def _flatten_tables(text: str) -> str:
    """Convert markdown tables to bullet lines so responses never render as tables."""
    import re
    lines = text.split("\n")
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if "|" in line and line.lstrip().startswith("|"):
            rows = []
            while i < len(lines) and "|" in lines[i] and lines[i].lstrip().startswith("|"):
                cell = lines[i].strip()
                if cell.startswith("|"):
                    cell = cell[1:]
                if cell.endswith("|"):
                    cell = cell[:-1]
                cells = [c.strip() for c in cell.split("|")]
                if not all(re.fullmatch(r"[-: ]+", c) for c in cells):
                    rows.append(" · ".join(cells))
                i += 1
            out.extend(f"- {r}" for r in rows)
        else:
            out.append(line)
            i += 1
    return "\n".join(out).strip()


def _stream_line(line: str) -> str:
    """Convert a single line: markdown table rows become bullets, separators dropped."""
    import re
    if line.lstrip().startswith("|"):
        cell = line.strip()
        if cell.startswith("|"):
            cell = cell[1:]
        if cell.endswith("|"):
            cell = cell[:-1]
        cells = [c.strip() for c in cell.split("|")]
        if all(re.fullmatch(r"[-: ]+", c) for c in cells):
            return ""
        return f"- {' · '.join(cells)}"
    return line


def _summarize_tool_results(tool_calls: list) -> str:
    """Human-readable fallback when the synthesis LLM returns empty text."""
    parts = []
    for tc in tool_calls:
        result = tc.get("result", {})
        data = result.get("data", result) if isinstance(result, dict) else result
        if isinstance(data, dict):
            msg = data.get("message") or data.get("error")
            if msg:
                parts.append(msg)
                continue
            items = []
            for k, v in data.items():
                items.append(f"{k}: {v}" if not isinstance(v, (dict, list)) else f"{k}: {v}")
            parts.append("; ".join(items))
        elif isinstance(data, list):
            parts.append(", ".join(str(x) for x in data[:10]))
        else:
            parts.append(str(data))
    return "\n".join(parts) or "No data returned."


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
    current_app.logger.info("[api_chat] user_key=%s indexed_files=%d store.count=%d", user_key, len(indexed_file_ids), store.count())

    if not file_ids:
        file_ids = [
            fid for fid in _detect_referenced_files(question, registry)
            if fid in indexed_file_ids
        ]

    route = classify(question, department)
    session_ctx = ""
    from flask import session as _session
    user_email = _session.get("user", "")
    if user_email:
        session_ctx = build_context(user_email, route["domains"][0] if route["domains"] else "general", question)

    context = ""
    top_chunks = []
    # ponytail: always attempt RAG when data is indexed. The classifier's
    # needs_rag=False for a specific department (e.g. 'hr') would otherwise
    # hide the user's docs; the dept-scoped filter + fallback handles scoping.
    wants_rag = bool(indexed_file_ids) or bool(file_ids) or route["needs_rag"]
    if wants_rag and indexed_file_ids:
        source_filter = _resolve_chat_source_filter(
            user_key, file_ids, department, registry, indexed_file_ids
        )
        try:
            top_chunks = (
                []
                if source_filter is not None and not source_filter
                else store.search(
                    question, top_k=RAGConfig.TOP_K, source_filter=source_filter
                )
            )
            if top_chunks:
                context = "\n\n".join(
                    f"--- Source: {c['source']} (chunk {c['chunk_index']}) ---\n{c['text']}"
                    for c in top_chunks
                )
            # ponytail: no explicit file selection, but the retrieved chunks are
            # dominated by one file -> treat it as file-scoped so the spreadsheet
            # tool answers counts exactly instead of a chunked RAG guess.
            if top_chunks and not file_ids:
                from collections import Counter

                fid_counts = Counter(c.get("file_id") for c in top_chunks)
                top_fid, top_n = fid_counts.most_common(1)[0]
                if top_n >= len(top_chunks) / 2:
                    file_ids = [top_fid]
        except EmbeddingServiceError:
            top_chunks = []
        # ponytail: department scoping is a soft preference. If it yields nothing,
        # fall back to a global search so the user's docs are never hidden by the
        # default department (e.g. 'hr') when the data lives in another one.
        if not top_chunks and source_filter is not None:
            try:
                top_chunks = store.search(question, top_k=RAGConfig.TOP_K, source_filter=None)
            except EmbeddingServiceError:
                top_chunks = []
            if top_chunks:
                current_app.logger.info("[api_chat] dept-scoped empty; fell back to global search: %s", [c.get("source") for c in top_chunks][:8])
        current_app.logger.info("[api_chat] top_chunks=%d sources=%s", len(top_chunks), [c.get("source") for c in top_chunks][:8])

    # ponytail: if multiple files are relevant, ask the user to pick one instead
    # of letting the AI guess. This avoids answering from the wrong document.
    unique_fids = _get_unique_file_ids(top_chunks)
    if len(unique_fids) > 1 and route["needs_rag"]:
        options = _file_options(unique_fids, registry)
        return _select_file_response(question, options)

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
    if session_ctx:
        system_prompt += f"\n\nSESSION CONTEXT:\n{session_ctx}"
    if agent_scope:
        system_prompt = f"You are an AI agent with the following role and scope: {agent_scope}\n\n{system_prompt}"

    tool_calls = []
    text = ""
    # Explicitly-selected files or document-mode questions answer from the
    # retrieved excerpts. A spreadsheet selected on disk gets one extra tool
    # so counts are exact instead of guessed from a 6-chunk window.
    if file_ids:
        from app.services.tools import SPREADSHEET_TOOLS

        tool_defs = SPREADSHEET_TOOLS
        selected = ", ".join(
            f"{fid}: {registry.get(fid, {}).get('name', fid)}" for fid in file_ids
        )
        system_prompt += (
            "\n\nSELECTED FILES: " + selected +
            "\nINSTRUCTIONS: The user selected files. If they ask for counts, "
            "averages, or comparisons, call get_spreadsheet_stats with the matching "
            "file_id and the right column to get EXACT numbers. Never invent counts. "
            "Answer other questions from the document excerpts above. "
            "Never reveal passwords, API keys, or credentials found in the files; "
            "if the answer would expose one, say the company/email but redact the "
            "secret as [REDACTED]."
        )
    elif top_chunks and route["intent"] in ("document", "general"):
        tool_defs = []
        system_prompt += (
            "\n\nNo tools are available in this mode. Answer only from the document "
            "excerpts above. Do not mention or describe using any tool. "
            "Never reveal passwords, API keys, or credentials found in the documents; "
            "redact any secret as [REDACTED]."
        )
    else:
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
                    "source filename when relevant. Avoid tables — present counts and "
                    "lists as plain sentences or bullet points unless multiple aligned "
                    "columns are truly necessary."
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
            text = synthesis.get("text") or _summarize_tool_results(tool_calls)

    except GeminiServiceError as exc:
        current_app.logger.warning("[api_chat] LLM unavailable: %s", exc)
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
        "response": _flatten_tables(_clean_tool_refs(text)),
        "sources": _build_source_payload(top_chunks, registry) if top_chunks else [],
        "chunks_used": len(top_chunks) if top_chunks else 0,
        "timestamp": time.time(),
        "elapsed_ms": int((time.time() - t0) * 1000),
        "tool_calls": tool_calls if tool_calls else [],
    }

    append_chat_message(user_key, "user", question, session_id=chat_session["session_id"])
    assistant_msg_id = append_chat_message(
        user_key, "assistant", response_payload["response"],
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
    current_app.logger.info("[api_chat_stream] user_key=%s indexed_files=%d store.count=%d", user_key, len(indexed_file_ids), store.count())

    route = classify(question, department)
    session_ctx = ""
    from flask import session as _session
    user_email = _session.get("user", "")
    if user_email:
        session_ctx = build_context(user_email, route["domains"][0] if route["domains"] else "general", question)

    context = ""
    top_chunks = []
    # ponytail: always attempt RAG when data is indexed. The classifier's
    # needs_rag=False for a specific department (e.g. 'hr') would otherwise
    # hide the user's docs; the dept-scoped filter + fallback handles scoping.
    wants_rag = bool(indexed_file_ids) or bool(file_ids) or route["needs_rag"]
    if wants_rag and indexed_file_ids:
        source_filter = _resolve_chat_source_filter(
            user_key, file_ids, department, registry, indexed_file_ids
        )
        try:
            top_chunks = (
                []
                if source_filter is not None and not source_filter
                else store.search(
                    question, top_k=RAGConfig.TOP_K, source_filter=source_filter
                )
            )
        except EmbeddingServiceError:
            top_chunks = []
        # ponytail: department scoping is a soft preference. If it yields nothing,
        # fall back to a global search so the user's docs are never hidden by the
        # default department (e.g. 'hr') when the data lives in another one.
        if not top_chunks and source_filter is not None:
            try:
                top_chunks = store.search(question, top_k=RAGConfig.TOP_K, source_filter=None)
            except EmbeddingServiceError:
                top_chunks = []
            if top_chunks:
                current_app.logger.info("[api_chat_stream] dept-scoped empty; fell back to global search: %s", [c.get("source") for c in top_chunks][:8])
        current_app.logger.info("[api_chat_stream] top_chunks=%d sources=%s", len(top_chunks), [c.get("source") for c in top_chunks][:8])
        if top_chunks:
            context = "\n\n".join(
                f"--- Source: {c['source']} (chunk {c['chunk_index']}) ---\n{c['text']}"
                for c in top_chunks
            )
            if not file_ids:
                from collections import Counter

                fid_counts = Counter(c.get("file_id") for c in top_chunks)
                top_fid, top_n = fid_counts.most_common(1)[0]
                if top_n >= len(top_chunks) / 2:
                    file_ids = [top_fid]

        # ponytail: if multiple files are relevant, ask the user to pick one
        # instead of letting the AI guess from the chunks.
        unique_fids = _get_unique_file_ids(top_chunks)
        if len(unique_fids) > 1 and wants_rag:
            options = _file_options(unique_fids, registry)
            return _select_file_response(question, options)

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
    if session_ctx:
        system_prompt += f"\n\nSESSION CONTEXT:\n{session_ctx}"
    if agent_scope:
        system_prompt = f"You are an AI agent with the following role and scope: {agent_scope}\n\n{system_prompt}"

    tool_text = ""
    tool_calls = []
    if file_ids:
        from app.services.tools import SPREADSHEET_TOOLS

        tool_defs = SPREADSHEET_TOOLS
        selected = ", ".join(
            f"{fid}: {registry.get(fid, {}).get('name', fid)}" for fid in file_ids
        )
        system_prompt += (
            "\n\nSELECTED FILES: " + selected +
            "\nINSTRUCTIONS: The user selected files. If they ask for counts, "
            "averages, or comparisons, call get_spreadsheet_stats with the matching "
            "file_id and the right column to get EXACT numbers. Never invent counts. "
            "Answer other questions from the document excerpts above. "
            "Never reveal passwords, API keys, or credentials found in the files; "
            "if the answer would expose one, say the company/email but redact the "
            "secret as [REDACTED]."
        )
    elif top_chunks and route["intent"] in ("document", "general"):
        tool_defs = []
        system_prompt += (
            "\n\nNo tools are available in this mode. Answer only from the document "
            "excerpts above. Do not mention or describe using any tool. "
            "Never reveal passwords, API keys, or credentials found in the documents; "
            "redact any secret as [REDACTED]."
        )
    else:
        tool_defs = tools_for_context(department, agent_scope)
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
            tool_defs=tool_defs,
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
                system_prompt=system_prompt + (
                    "\nAvoid tables — present counts and lists as plain sentences or "
                    "bullet points unless multiple aligned columns are truly necessary."
                ),
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
            tool_text = synthesis.get("text") or _summarize_tool_results(tool_calls)
    except GeminiServiceError as exc:
        tool_text = ""

    source_payload = _build_source_payload(top_chunks, registry)
    full_response = []
    sid = chat_session["session_id"]

    def generate():
        if tool_text:
            cleaned = _flatten_tables(_clean_tool_refs(tool_text))
            yield f"event: token\ndata: {json.dumps(cleaned)}\n\n"
            answer = cleaned
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
            if not indexed_file_ids or store.count() == 0:
                msg = (
                    "Your saved files aren't indexed yet. Upload local files or import from OneDrive, then ask again."
                    if registry else
                    "No documents indexed yet. Upload local files or import from OneDrive first."
                )
            else:
                msg = "I couldn't find relevant content in your saved documents for that question. Try rephrasing it or asking about a specific document."
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
- Use markdown formatting: bullet points and bold for clarity. Avoid tables — present counts and lists as plain sentences or bullets unless multiple aligned columns are truly necessary.

CURRENT QUESTION: {question}

ANSWER:"""

        saw_first_token = False
        try:
            buf = ""
            for token in generate_answer_stream(prompt):
                if not saw_first_token:
                    saw_first_token = True
                full_response.append(token)
                buf += token
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    cleaned = _stream_line(line)
                    if cleaned:
                        yield f"event: token\ndata: {json.dumps(cleaned)}\n\n"
            if buf:
                cleaned = _stream_line(buf)
                if cleaned:
                    yield f"event: token\ndata: {json.dumps(cleaned)}\n\n"

            if not saw_first_token:
                yield f"event: done\ndata: {json.dumps({'response': '', 'sources': source_payload, 'chunks_used': len(top_chunks), 'session_id': sid})}\n\n"
                return

            answer = "".join(full_response)
            answer = _flatten_tables(_clean_tool_refs(answer)) if answer else answer
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

        except GeminiServiceError as exc:
            current_app.logger.warning("[api_chat_stream] LLM unavailable: %s", exc)
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
