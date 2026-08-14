import os
import time
import tempfile
import uuid as _uuid
from flask import Blueprint, request, jsonify, send_from_directory, current_app
from sqlalchemy import desc
from app.auth_helpers import login_required
from app.db import SessionLocal
from app.models import ComplianceEvidence, ActivityLog
from app.services.groq_service import generate_answer, GeminiServiceError
from app.services.rag import _user_key, get_registry, register_and_index
from app.services.classifier import classify
from app.services.compliance_classifier import classify_compliance, COMPLIANCE_CATEGORIES, detect_compliance_status
from app.services.file_parser import extract_text, SUPPORTED_EXTS

compliance_bp = Blueprint("compliance", __name__)

COMPLIANCE_STORAGE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "storage",
)


def _ensure_compliance_dir(user_key: str):
    p = os.path.join(COMPLIANCE_STORAGE, "compliance", user_key)
    os.makedirs(p, exist_ok=True)
    return p


def _save_upload(file_obj, user_key: str) -> dict:
    ext = os.path.splitext(file_obj.filename)[1].lower()
    if ext not in SUPPORTED_EXTS:
        return {"error": f"Unsupported type: {ext}"}
    fname = f"{_uuid.uuid4().hex}{ext}"
    dest_dir = _ensure_compliance_dir(user_key)
    dest_path = os.path.join(dest_dir, fname)
    file_obj.save(dest_path)
    return {"file_path": dest_path, "filename": fname, "size": os.path.getsize(dest_path)}


@compliance_bp.route("/api/compliance/evidence", methods=["GET"])
@login_required
def list_evidence():
    framework = request.args.get("framework", "")
    user_key = _user_key()
    db = SessionLocal()
    q = db.query(ComplianceEvidence).filter(
        ComplianceEvidence.user_key == user_key
    )
    if framework:
        q = q.filter(ComplianceEvidence.framework == framework)
    rows = q.order_by(desc(ComplianceEvidence.created_at)).all()
    db.close()
    return jsonify([{
        "id": r.id,
        "title": r.title,
        "framework": r.framework,
        "status": r.status,
        "category": r.category,
        "lastUpdated": r.last_updated,
        "notes": r.notes,
        "file_path": r.file_path,
        "source_name": r.source_name,
        "owner": r.owner,
    } for r in rows])


@compliance_bp.route("/api/compliance/evidence/upload", methods=["POST"])
@login_required
def upload_evidence():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file provided"}), 400
    file = request.files["file"]
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in SUPPORTED_EXTS:
        return jsonify({"success": False, "error": f"Unsupported type: {ext}"}), 400

    user_key = _user_key()
    started = time.monotonic()
    try:
        saved = _save_upload(file, user_key)
        if "error" in saved:
            return jsonify({"success": False, "error": saved["error"]}), 400

        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            with open(saved["file_path"], "rb") as src:
                tmp.write(src.read())
            tmp_path = tmp.name

        text = extract_text(tmp_path, file.filename)
        os.unlink(tmp_path)
        if not text:
            return jsonify({"success": False, "error": "Could not extract text"}), 400

        category = classify_compliance(text, file.filename)
        if not category:
            category = "General"

        status = detect_compliance_status(text)

        department = classify(text, file.filename)
        registry = get_registry()
        if any(e.get("name") == file.filename for e in registry.values()):
            return jsonify({"success": False, "error": f"File '{file.filename}' already exists"}), 409
        entry = register_and_index(
            file.filename, text, saved["size"], "local",
            category_id=None, department=department,
        )

        item = ComplianceEvidence(
            user_key=user_key,
            title=os.path.splitext(file.filename)[0],
            framework="govt",
            status=status,
            category=category or "",
            last_updated=time.strftime("%Y-%m-%d"),
            file_path=saved["file_path"],
            source_name=file.filename,
            owner="",
        )
        db = SessionLocal()
        db.add(item)
        db.commit()
        item_id = item.id
        db.close()

        total_ms = int((time.monotonic() - started) * 1000)
        current_app.logger.info(
            "compliance.upload name=%s evidence_id=%s category=%s total_ms=%s",
            file.filename, item_id, category, total_ms,
        )
        return jsonify({"success": True, "id": item_id, **{
            "id": item_id,
            "title": item.title,
            "framework": item.framework,
            "status": item.status,
            "category": item.category,
            "lastUpdated": item.last_updated,
            "file_path": item.file_path,
            "source_name": item.source_name,
        }, "file_id": entry.get("file_id"), "chunks": entry.get("chunks")}), 201
    except Exception as e:
        current_app.logger.exception("compliance.upload.failed")
        return jsonify({"success": False, "error": str(e)}), 500


@compliance_bp.route("/api/compliance/evidence/<evidence_id>/download", methods=["GET"])
@login_required
def download_evidence(evidence_id):
    user_key = _user_key()
    db = SessionLocal()
    item = db.query(ComplianceEvidence).filter(
        ComplianceEvidence.id == evidence_id, ComplianceEvidence.user_key == user_key,
    ).first()
    db.close()
    if not item or not item.file_path or not os.path.exists(item.file_path):
        return jsonify({"error": "File not found"}), 404
    directory = os.path.dirname(item.file_path)
    filename = os.path.basename(item.file_path)
    return send_from_directory(directory, filename, as_attachment=True, download_name=item.source_name or filename)


