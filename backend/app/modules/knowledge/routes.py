import os
import time
from datetime import datetime
from flask import Blueprint, request, jsonify
from sqlalchemy import desc
from app.auth_helpers import login_required
from app.db import SessionLocal
from app.models import KnowledgeCard, Document, ActivityLog, RepositoryDocument, Department, Student
from app.services.rag import _user_key

knowledge_bp = Blueprint("knowledge", __name__)


@knowledge_bp.route("/api/knowledge/cards", methods=["GET"])
@login_required
def list_cards():
    q = request.args.get("q", "")
    card_type = request.args.get("type", "")
    user_key = _user_key()
    db = SessionLocal()

    doc_query = db.query(Document).filter(Document.user_key == user_key)
    if q:
        like = f"%{q}%"
        doc_query = doc_query.filter(Document.name.ilike(like))
    if card_type and card_type not in ("All", "Document"):
        doc_query = doc_query.filter(False)

    docs = doc_query.order_by(desc(Document.uploaded_at)).all()

    doc_cards = []
    for d in docs:
        ts = d.uploaded_at
        updated = datetime.fromtimestamp(ts).strftime("%Y-%m-%d") if ts else ""
        title = os.path.splitext(d.name)[0] if d.name else "Untitled"
        stale = bool(ts) and (time.time() - ts) > 365 * 86400
        doc_cards.append({
            "id": f"doc_{d.file_id}",
            "title": title,
            "type": "Document",
            "dept": d.department or "",
            "status": "Outdated" if stale else "Current",
            "summary": d.name or "",
            "relations": d.chunks or 0,
            "updated": updated,
            "source": "document",
        })

    card_query = db.query(KnowledgeCard).filter(KnowledgeCard.user_key == user_key)
    if q:
        like = f"%{q}%"
        card_query = card_query.filter(
            (KnowledgeCard.title.ilike(like)) | (KnowledgeCard.summary.ilike(like))
        )
    if card_type and card_type != "All":
        card_query = card_query.filter(KnowledgeCard.card_type == card_type)

    cards = card_query.order_by(desc(KnowledgeCard.updated_at)).all()
    card_results = [{
        "id": r.id,
        "title": r.title,
        "type": r.card_type,
        "dept": r.dept,
        "status": r.status,
        "summary": r.summary,
        "relations": r.relations,
        "updated": r.updated_at,
        "source": "manual",
    } for r in cards]

    db.close()
    combined = doc_cards + card_results
    combined.sort(key=lambda x: x.get("updated", ""), reverse=True)
    return jsonify(combined)


@knowledge_bp.route("/api/knowledge/cards", methods=["POST"])
@login_required
def create_card():
    data = request.json or {}
    user_key = _user_key()
    card = KnowledgeCard(
        user_key=user_key,
        title=data.get("title", ""),
        card_type=data.get("type", "Policy"),
        dept=data.get("dept", ""),
        status=data.get("status", "Current"),
        summary=data.get("summary", ""),
        relations=data.get("relations", 0),
        updated_at=data.get("updated", ""),
    )
    db = SessionLocal()
    db.add(card)
    db.commit()
    card_id = card.id
    db.close()
    return jsonify({"success": True, "id": card_id}), 201


@knowledge_bp.route("/api/knowledge/cards/<card_id>", methods=["PUT"])
@login_required
def update_card(card_id):
    data = request.json or {}
    user_key = _user_key()
    db = SessionLocal()
    card = db.query(KnowledgeCard).filter(
        KnowledgeCard.id == card_id, KnowledgeCard.user_key == user_key,
    ).first()
    if not card:
        db.close()
        return jsonify({"error": "Not found"}), 404
    for field in ("title", "card_type", "dept", "status", "summary", "relations", "updated_at"):
        key = field if field != "card_type" else "type"
        if key == "type":
            key = "type"
        if key in data:
            setattr(card, "card_type" if key == "type" else key, data[key])
    if "type" in data:
        card.card_type = data["type"]
    if "title" in data:
        card.title = data["title"]
    if "dept" in data:
        card.dept = data["dept"]
    if "status" in data:
        card.status = data["status"]
    if "summary" in data:
        card.summary = data["summary"]
    if "relations" in data:
        card.relations = data["relations"]
    if "updated" in data:
        card.updated_at = data["updated"]
    db.commit()
    db.close()
    return jsonify({"success": True})


@knowledge_bp.route("/api/knowledge/cards/<card_id>", methods=["DELETE"])
@login_required
def delete_card(card_id):
    user_key = _user_key()
    db = SessionLocal()
    card = db.query(KnowledgeCard).filter(
        KnowledgeCard.id == card_id, KnowledgeCard.user_key == user_key,
    ).first()
    if not card:
        db.close()
        return jsonify({"error": "Not found"}), 404
    db.delete(card)
    db.commit()
    db.close()
    return jsonify({"success": True})


@knowledge_bp.route("/api/knowledge/types", methods=["GET"])
@login_required
def list_types():
    user_key = _user_key()
    db = SessionLocal()
    types = (
        db.query(KnowledgeCard.card_type)
        .filter(KnowledgeCard.user_key == user_key)
        .distinct()
        .order_by(KnowledgeCard.card_type)
        .all()
    )
    db.close()
    result = sorted(set(t[0] for t in types))
    result.insert(0, "Document")
    return jsonify({"types": result})


