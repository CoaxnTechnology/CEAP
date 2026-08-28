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

    Returns None to search all indexed docs (General), or a list of file_ids to
    restrict to. An empty list means the department has no docs — callers must
    not widen to a global search (Q3: hide non-dept docs).
    """
    if file_ids:
        return [fid for fid in file_ids if fid in registry and fid in indexed_file_ids]
    dept = (department or "").strip().lower()
    if dept and dept != "general":
        return [
            fid for fid, entry in registry.items()
            if fid in indexed_file_ids and (entry.get("department") or "").strip().lower() == dept
        ]
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
        name = entry.get("name")
        if not name:
            continue
        choices.append({
            "file_id": fid,
            "name": name,
            "department": entry.get("department") or "",
        })
    return choices


def _select_file_response(question: str, options: list) -> dict:
    """Return a response that prompts the user to pick a file before answering."""
    return {
        "response": "Which file would you like me to use?",
        "sources": [],
        "chunks_used": 0,
        "timestamp": time.time(),
        "selectable_files": options,
    }


def _session_has_messages(user_key: str, session_id: str) -> bool:
    """True once the session already holds prior messages (not the opening question)."""
    return bool(list_chat_messages(user_key, session_id))


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
    # ponytail: bare filename with extension mentioned anywhere — even in a
    # long natural question like 'What does "Bereavement-...docx" say about...'
    # must resolve without requiring @-mention or picker. This check is before
    # the len>60 guard so long questions still resolve when they name a file.
    for fid, entry in registry.items():
        name = (entry.get("name") or "").strip()
        if not name or fid not in indexed_file_ids:
            continue
        name_l = name.lower()
        if name_l in q:
            return fid
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

# "What is in X?" style questions — if the question explicitly references a
    # file and no other match was found, scope to a single indexed file whose
    # name has a high character-overlap (SequenceMatcher ratio > 0.8) with the
    # reference term, indicating the user is likely referring to that file.
    # We check each word in the filename (ignoring extension) for a high ratio.
    m = re.match(r"^\s*what\s+is\s+in\s+(.+?)\??\s*$", q, re.IGNORECASE)
    if m:
        term = m.group(1).strip()
        if len(term) >= 2:
            import difflib
            best_fid = None
            best_ratio = 0
            for fid, entry in registry.items():
                if fid not in indexed_file_ids:
                    continue
                name = entry.get("name") or ""
                # Check each word in the filename (ignore extension and spaces)
                name_stripped = re.sub(r"\.(?:csv|xlsx?|pdf|txt)\$", "", name)
                for word in re.split(r"[\s\.]+", name_stripped):
                    ratio = difflib.SequenceMatcher(None, term.lower(), word.lower()).ratio()
                    if ratio > best_ratio and ratio > 0.8:
                        best_ratio = ratio
                        best_fid = fid
            if best_fid is not None:
                return best_fid

    # Question references a file by topic — if the user's question contains
    # enough key words that match the filename, scope to that file so the
    # RAG answer can come from its excerpts. This handles plain-English
    # questions like "What's the fire safety evacuation procedure?" without
    # requiring an @ mention or "what is in X?" pattern.
    topics = re.findall(r"[a-z0-9]+", q)
    if len(topics) >= 2:
        for fid, entry in registry.items():
            if fid not in indexed_file_ids:
                continue
            name = entry.get("name") or ""
            name_words = set(re.findall(r"[a-z0-9]+", name.lower()))
            overlap = len(set(topics) & name_words)
            if overlap >= 2 and any(t in name.lower() for t in topics[:3]):
                return fid

    return None


def _extract_mentioned_file_ids(question: str, registry: dict, indexed_file_ids: set) -> list:
    """Generic bare-name extractor — any file whose exact name (with extension)
    appears anywhere in the question, even in a long sentence. Used so
    `What does \"Bereavement-...docx\" say?` works without @-mention or picker.
    Handles typos like `paysip_09.pdf` -> `payslip_09.pdf` via fuzzy token match.
    Returns all matching indexed file_ids (supports multi-file mentions)."""
    if not question or not registry:
        return []
    import difflib
    import re

    q = question.strip().lower()
    matched = []
    # 1) exact substring (fast, no false positives)
    for fid, entry in registry.items():
        if fid not in indexed_file_ids:
            continue
        name = (entry.get("name") or "").strip()
        if not name:
            continue
        if name.lower() in q:
            matched.append(fid)
    if matched:
        return matched
    # 2) typo-tolerant: extract filename-like tokens and fuzzy-match
    # e.g. "paysip_09.pdf" -> "payslip_09.pdf" (missing 'l')
    tokens = re.findall(r"[\w\-]+\.[\w]{2,5}", q)
    # also consider bare names without extension for robustness
    if not tokens:
        tokens = re.findall(r"[\w\-]{3,}", q)
    for token in tokens:
        best_fid = None
        best_ratio = 0
        for fid, entry in registry.items():
            if fid not in indexed_file_ids or fid in matched:
                continue
            name = (entry.get("name") or "").strip().lower()
            # compare token vs full name and vs name without extension
            name_no_ext = re.sub(r"\.[a-z0-9]{2,5}$", "", name)
            for cand in (name, name_no_ext):
                ratio = difflib.SequenceMatcher(None, token, cand).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_fid = fid
        # typo threshold — 0.85 catches single-char deletions like paysip->payslip
        # but not distant files; require token length >=4 to avoid tiny false matches
        if best_fid and best_ratio >= 0.85 and len(token) >= 4:
            matched.append(best_fid)
    return matched


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


def _wants_all_documents(question: str) -> bool:
    """True when the user explicitly asks to search every document, so the
    ambiguity prompt and context-file scoping are skipped in favour of a global
    search ('list the pending items across all documents')."""
    return bool(re.search(
        r"\b(across\s+all|all\s+(my\s+)?(documents|docs|files)|every\s+(document|file)|everything)\b",
        question.lower(),
    ))


def _is_file_url_request(question: str) -> bool:
    """True if user just wants the file link (give me this file) — return URL wrap, no LLM."""
    ql = (question or "").lower()
    if not ql:
        return False
    triggers = ["give me", "send me", "provide me", "share", "download", "open ", "get me", "give this", "send this"]
    if not any(t in ql for t in triggers):
        return False
    # must reference a file (extension, deictic, or generic "files" for prefix search like "bank_statement files")
    return bool(re.search(r"(\.\w{2,5}\b|this file|that file|the file|files\b)", ql))


def _is_aggregation_question(question: str) -> bool:
    """True for count/compare/enumeration questions where excerpt sampling
    hallucinates ('how many', 'which city has the highest', 'net pay in each').
    These must be answered with exact stats or full-doc text, not a 6-chunk
    RAG window."""
    return bool(re.search(
        r"\b(how many|how much|count|number of|total|average|sum of|"
        r"which\s+\w+\s+(has|have)\s+the\s+(highest|lowest|most|least|largest|smallest)|"
        r"(highest|lowest|most|least)\s+\w+|"
        r"in each of|each of the|every|all of the|list (all|every))\b",
        question.lower(),
    ))


def _spreadsheet_candidates(registry: dict, source_filter, indexed_file_ids: set) -> list:
    """Spreadsheet file_ids in the current retrieval scope (dept filter or all)."""
    scope = source_filter if source_filter is not None else indexed_file_ids
    return [
        fid for fid in scope
        if fid in registry
        and str(registry[fid].get("name") or "").lower().endswith((".xlsx", ".xls", ".csv"))
    ]


def _aggregation_doc_context(
    question: str,
    file_ids: list,
    registry: dict,
    source_filter,
    indexed_file_ids: set,
    store,
    context: str,
    top_chunks: list | None = None,
    drop_excerpts: bool = False,
) -> str:
    """Context for counts/comparison questions — accuracy over sampling.

    - All scoped files are spreadsheets -> no excerpts; get_spreadsheet_stats
      reads the raw file for exact numbers.
    - Otherwise -> inject FULL stitched text of the best keyword-matching
      non-spreadsheet docs (a 6k-char PDF register beats 12 sampled chunks),
      budget-capped so multi-select covers every picked file.
    - Fallback -> normal excerpt context.
    """
    normal = (
        "RELEVANT DOCUMENTS (use these as your primary source of truth):\n"
        f"{context}\n\n"
    ) if context else ""
    if drop_excerpts:
        return ""
    if not _is_aggregation_question(question):
        return normal

    scoped_sheets = set(_spreadsheet_candidates(registry, source_filter, indexed_file_ids))

    if file_ids and all(f in scoped_sheets for f in file_ids):
        return ""

    if file_ids:
        candidates = list(file_ids)
    else:
        # Retrieval may cluster on the wrong doc for count questions — scan the
        # whole dept scope's non-spreadsheet docs and rank by keyword hits.
        scope = source_filter if source_filter is not None else indexed_file_ids
        seen = []
        for c in top_chunks or []:
            fid = c.get("file_id")
            if fid and fid not in seen and fid not in scoped_sheets and fid in scope:
                seen.append(fid)
        for fid in scope:
            if fid not in seen and fid not in scoped_sheets and fid in registry:
                seen.append(fid)
        candidates = seen

    q_words = [w for w in re.findall(r"[a-z]{4,}", question.lower())]
    scored = []
    for fid in candidates[:8]:
        entry = registry.get(fid, {})
        if str(entry.get("name") or "").lower().endswith((".xlsx", ".xls", ".csv")):
            continue
        try:
            full = store.get_file_text(fid)
        except Exception:
            continue
        if not full or len(full) > 20000:
            continue
        low = full.lower()
        score = sum(low.count(w) for w in q_words)
        scored.append((score, fid, full))
    scored.sort(key=lambda t: t[0], reverse=True)
    # ponytail: total char budget keeps multi-doc prompts under free-tier Groq
    # TPM; raise alongside the per-doc 20000 cap on paid tier. A doc that
    # doesn't fit is skipped so a smaller next one still can.
    budget, used, parts = 32000, 0, []
    for _score, fid, full in scored:
        if used + len(full) > budget:
            continue
        name = registry.get(fid, {}).get("name", fid)
        parts.append(
            f"COMPLETE DOCUMENT TEXT: {name} (the entire file — count every "
            "occurrence, do not sample):\n" + full
        )
        used += len(full)
    if not parts:
        return normal
    return "\n\n".join(parts) + "\n\n"


def _is_outside_department(question: str, department: str, file_ids: list) -> bool:
    """True if question is clearly about another department while user is scoped to one.

    Works for ANY department (existing or newly created):
    - General-intent questions (no domain keywords) are never blocked — they may
      live in a doc tagged to any dept (e.g. 'delivery volume' in Transport).
    - Domain-mapped depts (finance/hr/academic/...) block questions whose true
      domain differs from the dept's domain.
    - Custom depts (Transport/IT/Sports/... or any new name) block questions that
      clearly map to a specific OTHER known domain; everything else passes.
    Explicit file_ids (@mention / picker) always win — not outside.
    """
    if file_ids:
        return False
    dept_norm = (department or "").strip().lower()
    if not dept_norm or dept_norm == "general":
        return False
    true_domains = classify(question, "")["domains"]
    if true_domains == ["general"]:
        return False
    dept_to_domain = {
        "finance": "finance",
        "hr": "hr",
        "academic": "academic",
        "admin": "executive",
        "compliance": "compliance",
        "admissions": "admissions",
        "executive": "executive",
        "knowledge": "knowledge",
    }
    expected = dept_to_domain.get(dept_norm)
    if expected:
        return expected not in true_domains
    # Custom/new department with no keyword mapping: block only when the
    # question unambiguously belongs to specific other hard domains.
    # knowledge/workflows are soft catch-alls ("how do I...") — never block on them.
    hard = {"finance", "hr", "academic", "compliance", "admissions", "executive"}
    return bool(true_domains) and all(d in hard for d in true_domains)


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


def _sanitize(text: str) -> str:
    """Clean tool refs and normalise <br> tags so Markdown renders correctly.
    Tables are kept as tables — Markdown.jsx renders them with overflow handling.
    """
    import re
    text = _clean_tool_refs(text)
    # <br> inside table cells / lists → markdown hard break
    text = re.sub(r"<br\s*/?>", "  \n", text, flags=re.I)
    return text.strip()


def _stream_line(line: str) -> str:
    """Pass through; tables are kept. Only normalise <br>."""
    import re
    return re.sub(r"<br\s*/?>", "  \n", line, flags=re.I)


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
    mode = (data.get("mode") or "").strip().lower()  # ponytail: ai | file button

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

    # ponytail: generic bare-name — any file whose exact name (even with typo like
    # "paysip_09.pdf" -> "payslip_09.pdf") appears in the question must resolve
    # without picker/@-mention. Covers any file, multi-file too. Runs even when
    # file_ids already set so a typo mention can expand the selection.
    mentioned = _extract_mentioned_file_ids(question, registry, indexed_file_ids)
    if mentioned:
        file_ids = list(dict.fromkeys(mentioned + list(file_ids or [])))
    # ponytail: a follow-up like "use Shipments.csv" is a file selection, not a
    # new question. Resolve it to the file and re-answer the original question
    # so the ambiguity prompt doesn't loop. Only rewrite the question when the
    # reply is selection-shaped (short, no '?'); a real question like "what's
    # in Shipments.csv?" just scopes to that file as-is.
    if not file_ids and mode != "file":
        selected = _resolve_file_selection(question, registry, indexed_file_ids)
        if selected:
            file_ids = [selected]
            if "?" not in question and len(question.strip()) <= 60:
                pending = _recover_pending_question(user_key, chat_session["session_id"])
                if pending:
                    question = pending
        elif mode != "file" and len(question.strip()) <= 60 and not _wants_all_documents(question) and not _is_aggregation_question(question):
            ctx = _recover_context_file(user_key, chat_session["session_id"])
            if ctx and ctx in indexed_file_ids:
                deictic = bool(re.search(r"\b(this|that|the|above)\s+(file|document|spreadsheet|sheet)\b", question.lower()))
                if deictic or _ctx_relevant(store, question, ctx):
                    file_ids = [ctx]

    # ponytail: file URL request — give link wrap, no LLM chat response
    # mode button separates tasks: file → always return URLs, ai → never return URLs
    is_file_req = _is_file_url_request(question)
    if mode == "file":
        is_file_req = True
    elif mode == "ai":
        is_file_req = False
    if is_file_req:
        ql = question.lower()
        is_generic = ("files" in ql or mode == "file") and not re.search(r"\.\w{2,5}\b", ql)
        if not file_ids or is_generic:
            if is_generic:
                file_ids = []
            generic_ids = []
            # ponytail: universal numbered file — any new file like "report 12" (typo tolerant)
            nums = re.findall(r"\d+", ql)
            if nums:
                import difflib
                q_tokens = re.findall(r"[a-z0-9_]+", ql)
                for fid, entry in registry.items():
                    if fid not in indexed_file_ids:
                        continue
                    name = (entry.get("name") or "").lower()
                    name_nums = re.findall(r"\d+", name)
                    if not name_nums:
                        continue
                    # number must match any query number
                    num_match = False
                    for n_str in nums:
                        try:
                            n = int(n_str)
                        except:
                            continue
                        for nn in name_nums:
                            try:
                                if int(nn) == n:
                                    num_match = True
                                    break
                            except:
                                continue
                        if num_match:
                            break
                    if not num_match:
                        continue
                    # name base fuzzy must match query token (any typo)
                    name_words = re.findall(r"[a-z0-9]+", name.replace("_", " "))
                    name_base = re.sub(r"[\d_]+", "", name).replace(".", "")
                    found = False
                    for qtok in q_tokens:
                        if len(qtok) < 3:
                            continue
                        if qtok in name:
                            found = True
                            break
                        if difflib.SequenceMatcher(None, qtok, name_base).ratio() >= 0.7:
                            found = True
                            break
                        if any(difflib.SequenceMatcher(None, qtok, w).ratio() >= 0.75 for w in name_words):
                            found = True
                            break
                    if found:
                        if fid not in generic_ids:
                            generic_ids.append(fid)
            if not generic_ids:
                import difflib, re as _re
                m = _re.search(r"(\w+)\s+files?", ql)
                if m:
                    prefix = m.group(1)
                    # skip generic trigger words
                    if prefix not in ("give","send","this","that","the","all","my","please","me"):
                        for fid, entry in registry.items():
                            if fid not in indexed_file_ids:
                                continue
                            name = (entry.get("name") or "").lower()
                            # ponytail: typo tolerant prefix — bankstatment -> bank_statement (any typo, thresh 0.7 for missing chars)
                            name_norm = name.replace("_","").replace(".","")
                            prefix_norm = prefix.replace("_","")
                            if prefix in name or difflib.SequenceMatcher(None, prefix_norm, name_norm).ratio() >= 0.7 or any(difflib.SequenceMatcher(None, prefix, w).ratio() >= 0.75 for w in _re.findall(r"[a-z0-9]+", name.replace("_", " "))):
                                generic_ids.append(fid)
            if not generic_ids:
                import difflib
                tokens = [t for t in re.findall(r"[a-z0-9_]+", ql) if len(t) >= 4 and t not in ("give","send","provide","share","download","open","file","files","please")]
                for fid, entry in registry.items():
                    if fid not in indexed_file_ids:
                        continue
                    name = (entry.get("name") or "").lower()
                    name_words = re.findall(r"[a-z0-9]+", name.replace("_", " ").replace(".", " "))
                    name_norm = name.replace("_","").replace(".","")
                    # ponytail: any typo — paysip -> payslip, bankstatment -> bank_statement (thresh 0.7)
                    if tokens and all(tok in name or difflib.SequenceMatcher(None, tok.replace("_",""), name_norm).ratio() >= 0.7 or any(difflib.SequenceMatcher(None, tok, w).ratio() >= 0.75 for w in name_words) for tok in tokens):
                        if fid not in generic_ids:
                            generic_ids.append(fid)
            if not generic_ids and "files" in ql:
                generic_ids = list(indexed_file_ids)
            # ponytail: filter by requested extension (pdf/docx) if mentioned — e.g. "pdf of bankstatmenet"
            req_ext = None
            if re.search(r"\.pdf\b", ql) or re.search(r"\bpdfs?\b", ql):
                req_ext = ".pdf"
            elif re.search(r"\.docx\b", ql) or re.search(r"\bdocx\b", ql):
                req_ext = ".docx"
            elif re.search(r"\.doc\b", ql) or re.search(r"\bdoc\b", ql):
                req_ext = ".doc"
            elif re.search(r"\.xlsx\b", ql) or re.search(r"\bxlsx\b", ql):
                req_ext = ".xlsx"
            if req_ext and generic_ids:
                filtered = [fid for fid in generic_ids if (registry.get(fid, {}).get("name") or "").lower().endswith(req_ext)]
                if filtered:
                    generic_ids = filtered
            if generic_ids:
                # limit to 30 to avoid huge response
                file_ids = generic_ids[:30]
        if file_ids:
            links = []
            for fid in file_ids:
                entry = registry.get(fid, {}) or {}
                name = entry.get("name") or fid
                links.append(f"[{name}](/api/files/{fid}/open)")
            resp_text = "\n\n".join(links)
            append_chat_message(user_key, "user", question, session_id=chat_session["session_id"])
            aid = append_chat_message(user_key, "assistant", resp_text, session_id=chat_session["session_id"])
            return jsonify({"response": resp_text, "sources": [], "chunks_used": 0, "timestamp": time.time(), "session_id": chat_session["session_id"], "message_id": aid})

    route = classify(question, department)
    # Strict dept boundary: don't answer outside-dept questions (Q: finance user asking compliance)
    if _is_outside_department(question, department, file_ids):
        dept_label = (department or "").strip()
        msg = f"This question is outside the **{dept_label}** department. Please switch to **General** or the relevant department to get an answer."
        append_chat_message(user_key, "user", question, session_id=chat_session["session_id"])
        aid = append_chat_message(user_key, "assistant", msg, session_id=chat_session["session_id"])
        return jsonify({"response": msg, "sources": [], "chunks_used": 0, "timestamp": time.time(), "session_id": chat_session["session_id"], "message_id": aid})

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
    # Aggregation questions need wider retrieval — 6 chunks under-counts tables.
    retrieve_k = RAGConfig.TOP_K * 2 if _is_aggregation_question(question) else RAGConfig.TOP_K
    if wants_rag and indexed_file_ids:
        source_filter = _resolve_chat_source_filter(
            user_key, file_ids, department, registry, indexed_file_ids
        )
        try:
            top_chunks = (
                []
                if source_filter is not None and not source_filter
                else store.search(
                    question, top_k=retrieve_k, source_filter=source_filter
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
            if top_chunks and not file_ids and not _wants_all_documents(question) and not _is_aggregation_question(question):
                from collections import Counter

                fid_counts = Counter(c.get("file_id") for c in top_chunks)
                top_fid, top_n = fid_counts.most_common(1)[0]
                if top_n >= len(top_chunks) / 2:
                    file_ids = [top_fid]
        except EmbeddingServiceError:
            top_chunks = []
        # Strict dept scope (Q3): General searches all, dept searches only that dept's docs.
        # Do not widen dept-filtered empty result to global.
        dept_norm = (department or "").strip().lower()
        if not top_chunks and source_filter is not None and dept_norm in ("", "general"):
            try:
                top_chunks = store.search(question, top_k=retrieve_k, source_filter=None)
            except EmbeddingServiceError:
                top_chunks = []
            if top_chunks:
                current_app.logger.info("[api_chat] dept-scoped empty; fell back to global search: %s", [c.get("source") for c in top_chunks][:8])
        elif not top_chunks and source_filter is not None:
            try:
                global_chunks = store.search(question, top_k=retrieve_k, source_filter=None)
            except EmbeddingServiceError:
                global_chunks = []
            if global_chunks and _is_outside_department(question, department, []):
                # Clearly another department's subject (e.g. compliance in Finance)
                dept_label = (department or "").strip()
                msg = f"This question is outside the **{dept_label}** department. No relevant documents found in {dept_label}. Please switch to **General** or the relevant department to get an answer."
                append_chat_message(user_key, "user", question, session_id=chat_session["session_id"])
                aid = append_chat_message(user_key, "assistant", msg, session_id=chat_session["session_id"])
                return jsonify({"response": msg, "sources": [], "chunks_used": 0, "timestamp": time.time(), "session_id": chat_session["session_id"], "message_id": aid})
            if global_chunks:
                # General-intent question ("delivery volume") that merely lives in
                # a doc tagged elsewhere — answer it, don't block.
                top_chunks = global_chunks
                source_filter = None  # retrieval scope widened; tool candidates too
                current_app.logger.info("[api_chat] dept empty; general question answered from global: %s", [c.get("source") for c in top_chunks][:8])
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
    # Exact answers: selected files OR any count/compare question with a
    # spreadsheet in scope get get_spreadsheet_stats, never a 6-chunk guess.
    # ponytail: only force spreadsheet tool when selected/scope actually contains a spreadsheet;
    # for docx/pdf aggregation (e.g. bank_statement_02.docx credits), answer from full doc text.
    sheet_ids = _spreadsheet_candidates(registry, source_filter, indexed_file_ids) if _is_aggregation_question(question) else []
    selected_has_sheet = bool(file_ids and any(
        str(registry.get(fid, {}).get("name") or "").lower().endswith((".xlsx", ".xls", ".csv"))
        for fid in file_ids
    ))
    if file_ids:
        selected = ", ".join(
            f"{fid}: {registry.get(fid, {}).get('name', fid)}" for fid in file_ids
        )
        system_prompt += (
            "\n\nSELECTED FILES: " + selected +
            "\nINSTRUCTIONS: The user selected files. "
            "Answer other questions from the document excerpts above. "
            "Never reveal passwords, API keys, or credentials found in the files; "
            "if the answer would expose one, say the company/email but redact the "
            "secret as [REDACTED]."
        )
        if selected_has_sheet:
            from app.services.tools import SPREADSHEET_TOOLS
            tool_defs = SPREADSHEET_TOOLS
            system_prompt += (
                " If they ask for counts, averages, or comparisons on a spreadsheet, call get_spreadsheet_stats "
                "with the matching file_id and the right column to get EXACT numbers — for totals or comparisons spanning "
                "multiple selected files, make one call PER spreadsheet file_id. Never invent counts. "
                "If the question asks about a document type that none of the selected files contain (e.g. payslips when only an invoice "
                "register is selected), state which files ARE selected and ask the user to select the right ones — never present unrelated "
                "file content as the answer."
            )
            if _is_aggregation_question(question):
                system_prompt += (
                    "\nMANDATORY: This is a counts/comparison question on a spreadsheet. You MUST call "
                    "get_spreadsheet_stats BEFORE answering — once per relevant selected spreadsheet file_id (first without "
                    "column to list columns, then with the matching column). NEVER count from document excerpts — they are samples and will give "
                    "wrong totals."
                )
        elif _is_aggregation_question(question):
            tool_defs = []
            system_prompt += (
                " This is a counts/totals question on non-spreadsheet documents (PDF/DOCX). Do NOT call get_spreadsheet_stats — it only works on xlsx/csv. "
                "Answer by counting directly from the COMPLETE DOCUMENT TEXT provided above. Be exact."
            )
        else:
            tool_defs = tools_for_context(department, agent_scope) if not top_chunks or route["intent"] not in ("document", "general") else []
            if top_chunks and route["intent"] in ("document", "general") and not tool_defs:
                system_prompt += (
                    "\n\nNo tools are available in this mode. Answer only from the document excerpts above. Do not mention or describe using any tool. "
                    "Never reveal passwords, API keys, or credentials found in the documents; redact any secret as [REDACTED]."
                )
    elif sheet_ids:
        from app.services.tools import SPREADSHEET_TOOLS

        tool_defs = SPREADSHEET_TOOLS
        candidates = ", ".join(
            f"{fid}: {registry.get(fid, {}).get('name', fid)}" for fid in sheet_ids
        )
        system_prompt += (
            "\n\nAVAILABLE SPREADSHEETS: " + candidates +
            "\nINSTRUCTIONS: This is a counts/comparison question. You MUST call "
            "get_spreadsheet_stats to answer it — first without a column to list "
            "columns, then with the matching column (e.g. destination/city/status). "
            "Use EXACT numbers from the tool result. NEVER count from document "
            "excerpts; excerpts are samples and will give wrong totals. If no "
            "spreadsheet matches the question's subject, say which files you "
            "checked. Never reveal secrets found in files; redact as [REDACTED]."
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
        drop_excerpts = bool(
            sheet_ids and top_chunks
            and all(c.get("file_id") in set(sheet_ids) for c in top_chunks)
        )
        doc_context = _aggregation_doc_context(
            question, file_ids, registry, source_filter, indexed_file_ids, store, context, top_chunks,
            drop_excerpts=drop_excerpts,
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
        "response": _sanitize(text),
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
    mode = (data.get("mode") or "").strip().lower()  # ponytail: ai | file

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

    # ponytail: generic bare-name — any file whose exact name (even with typo like
    # "paysip_09.pdf" -> "payslip_09.pdf") appears in the question must resolve
    # without picker/@-mention. Covers any file, multi-file too. Runs even when
    # file_ids already set so a typo mention can expand the selection.
    mentioned = _extract_mentioned_file_ids(question, registry, indexed_file_ids)
    if mentioned:
        file_ids = list(dict.fromkeys(mentioned + list(file_ids or [])))
    # ponytail: a follow-up like "use Shipments.csv" is a file selection, not a
    # new question. Resolve it to the file and re-answer the original question
    # so the ambiguity prompt doesn't loop. Only rewrite the question when the
    # reply is selection-shaped (short, no '?'); a real question like "what's
    # in Shipments.csv?" just scopes to that file as-is.
    if not file_ids and mode != "file":
        selected = _resolve_file_selection(question, registry, indexed_file_ids)
        if selected:
            file_ids = [selected]
            if "?" not in question and len(question.strip()) <= 60:
                pending = _recover_pending_question(user_key, chat_session["session_id"])
                if pending:
                    question = pending
        elif mode != "file" and len(question.strip()) <= 60 and not _wants_all_documents(question) and not _is_aggregation_question(question):
            ctx = _recover_context_file(user_key, chat_session["session_id"])
            if ctx and ctx in indexed_file_ids:
                deictic = bool(re.search(r"\b(this|that|the|above)\s+(file|document|spreadsheet|sheet)\b", question.lower()))
                if deictic or _ctx_relevant(store, question, ctx):
                    file_ids = [ctx]

    # ponytail: file URL request — give link wrap, no LLM (stream endpoint returns JSON, frontend handles non-SSE)
    is_file_req = _is_file_url_request(question)
    if mode == "file":
        is_file_req = True
    elif mode == "ai":
        is_file_req = False
    if is_file_req:
        ql = question.lower()
        is_generic = ("files" in ql or mode == "file") and not re.search(r"\.\w{2,5}\b", ql)
        if not file_ids or is_generic:
            if is_generic:
                file_ids = []
            generic_ids = []
            # ponytail: universal numbered file — any new file like "report 12" (typo tolerant)
            nums = re.findall(r"\d+", ql)
            if nums:
                import difflib
                q_tokens = re.findall(r"[a-z0-9_]+", ql)
                for fid, entry in registry.items():
                    if fid not in indexed_file_ids:
                        continue
                    name = (entry.get("name") or "").lower()
                    name_nums = re.findall(r"\d+", name)
                    if not name_nums:
                        continue
                    # number must match any query number
                    num_match = False
                    for n_str in nums:
                        try:
                            n = int(n_str)
                        except:
                            continue
                        for nn in name_nums:
                            try:
                                if int(nn) == n:
                                    num_match = True
                                    break
                            except:
                                continue
                        if num_match:
                            break
                    if not num_match:
                        continue
                    # name base fuzzy must match query token (any typo)
                    name_words = re.findall(r"[a-z0-9]+", name.replace("_", " "))
                    name_base = re.sub(r"[\d_]+", "", name).replace(".", "")
                    found = False
                    for qtok in q_tokens:
                        if len(qtok) < 3:
                            continue
                        if qtok in name:
                            found = True
                            break
                        if difflib.SequenceMatcher(None, qtok, name_base).ratio() >= 0.7:
                            found = True
                            break
                        if any(difflib.SequenceMatcher(None, qtok, w).ratio() >= 0.75 for w in name_words):
                            found = True
                            break
                    if found:
                        if fid not in generic_ids:
                            generic_ids.append(fid)
            if not generic_ids:
                import difflib, re as _re
                m = _re.search(r"(\w+)\s+files?", ql)
                if m:
                    prefix = m.group(1)
                    if prefix not in ("give","send","this","that","the","all","my","please","me"):
                        for fid, entry in registry.items():
                            if fid not in indexed_file_ids:
                                continue
                            name = (entry.get("name") or "").lower()
                            name_norm = name.replace("_","")
                            prefix_norm = prefix.replace("_","")
                            if prefix in name or difflib.SequenceMatcher(None, prefix_norm, name_norm).ratio() >= 0.7 or any(difflib.SequenceMatcher(None, prefix, w).ratio() >= 0.75 for w in _re.findall(r"[a-z0-9]+", name.replace("_", " "))):
                                generic_ids.append(fid)
            if not generic_ids:
                import difflib
                tokens = [t for t in re.findall(r"[a-z0-9_]+", ql) if len(t) >= 4 and t not in ("give","send","provide","share","download","open","file","files","please")]
                for fid, entry in registry.items():
                    if fid not in indexed_file_ids:
                        continue
                    name = (entry.get("name") or "").lower()
                    name_words = re.findall(r"[a-z0-9]+", name.replace("_", " ").replace(".", " "))
                    name_norm = name.replace("_","").replace(".","")
                    if tokens and all(tok in name or difflib.SequenceMatcher(None, tok.replace("_",""), name_norm).ratio() >= 0.7 or any(difflib.SequenceMatcher(None, tok, w).ratio() >= 0.75 for w in name_words) for tok in tokens):
                        if fid not in generic_ids:
                            generic_ids.append(fid)
            if not generic_ids and "files" in ql:
                generic_ids = list(indexed_file_ids)
            # ponytail: filter by requested extension (pdf/docx) if mentioned — e.g. "pdf of bankstatmenet"
            req_ext = None
            if re.search(r"\.pdf\b", ql) or re.search(r"\bpdfs?\b", ql):
                req_ext = ".pdf"
            elif re.search(r"\.docx\b", ql) or re.search(r"\bdocx\b", ql):
                req_ext = ".docx"
            elif re.search(r"\.doc\b", ql) or re.search(r"\bdoc\b", ql):
                req_ext = ".doc"
            elif re.search(r"\.xlsx\b", ql) or re.search(r"\bxlsx\b", ql):
                req_ext = ".xlsx"
            if req_ext and generic_ids:
                filtered = [fid for fid in generic_ids if (registry.get(fid, {}).get("name") or "").lower().endswith(req_ext)]
                if filtered:
                    generic_ids = filtered
            if generic_ids:
                file_ids = generic_ids[:30]
        if file_ids:
            links = []
            for fid in file_ids:
                entry = registry.get(fid, {}) or {}
                name = entry.get("name") or fid
                links.append(f"[{name}](/api/files/{fid}/open)")
            resp_text = "\n\n".join(links)
            append_chat_message(user_key, "user", question, session_id=chat_session["session_id"])
            aid = append_chat_message(user_key, "assistant", resp_text, session_id=chat_session["session_id"])
            return jsonify({"response": resp_text, "sources": [], "chunks_used": 0, "timestamp": time.time(), "session_id": chat_session["session_id"], "message_id": aid})

    route = classify(question, department)
    if _is_outside_department(question, department, file_ids):
        dept_label = (department or "").strip()
        msg = f"This question is outside the **{dept_label}** department. Please switch to **General** or the relevant department to get an answer."
        append_chat_message(user_key, "user", question, session_id=chat_session["session_id"])
        aid = append_chat_message(user_key, "assistant", msg, session_id=chat_session["session_id"])
        # stream endpoint: return JSON prompt (frontend handles non-SSE)
        return jsonify({"response": msg, "sources": [], "chunks_used": 0, "timestamp": time.time(), "session_id": chat_session["session_id"], "message_id": aid})

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
    # Aggregation questions need wider retrieval — 6 chunks under-counts tables.
    retrieve_k = RAGConfig.TOP_K * 2 if _is_aggregation_question(question) else RAGConfig.TOP_K
    if wants_rag and indexed_file_ids:
        source_filter = _resolve_chat_source_filter(
            user_key, file_ids, department, registry, indexed_file_ids
        )
        try:
            top_chunks = (
                []
                if source_filter is not None and not source_filter
                else store.search(
                    question, top_k=retrieve_k, source_filter=source_filter
                )
            )
        except EmbeddingServiceError:
            top_chunks = []
        # Strict dept scope (Q3): General searches all, dept searches only that dept's docs.
        if not top_chunks and source_filter is not None and (department or "").strip().lower() in ("", "general"):
            try:
                top_chunks = store.search(question, top_k=retrieve_k, source_filter=None)
            except EmbeddingServiceError:
                top_chunks = []
            if top_chunks:
                current_app.logger.info("[api_chat_stream] dept-scoped empty; fell back to global search: %s", [c.get("source") for c in top_chunks][:8])
        elif not top_chunks and source_filter is not None:
            try:
                global_chunks = store.search(question, top_k=retrieve_k, source_filter=None)
            except EmbeddingServiceError:
                global_chunks = []
            if global_chunks and _is_outside_department(question, department, []):
                # Clearly another department's subject (e.g. compliance in Finance)
                dept_label = (department or "").strip()
                msg = f"This question is outside the **{dept_label}** department. No relevant documents found in {dept_label}. Please switch to **General** or the relevant department to get an answer."
                append_chat_message(user_key, "user", question, session_id=chat_session["session_id"])
                aid = append_chat_message(user_key, "assistant", msg, session_id=chat_session["session_id"])
                return jsonify({"response": msg, "sources": [], "chunks_used": 0, "timestamp": time.time(), "session_id": chat_session["session_id"], "message_id": aid})
            if global_chunks:
                # General-intent question ("delivery volume") that merely lives in
                # a doc tagged elsewhere — answer it, don't block.
                top_chunks = global_chunks
                source_filter = None  # retrieval scope widened; tool candidates too
                current_app.logger.info("[api_chat_stream] dept empty; general question answered from global: %s", [c.get("source") for c in top_chunks][:8])
        current_app.logger.info("[api_chat_stream] top_chunks=%d sources=%s", len(top_chunks), [c.get("source") for c in top_chunks][:8])

        if top_chunks:
            context = "\n\n".join(
                f"--- Source: {c['source']} (chunk {c['chunk_index']}) ---\n{c['text']}"
                for c in top_chunks
            )
            if not file_ids and not _wants_all_documents(question) and not _is_aggregation_question(question):
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
    # ponytail: only force spreadsheet tool when selected/scope actually contains a spreadsheet;
    # for docx/pdf aggregation, answer from full doc text.
    sheet_ids = _spreadsheet_candidates(registry, source_filter, indexed_file_ids) if _is_aggregation_question(question) else []
    selected_has_sheet = bool(file_ids and any(
        str(registry.get(fid, {}).get("name") or "").lower().endswith((".xlsx", ".xls", ".csv"))
        for fid in file_ids
    ))
    if file_ids:
        selected = ", ".join(
            f"{fid}: {registry.get(fid, {}).get('name', fid)}" for fid in file_ids
        )
        system_prompt += (
            "\n\nSELECTED FILES: " + selected +
            "\nINSTRUCTIONS: The user selected files. "
            "Answer other questions from the document excerpts above. "
            "Never reveal passwords, API keys, or credentials found in the files; "
            "if the answer would expose one, say the company/email but redact the "
            "secret as [REDACTED]."
        )
        if selected_has_sheet:
            from app.services.tools import SPREADSHEET_TOOLS
            tool_defs = SPREADSHEET_TOOLS
            system_prompt += (
                " If they ask for counts, averages, or comparisons on a spreadsheet, call get_spreadsheet_stats "
                "with the matching file_id and the right column to get EXACT numbers — for totals or comparisons spanning "
                "multiple selected files, make one call PER spreadsheet file_id. Never invent counts. "
                "If the question asks about a document type that none of the selected files contain (e.g. payslips when only an invoice "
                "register is selected), state which files ARE selected and ask the user to select the right ones — never present unrelated "
                "file content as the answer."
            )
            if _is_aggregation_question(question):
                system_prompt += (
                    "\nMANDATORY: This is a counts/comparison question on a spreadsheet. You MUST call "
                    "get_spreadsheet_stats BEFORE answering — once per relevant selected spreadsheet file_id (first without "
                    "column to list columns, then with the matching column). NEVER count from document excerpts — they are samples and will give "
                    "wrong totals."
                )
        elif _is_aggregation_question(question):
            tool_defs = []
            system_prompt += (
                " This is a counts/totals question on non-spreadsheet documents (PDF/DOCX). Do NOT call get_spreadsheet_stats — it only works on xlsx/csv. "
                "Answer by counting directly from the COMPLETE DOCUMENT TEXT provided above. Be exact."
            )
        else:
            tool_defs = tools_for_context(department, agent_scope) if not top_chunks or route["intent"] not in ("document", "general") else []
            if top_chunks and route["intent"] in ("document", "general") and not tool_defs:
                system_prompt += (
                    "\n\nNo tools are available in this mode. Answer only from the document excerpts above. Do not mention or describe using any tool. "
                    "Never reveal passwords, API keys, or credentials found in the documents; redact any secret as [REDACTED]."
                )
    elif sheet_ids:
        from app.services.tools import SPREADSHEET_TOOLS

        tool_defs = SPREADSHEET_TOOLS
        candidates = ", ".join(
            f"{fid}: {registry.get(fid, {}).get('name', fid)}" for fid in sheet_ids
        )
        system_prompt += (
            "\n\nAVAILABLE SPREADSHEETS: " + candidates +
            "\nINSTRUCTIONS: This is a counts/comparison question. You MUST call "
            "get_spreadsheet_stats to answer it — first without a column to list "
            "columns, then with the matching column (e.g. destination/city/status). "
            "Use EXACT numbers from the tool result. NEVER count from document "
            "excerpts; excerpts are samples and will give wrong totals. If no "
            "spreadsheet matches the question's subject, say which files you "
            "checked. Never reveal secrets found in files; redact as [REDACTED]."
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
    drop_excerpts = bool(
        sheet_ids and top_chunks
        and all(c.get("file_id") in set(sheet_ids) for c in top_chunks)
    )
    doc_context = _aggregation_doc_context(
        question, file_ids, registry, source_filter, indexed_file_ids, store, context, top_chunks,
        drop_excerpts=drop_excerpts,
    )
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
            cleaned = _sanitize(tool_text)
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
            append_chat_message(user_key, "user", question, session_id=sid)
            assistant_msg_id = append_chat_message(user_key, "assistant", msg, sources=[], session_id=sid)
            yield f"event: done\ndata: {json.dumps({'response': msg, 'sources': [], 'chunks_used': 0, 'session_id': sid, 'message_id': assistant_msg_id})}\n\n"
            return

        prompt = f"""You are CEAP for Schools, an expert school document analyst AI.