@compliance_bp.route("/api/compliance/evidence", methods=["POST"])
@login_required
def create_evidence():
    data = request.json or {}
    user_key = _user_key()
    item = ComplianceEvidence(
        user_key=user_key,
        title=data.get("title", ""),
        framework=data.get("framework", "govt"),
        status=data.get("status", "Missing"),
        category=data.get("category", ""),
        last_updated=data.get("lastUpdated", "—"),
        notes=data.get("notes", ""),
    )
    db = SessionLocal()
    db.add(item)
    db.commit()
    item_id = item.id
    db.close()
    return jsonify({"success": True, "id": item_id}), 201


@compliance_bp.route("/api/compliance/evidence/<evidence_id>", methods=["PUT"])
@login_required
def update_evidence(evidence_id):
    data = request.json or {}
    user_key = _user_key()
    db = SessionLocal()
    item = db.query(ComplianceEvidence).filter(
        ComplianceEvidence.id == evidence_id, ComplianceEvidence.user_key == user_key,
    ).first()
    if not item:
        db.close()
        return jsonify({"error": "Not found"}), 404
    if "status" in data:
        item.status = data["status"]
    if "lastUpdated" in data:
        item.last_updated = data["lastUpdated"]
    if "notes" in data:
        item.notes = data["notes"]
    if "title" in data:
        item.title = data["title"]
    if "category" in data:
        item.category = data["category"]
    db.commit()
    db.close()
    return jsonify({"success": True})


@compliance_bp.route("/api/compliance/evidence/<evidence_id>", methods=["DELETE"])
@login_required
def delete_evidence(evidence_id):
    user_key = _user_key()
    db = SessionLocal()
    item = db.query(ComplianceEvidence).filter(
        ComplianceEvidence.id == evidence_id, ComplianceEvidence.user_key == user_key,
    ).first()
    if not item:
        db.close()
        return jsonify({"error": "Not found"}), 404
    if item.file_path and os.path.exists(item.file_path):
        os.unlink(item.file_path)
    db.delete(item)
    db.commit()
    db.close()
    return jsonify({"success": True})


_PLAN_PROMPT = """You are a compliance officer for a school. Based on the following evidence items, generate a prioritized action plan.

For each item that is not "Available", provide:
1. A clear action to take
2. Priority (High / Medium / Low)
3. Suggested deadline
4. Suggested department/team to handle this

Return the plan as a JSON array of objects with keys: "item", "action", "priority", "deadline", "assignedTo".

Evidence items:
{items}"""


@compliance_bp.route("/api/compliance/plan", methods=["POST"])
@login_required
def generate_plan():
    data = request.json or {}
    items = data.get("items", [])
    if not items:
        return jsonify({"error": "No evidence items provided"}), 400

    summary = "\n".join(
        f"- {i.get('title', '?')} [{i.get('status', '?')}] — {i.get('category', '')}"
        for i in items
    )
    prompt = _PLAN_PROMPT.format(items=summary)

    try:
        raw = generate_answer(prompt)
        import json as _json
        start = raw.find("[")
        end = raw.rfind("]")
        if start != -1 and end != -1:
            raw = raw[start:end + 1]
        plan = _json.loads(raw)
        return jsonify({"plan": plan})
    except (GeminiServiceError, ValueError, _json.JSONDecodeError):
        fallback = []
        for i in items:
            if i.get("status") != "Available":
                fallback.append({
                    "item": i.get("title", ""),
                    "action": f"Review and update {i.get('title', '')}",
                    "priority": "High" if i.get("status") == "Missing" else "Medium",
                    "deadline": "30 days",
                    "assignedTo": i.get("category", "Compliance Team"),
                })
        return jsonify({"plan": fallback})


PACK_STORAGE = {}


@compliance_bp.route("/api/compliance/pack/generate", methods=["POST"])
@login_required
def generate_pack():
    user_key = _user_key()
    data = request.json or {}
    framework = data.get("framework", "govt")
    item_ids = data.get("items", [])

    db = SessionLocal()
    items = db.query(ComplianceEvidence).filter(
        ComplianceEvidence.id.in_(item_ids),
        ComplianceEvidence.user_key == user_key,
    ).all() if item_ids else []
    db.close()

    count = len(items)
    pack_id = _uuid.uuid4().hex[:12]
    PACK_STORAGE[pack_id] = {"user_key": user_key, "framework": framework, "items": [i.id for i in items]}

    db = SessionLocal()
    db.add(ActivityLog(
        user_email=user_key,
        action="generate_pack",
        resource_type="compliance_pack",
        resource_id=pack_id,
        details=f"Generated evidence pack for framework '{framework}' with {count} items",
    ))
    db.commit()
    db.close()

    return jsonify({"success": True, "pack_id": pack_id, "count": count, "message": f"Evidence pack ready — {count} files"})


@compliance_bp.route("/api/compliance/pack/download", methods=["GET"])
@login_required
def download_pack():
    user_key = _user_key()
    framework = request.args.get("framework", "govt")

    db = SessionLocal()
    db.add(ActivityLog(
        user_email=user_key,
        action="download_pack",
        resource_type="compliance_pack",
        details=f"Downloaded evidence pack for framework '{framework}'",
    ))
    db.commit()
    db.close()

    return jsonify({"success": True, "message": "Download simulated"})