KIND_MAP = {
    "login": "Login", "logout": "Logout", "upload": "Document", "delete": "Document",
    "download": "Document", "generate_pack": "Document", "download_pack": "Document",
    "approve": "Approval", "chat": "Discussion", "search": "Search",
}

KIND_COLORS = {
    "Decision": "bg-violet-500", "Meeting": "bg-navy-600", "Approval": "bg-emerald-500",
    "Policy": "bg-amber-500", "Discussion": "bg-sky-500", "Document": "bg-slate-500",
    "Login": "bg-slate-400", "Search": "bg-slate-400", "Logout": "bg-slate-400",
}


@knowledge_bp.route("/api/knowledge/memory", methods=["GET"])
@login_required
def list_memory():
    user_key = _user_key()
    db = SessionLocal()
    try:
        logs = db.query(ActivityLog).filter(
            ActivityLog.user_email == user_key,
        ).order_by(desc(ActivityLog.created_at)).limit(50).all()

        memory = []
        for log in logs:
            kind = KIND_MAP.get(log.action, "Document")
            when = datetime.fromtimestamp(log.created_at).strftime("%Y-%m-%d %H:%M") if log.created_at else ""
            title = log.details or log.resource_name or log.action
            if len(title) > 80:
                title = title[:80] + "…"
            memory.append({
                "id": log.id,
                "when": when,
                "kind": kind,
                "title": title,
                "actor": log.user_email,
                "tags": [log.resource_type] if log.resource_type else [],
                "color": KIND_COLORS.get(kind, "bg-slate-500"),
            })

        return jsonify(memory)
    finally:
        db.close()


@knowledge_bp.route("/api/search", methods=["GET"])
@login_required
def search_all():
    q = request.args.get("q", "").strip()
    user_key = _user_key()
    db = SessionLocal()
    try:
        results = []

        if q:
            like = f"%{q}%"
            repo_docs = db.query(RepositoryDocument).filter(
                RepositoryDocument.user_key == user_key,
                RepositoryDocument.status == "active",
                RepositoryDocument.name.ilike(like),
            ).order_by(desc(RepositoryDocument.updated_at)).limit(20).all()

            for d in repo_docs:
                dept_name = ""
                if d.department_id:
                    dept = db.query(Department).filter(Department.id == d.department_id).first()
                    dept_name = dept.name if dept else ""
                results.append({
                    "id": d.id,
                    "title": d.name,
                    "snippet": d.description or "",
                    "status": "Current" if d.status == "active" else d.status,
                    "department": dept_name,
                    "type": "Document",
                    "year": datetime.fromtimestamp(d.created_at).strftime("%Y") if d.created_at else "",
                    "citation": "",
                    "lastUpdated": datetime.fromtimestamp(d.updated_at).strftime("%Y-%m-%d") if d.updated_at else "",
                    "owner": d.owner_email,
                    "source": "repository",
                })
        else:
            repo_docs = db.query(RepositoryDocument).filter(
                RepositoryDocument.user_key == user_key,
                RepositoryDocument.status == "active",
            ).order_by(desc(RepositoryDocument.updated_at)).limit(20).all()

            for d in repo_docs:
                dept_name = ""
                if d.department_id:
                    dept = db.query(Department).filter(Department.id == d.department_id).first()
                    dept_name = dept.name if dept else ""
                results.append({
                    "id": d.id,
                    "title": d.name,
                    "snippet": d.description or "",
                    "status": "Current" if d.status == "active" else d.status,
                    "department": dept_name,
                    "type": "Document",
                    "year": datetime.fromtimestamp(d.created_at).strftime("%Y") if d.created_at else "",
                    "citation": "",
                    "lastUpdated": datetime.fromtimestamp(d.updated_at).strftime("%Y-%m-%d") if d.updated_at else "",
                    "owner": d.owner_email,
                    "source": "repository",
                })

        if q:
            like = f"%{q}%"
            students = db.query(Student).filter(
                Student.user_key == user_key,
                Student.name.ilike(like),
            ).order_by(Student.class_name, Student.name).limit(10).all()
            for st in students:
                results.append({
                    "id": st.id,
                    "title": st.name,
                    "snippet": f"Grade {st.class_name} · {st.house or ''} house · Attendance {st.attendance}% · GPA {st.gpa}",
                    "status": "Missing" if st.risk_level == "High" else "Expiring" if st.risk_level == "Medium" else "Current",
                    "department": st.class_name,
                    "type": "Student",
                    "year": "",
                    "citation": "",
                    "lastUpdated": "",
                    "owner": st.parent_name,
                    "source": "student",
                })

            cards = db.query(KnowledgeCard).filter(
                KnowledgeCard.user_key == user_key,
                KnowledgeCard.title.ilike(like),
            ).order_by(KnowledgeCard.title).limit(10).all()
            for c in cards:
                results.append({
                    "id": c.id,
                    "title": c.title,
                    "snippet": c.summary or "",
                    "status": c.status or "Current",
                    "department": c.dept or "",
                    "type": c.card_type,
                    "year": "",
                    "citation": "",
                    "lastUpdated": c.updated_at or "",
                    "owner": "",
                    "source": "knowledge",
                })

        return jsonify({"results": results, "total": len(results)})
    finally:
        db.close()
