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


def _file_choices(unique_fids: set, registry: dict) -> list:
    """Structured file options (file_id + name + department) for the prompt."""
    choices = []
    for fid in sorted(unique_fids, key=lambda f: registry.get(f, {}).get("name", "")):
        entry = registry.get(fid, {})
        choices.append({
            "file_id": fid,
            "name": entry.get("name") or fid,
            "department": entry.get("department") or "",
        })
    return choices


def _select_file_response(question: str, options: list) -> dict:
    """Return a response that prompts the user to pick a file before answering."""
    opts = "; ".join(f"{c['name']} (dept: {c['department']})" for c in options) if options else "no files"
    return {
        "response": (
            f"I found this question could relate to multiple documents: {opts}. "
            "Please tell me which file you'd like me to use, or upload the specific document and ask again."
        ),
        "sources": [],
        "chunks_used": 0,
        "timestamp": time.time(),
        "selectable_files": options,
    }


def _resolve_file_selection(question: str, registry: dict, indexed_file_ids: set) -> str | None:
    """Resolve a file-selection reply to a file_id.

    Matches: exact filename-with-extension mentioned anywhere in the reply
    ("use Shipments.csv", "what is in Shipments.csv?"), a verb-prefixed
    selection ("use the shipments file"), or a short bare-name reply
    ("Shipments"). Deliberately strict: a content question like "how many
    shipments are in transit?" must NOT auto-scope to Shipments.csv.
    """
    if not question or not registry:
        return None
    q = question.strip().lower()
    if len(q) > 60:
        return None

    verb_hit = re.match(r"^(?:please\s+)?(?:use|select|pick|choose|read|open|analyze|look\s+at|from|with|the)\s+(?:file\s+)?(.+)$", q)
    candidate = verb_hit.group(1).strip() if verb_hit else None

    def clean(n):
        s = re.sub(r"\.(?:csv|xlsx?|pdf|txt)$", "", n.lower()).strip()
        return re.sub(r"\s+(file|document)$", "", s).strip()

    for fid, entry in registry.items():
        name = (entry.get("name") or "").strip()
        if not name or fid not in indexed_file_ids:
            continue
        name_l = name.lower()
        # Filename with extension mentioned anywhere (strong signal).
        if name_l in q:
            return fid
        # Verb-prefixed selection matching the name/stem.
        if candidate and clean(candidate) == clean(name):
            return fid
        # Short bare-name reply that IS the file ("Shipments" or "Shipments.csv").
        if len(q) <= 30 and (q == name_l or clean(q) == clean(name)):
            return fid
    return None


def _recover_pending_question(user_key: str, session_id: str) -> str | None:
    """Return the last user question from the session, so a file-selection
    reply can re-answer the question that triggered the ambiguity prompt."""
    try:
        msgs = list_chat_messages(user_key, session_id)
    except Exception:
        return None
    for m in reversed(msgs):
        if m.get("role") == "user" and m.get("content", "").strip():
            return m["content"].strip()
    return None


def _recover_context_file(user_key: str, session_id: str) -> str | None:
    """Return the file_id most recently cited in the session's answers, so a
    short follow-up ('show me pending task') stays scoped to the file the user
    just picked instead of re-triggering the ambiguity prompt."""
    try:
        msgs = list_chat_messages(user_key, session_id)
    except Exception:
        return None
    for m in reversed(msgs):
        if m.get("role") == "assistant":
            sources = m.get("sources") or []
            fids = {s.get("file_id") for s in sources if s.get("file_id")}
            if len(fids) == 1:
                return fids.pop()
    return None


def _ctx_relevant(store, question: str, ctx_file_id: str) -> bool:
    """True if the cited file still surfaces in a wide search for the follow-up,
    so a short new-topic question ('show me pending task' after discussing a
    medical file) isn't force-scoped to the old file."""
    try:
        pool = store.search(question, top_k=RAGConfig.TOP_K * 3, source_filter=None)
    except EmbeddingServiceError:
        return False
    return ctx_file_id in _get_unique_file_ids(pool)


def _fallback_response(top_chunks: list, registry: dict, label: str) -> dict:
    source_payload = _build_source_payload(top_chunks, registry)
    raw = top_chunks[0].get('text', '') if top_chunks else ''
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


