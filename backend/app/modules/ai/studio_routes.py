from flask import Blueprint, request, jsonify
from sqlalchemy import desc
from app.auth_helpers import login_required
from app.db import SessionLocal
from app.models import DocumentTemplate, AIDraft
from app.services.rag import get_store, get_registry, _user_key
from .routes import _build_source_payload
from app.services.gemini import generate_answer, GeminiServiceError
from app.config import RAGConfig

studio_bp = Blueprint("studio", __name__)

DEFAULT_TEMPLATES = [
    {"doc_type": "Circular", "name": "Parent Circular – General", "description": "Standard parent communication"},
    {"doc_type": "Circular", "name": "Event Announcement", "description": "Sports day, annual day, workshops"},
    {"doc_type": "Circular", "name": "Holiday Notice", "description": "Academic calendar holidays"},
    {"doc_type": "Circular", "name": "Fee Reminder", "description": "Fee payment reminders"},
    {"doc_type": "Letter", "name": "Staff Offer Letter", "description": "Appointment communication"},
    {"doc_type": "Letter", "name": "Parent Concern Response", "description": "Formal parent reply"},
    {"doc_type": "Letter", "name": "Transfer Certificate", "description": "Student TC letter"},
    {"doc_type": "Report", "name": "Inspection Readiness Report", "description": "Compliance summary"},
    {"doc_type": "Report", "name": "Academic Performance Report", "description": "Term-end analytics"},
    {"doc_type": "Report", "name": "Incident Investigation Report", "description": "Safety incident write-up"},
    {"doc_type": "Notice", "name": "General Notice", "description": "School-wide announcements"},
    {"doc_type": "Notice", "name": "Meeting Notice", "description": "Staff or parent meeting notice"},
    {"doc_type": "Certificate", "name": "Bonafide Certificate", "description": "Student bonafide certificate"},
    {"doc_type": "Certificate", "name": "Experience Certificate", "description": "Staff experience letter"},
    {"doc_type": "Certificate", "name": "Transfer Certificate", "description": "Student leaving certificate"},
    {"doc_type": "Meeting Minutes", "name": "Staff Meeting Minutes", "description": "Minutes of staff meetings"},
    {"doc_type": "Meeting Minutes", "name": "PTA Meeting Minutes", "description": "Parent-teacher meeting record"},
    {"doc_type": "Policy", "name": "School Policy Document", "description": "General policy documentation"},
    {"doc_type": "Email", "name": "Official Email", "description": "Professional email communication"},
    {"doc_type": "Offer Letter", "name": "Staff Offer Letter", "description": "Formal employment offer"},
    {"doc_type": "Appointment Letter", "name": "Staff Appointment Letter", "description": "Formal appointment letter"},
]


def seed_templates_if_empty():
    db = SessionLocal()
    existing = db.query(DocumentTemplate).first()
    if existing:
        db.close()
        return
    for t in DEFAULT_TEMPLATES:
        db.add(DocumentTemplate(
            doc_type=t["doc_type"],
            name=t["name"],
            description=t["description"],
        ))
    db.commit()
    db.close()


def _build_prompt(doc_type, template_name, topic, department, audience, academic_year, context, agent_scope=None):
    agent_prefix = ""
    if agent_scope:
        agent_prefix = f"You are acting as: {agent_scope}\n\n"
    prompt = f"""{agent_prefix}You are CEAP for Schools, an AI document generation assistant. Generate a professional {doc_type.lower()} for a school.

DOCUMENT TYPE: {doc_type}
TEMPLATE: {template_name}
TOPIC: {topic}
DEPARTMENT: {department}
AUDIENCE: {audience}
ACADEMIC YEAR: {academic_year}

"""

    if context:
        prompt += f"""Use the following school documents as reference:

{context}

"""

    prompt += f"""Follow standard school document conventions for a {doc_type.lower()}. Include appropriate headers, reference numbers, date, subject line, salutation, body, and closing.

Generate the complete document in plain text suitable for a formal school document. Do not use markdown formatting."""
    return prompt


@studio_bp.route("/api/ai/templates", methods=["GET"])
@login_required
def get_templates():
    seed_templates_if_empty()
    db = SessionLocal()
    rows = db.query(DocumentTemplate).filter(DocumentTemplate.is_active == 1)\
        .order_by(DocumentTemplate.doc_type, desc(DocumentTemplate.created_at)).all()
    grouped = {}
    for r in rows:
        grouped.setdefault(r.doc_type, []).append({
            "id": r.id,
            "name": r.name,
            "description": r.description,
        })
    db.close()
    return jsonify(grouped)


@studio_bp.route("/api/ai/generate", methods=["POST"])
@login_required
def generate_draft():
    data = request.json or {}
    doc_type = data.get("doc_type", "Circular")
    template_id = data.get("template_id", "")
    topic = data.get("topic", "")
    department = data.get("department", "")
    audience = data.get("audience", "Parents")
    academic_year = data.get("academic_year", "2025-26")
    agent_scope = (data.get("agent_scope") or "").strip() or None

    db = SessionLocal()
    tpl = db.query(DocumentTemplate).filter(
        DocumentTemplate.id == template_id, DocumentTemplate.is_active == 1
    ).first()
    template_name = tpl.name if tpl else doc_type
    db.close()

    context = ""
    top_chunks = []
    try:
        store = get_store()
        if store.indexed_file_ids():
            top_chunks = store.search(topic, top_k=RAGConfig.TOP_K)
            if top_chunks:
                context = "\n\n".join(
                    f"--- Source: {c['source']} (chunk {c['chunk_index']}) ---\n{c['text']}"
                    for c in top_chunks
                )
    except Exception:
        pass

    prompt = _build_prompt(doc_type, template_name, topic, department, audience, academic_year, context, agent_scope)

    try:
        content = generate_answer(prompt)
        if not content:
            return jsonify({"error": "AI generation returned empty result"}), 500
    except GeminiServiceError as exc:
        return jsonify({"error": str(exc)}), 503

    title = f"{doc_type} – {topic or template_name}"
    user_key = _user_key()

    draft = AIDraft(
        user_key=user_key,
        doc_type=doc_type,
        template_id=template_id,
        template_name=template_name,
        title=title,
        content=content,
        department=department,
        academic_year=academic_year,
        audience=audience,
        topic=topic,
        status="draft",
    )
    db = SessionLocal()
    db.add(draft)
    db.commit()
    draft_id = draft.id
    db.close()

    registry = get_registry() if top_chunks else {}
    source_payload = _build_source_payload(top_chunks, registry) if top_chunks else []

    return jsonify({
        "id": draft_id,
        "title": title,
        "content": content,
        "sources": source_payload,
    })


@studio_bp.route("/api/ai/drafts", methods=["GET"])
@login_required
def list_drafts():
    user_key = _user_key()
    db = SessionLocal()
    rows = db.query(AIDraft).filter(
        AIDraft.user_key == user_key
    ).order_by(desc(AIDraft.created_at)).all()
    db.close()
    return jsonify([{
        "id": r.id,
        "title": r.title,
        "doc_type": r.doc_type,
        "template_name": r.template_name,
        "department": r.department,
        "status": r.status,
        "topic": r.topic,
        "created_at": r.created_at,
    } for r in rows])