{history_block}DOCUMENT EXCERPTS (use these as your primary source of truth):
{context}

INSTRUCTIONS:
- Answer using ONLY the document excerpts above.
- If the conversation history provides relevant context, use it to give a more coherent answer.
- Be concise and accurate. Cite the source filename when relevant.
- If the answer is not in the documents, say so clearly.
{"- IMPORTANT: The excerpts are a SAMPLE of the document, not the whole file. Never state counts/totals as complete — prefix with 'Based on the available excerpts' and recommend selecting the file for exact numbers." if _is_aggregation_question(question) else ""}
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
                append_chat_message(user_key, "user", question, session_id=sid)
                assistant_msg_id = append_chat_message(user_key, "assistant", "I couldn't generate a response. Please try again.", sources=source_payload, session_id=sid)
                yield f"event: done\ndata: {json.dumps({'response': '', 'sources': source_payload, 'chunks_used': len(top_chunks), 'session_id': sid, 'message_id': assistant_msg_id})}\n\n"
                return

            answer = "".join(full_response)
            answer = _sanitize(answer) if answer else answer
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
            append_chat_message(user_key, "user", question, session_id=sid)
            assistant_msg_id = append_chat_message(user_key, "assistant", fallback["response"], sources=fallback.get("sources") or source_payload, session_id=sid)
            yield f"event: done\ndata: {json.dumps({**fallback, 'session_id': sid, 'message_id': assistant_msg_id})}\n\n"
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