def _ambiguous_files(
    store,
    question: str,
    registry: dict,
    indexed_file_ids: set,
    source_filter,
) -> list | None:
    """Detect if a question spans multiple indexed files via a wide search.

    Returns the file options list when the top-18 pool mixes >=2 real files,
    else None. TOP_K=6 is too narrow — it clusters on a single dominant file
    (e.g. Shipments.csv vs Logistics_Testing_Data.xlsx), hiding ambiguity.
    """
    try:
        pool = store.search(question, top_k=RAGConfig.TOP_K * 3, source_filter=source_filter)
    except EmbeddingServiceError:
        return None
    if not pool:
        current_app.logger.info("[ambig] no pool for %r", question[:60])
        return None
    fids = _get_unique_file_ids(pool)
    current_app.logger.info("[ambig] pool=%d fids=%d %s", len(pool), len(fids), [registry.get(f, {}).get("name", f)[:30] for f in fids][:5])
    if len(fids) < 2:
        return None
    return _file_choices(fids, registry)


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

    # ponytail: a follow-up like "use Shipments.csv" is a file selection, not a
    # new question. Resolve it to the file and re-answer the original question
    # so the ambiguity prompt doesn't loop. Only rewrite the question when the
    # reply is selection-shaped (short, no '?'); a real question like "what's
    # in Shipments.csv?" just scopes to that file as-is.
    if not file_ids:
        selected = _resolve_file_selection(question, registry, indexed_file_ids)
        if selected:
            file_ids = [selected]
            if "?" not in question and len(question.strip()) <= 60:
                pending = _recover_pending_question(user_key, chat_session["session_id"])
                if pending:
                    question = pending
        # ponytail: a short follow-up ("which category has the highest count?")
        # that names no file stays scoped to the file the previous answer cited
        # — as long as that file is still relevant to the follow-up. If it no
        # longer surfaces in the search, fall through to normal ambiguity
        # detection instead of force-scoping to an unrelated file. A deictic
        # reference ("what's in this file?") is about that file by definition,
        # so it skips the similarity gate — a vague "this file" query embeds
        # nowhere near the cited file's chunks and would wrongly drift away.
        elif len(question.strip()) <= 60:
            ctx = _recover_context_file(user_key, chat_session["session_id"])
            if ctx and ctx in indexed_file_ids:
                deictic = bool(re.search(r"\b(this|that|the|above)\s+(file|document|spreadsheet|sheet)\b", question.lower()))
                if deictic or _ctx_relevant(store, question, ctx):
                    file_ids = [ctx]

    route = classify(question, department)
    session_ctx = ""
    from flask import session as _session
    user_email = _session.get("user", "")
    if user_email:
        session_ctx = build_context(user_email, route["domains"][0] if route["domains"] else "general", question)

    context = ""
    top_chunks = []
    source_filter = None
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
            # ponytail: if multiple files are relevant, ask the user to pick one
            # instead of letting the AI guess. Run BEFORE the dominant-file
            # auto-detection below, which would otherwise narrow to one file and
            # skip the prompt. Uses a wide pool because TOP_K=6 clusters on one.
            if top_chunks and not file_ids:
                options = _ambiguous_files(store, question, registry, indexed_file_ids, source_filter)
                if options:
                    prompt = _select_file_response(question, options)
                    append_chat_message(user_key, "user", question, session_id=chat_session["session_id"])
                    append_chat_message(user_key, "assistant", prompt["response"], sources=[], session_id=chat_session["session_id"])
                    return prompt
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

    # ponytail: a follow-up like "use Shipments.csv" is a file selection, not a
    # new question. Resolve it to the file and re-answer the original question
    # so the ambiguity prompt doesn't loop. Only rewrite the question when the
    # reply is selection-shaped (short, no '?'); a real question like "what's
    # in Shipments.csv?" just scopes to that file as-is.
    if not file_ids:
        selected = _resolve_file_selection(question, registry, indexed_file_ids)
        if selected:
            file_ids = [selected]
            if "?" not in question and len(question.strip()) <= 60:
                pending = _recover_pending_question(user_key, chat_session["session_id"])
                if pending:
                    question = pending
        # ponytail: a short follow-up ("which category has the highest count?")
        # that names no file stays scoped to the file the previous answer cited
        # — as long as that file is still relevant to the follow-up. If it no
        # longer surfaces in the search, fall through to normal ambiguity
        # detection instead of force-scoping to an unrelated file. A deictic
        # reference ("what's in this file?") is about that file by definition,
        # so it skips the similarity gate — a vague "this file" query embeds
        # nowhere near the cited file's chunks and would wrongly drift away.
        elif len(question.strip()) <= 60:
            ctx = _recover_context_file(user_key, chat_session["session_id"])
            if ctx and ctx in indexed_file_ids:
                deictic = bool(re.search(r"\b(this|that|the|above)\s+(file|document|spreadsheet|sheet)\b", question.lower()))
                if deictic or _ctx_relevant(store, question, ctx):
                    file_ids = [ctx]

    route = classify(question, department)
    session_ctx = ""
    from flask import session as _session
    user_email = _session.get("user", "")
    if user_email:
        session_ctx = build_context(user_email, route["domains"][0] if route["domains"] else "general", question)

    context = ""
    top_chunks = []
    source_filter = None
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

        # ponytail: if multiple files are relevant, ask the user to pick one
        # instead of letting the AI guess. Run BEFORE the dominant-file
        # auto-detection below, which would otherwise narrow to one file and
        # skip the prompt. Uses a wide pool because TOP_K=6 clusters on one file.
        if not file_ids:
            options = _ambiguous_files(store, question, registry, indexed_file_ids, source_filter)
            if options:
                prompt = _select_file_response(question, options)
                append_chat_message(user_key, "user", question, session_id=chat_session["session_id"])
                append_chat_message(user_key, "assistant", prompt["response"], sources=[], session_id=chat_session["session_id"])
                return prompt

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
