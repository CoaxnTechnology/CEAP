import hashlib

from flask import Blueprint, jsonify, request

from app.auth_helpers import login_required
from app.db import SessionLocal
from app.models import User, Workflow, WorkflowInstance

workflow_bp = Blueprint("workflows", __name__)

DEFAULT_TEMPLATES = [
    {"key": "admission", "name": "Admission Journey", "stages": ["Inquiry", "Application", "Assessment", "Interview", "Offer", "Enrollment"], "color": "#7C3AED"},
    {"key": "leave", "name": "Staff Leave", "stages": ["Request", "Manager", "HR", "Calendar", "Done"], "color": "#0369A1"},
    {"key": "purchase", "name": "Purchase Request", "stages": ["Request", "Budget Check", "Principal", "PO", "Receive"], "color": "#B45309"},
    {"key": "recruitment", "name": "Recruitment", "stages": ["Requisition", "Posting", "Screen", "Interview", "Offer", "Onboard"], "color": "#0F766E"},
    {"key": "complaint", "name": "Parent Complaint", "stages": ["Intake", "Triage", "Investigate", "Resolve", "Close"], "color": "#B91C1C"},
    {"key": "fee-waiver", "name": "Fee Waiver", "stages": ["Request", "Finance Review", "Principal", "Apply", "Notify"], "color": "#4F46E5"},
    {"key": "transport", "name": "Transport Change", "stages": ["Request", "Capacity", "Approve", "Roster", "Notify"], "color": "#334e68"},
    {"key": "hostel", "name": "Hostel Allocation", "stages": ["Apply", "Eligibility", "Allocate", "Fee", "Check-in"], "color": "#059669"},
]


def _db_key(db):
    from flask import session
    email = (session.get("user") or "").strip().lower()
    return hashlib.sha256(email.encode("utf-8")).hexdigest()[:32] if email else hashlib.sha256(b"admin@ceap.school").hexdigest()[:32]


def _serialize(w):
    return {
        "id": w.id,
        "key": w.key,
        "name": w.name,
        "color": w.color,
        "stages": w.stages_json or [],
        "status": w.status,
        "updated_at": w.updated_at,
    }


def seed_workflows_if_empty():
    db = SessionLocal()
    try:
        user_key = _db_key(db)
        if db.query(Workflow).filter(Workflow.user_key == user_key).count() == 0:
            for t in DEFAULT_TEMPLATES:
                db.add(Workflow(
                    user_key=user_key,
                    key=t["key"],
                    name=t["name"],
                    color=t["color"],
                    stages_json=t["stages"],
                    status="draft",
                ))
            db.commit()
    finally:
        db.close()


@workflow_bp.route("/api/workflows", methods=["GET"])
@login_required
def list_workflows():
    db = SessionLocal()
    try:
        user_key = _db_key(db)
        rows = (
            db.query(Workflow)
            .filter(Workflow.user_key == user_key)
            .order_by(Workflow.created_at)
            .all()
        )
        return jsonify({"workflows": [_serialize(w) for w in rows]})
    finally:
        db.close()


@workflow_bp.route("/api/workflows", methods=["POST"])
@login_required
def create_workflow():
    data = request.json or {}
    name = (data.get("name") or "Untitled Workflow").strip()[:255]
    stages = data.get("stages") or ["New Stage"]
    db = SessionLocal()
    try:
        w = Workflow(
            user_key=_db_key(db),
            key="custom",
            name=name,
            color=(data.get("color") or "#1E3A5F")[:20],
            stages_json=[str(s)[:80] for s in stages][:50],
            status="draft",
        )
        db.add(w)
        db.commit()
        db.refresh(w)
        return jsonify({"workflow": _serialize(w)}), 201
    finally:
        db.close()


@workflow_bp.route("/api/workflows/<workflow_id>", methods=["PATCH"])
@login_required
def update_workflow(workflow_id):
    data = request.json or {}
    db = SessionLocal()
    try:
        w = db.query(Workflow).filter(
            Workflow.id == workflow_id, Workflow.user_key == _db_key(db)
        ).first()
        if not w:
            return jsonify({"error": "Workflow not found"}), 404
        if "name" in data:
            w.name = str(data["name"])[:255]
        if "color" in data:
            w.color = str(data["color"])[:20]
        if "stages" in data:
            w.stages_json = [str(s)[:80] for s in data["stages"]][:50]
        db.commit()
        return jsonify({"success": True, "workflow": _serialize(w)})
    finally:
        db.close()


@workflow_bp.route("/api/workflows/<workflow_id>/publish", methods=["POST"])
@login_required
def publish_workflow(workflow_id):
    db = SessionLocal()
    try:
        w = db.query(Workflow).filter(
            Workflow.id == workflow_id, Workflow.user_key == _db_key(db)
        ).first()
        if not w:
            return jsonify({"error": "Workflow not found"}), 404
        w.status = "published"
        db.commit()
        return jsonify({"success": True, "workflow": _serialize(w)})
    finally:
        db.close()


def _serialize_instance(inst, workflow):
    stages = workflow.stages_json or []
    return {
        "id": inst.id,
        "workflow_id": inst.workflow_id,
        "workflow_name": workflow.name,
        "title": inst.title,
        "current_stage": inst.current_stage,
        "current_stage_name": stages[inst.current_stage] if inst.current_stage < len(stages) else None,
        "total_stages": len(stages),
        "status": inst.status,
        "created_at": inst.created_at,
    }


@workflow_bp.route("/api/workflows/<workflow_id>/instances", methods=["GET"])
@login_required
def list_instances(workflow_id):
    db = SessionLocal()
    try:
        w = db.query(Workflow).filter(
            Workflow.id == workflow_id, Workflow.user_key == _db_key(db)
        ).first()
        if not w:
            return jsonify({"error": "Workflow not found"}), 404
        rows = (
            db.query(WorkflowInstance)
            .filter(WorkflowInstance.workflow_id == workflow_id)
            .order_by(WorkflowInstance.created_at.desc())
            .all()
        )
        return jsonify({"instances": [_serialize_instance(i, w) for i in rows]})
    finally:
        db.close()


@workflow_bp.route("/api/workflows/<workflow_id>/start", methods=["POST"])
@login_required
def start_workflow(workflow_id):
    data = request.json or {}
    title = (data.get("title") or "New request").strip()[:255]
    db = SessionLocal()
    try:
        w = db.query(Workflow).filter(
            Workflow.id == workflow_id, Workflow.user_key == _db_key(db)
        ).first()
        if not w:
            return jsonify({"error": "Workflow not found"}), 404
        if w.status != "published":
            return jsonify({"error": "Workflow must be published first"}), 400
        inst = WorkflowInstance(workflow_id=workflow_id, title=title, current_stage=0, status="open")
        db.add(inst)
        db.commit()
        db.refresh(inst)
        return jsonify({"success": True, "instance": _serialize_instance(inst, w)}), 201
    finally:
        db.close()


@workflow_bp.route("/api/workflows/instances/<instance_id>/advance", methods=["POST"])
@login_required
def advance_instance(instance_id):
    db = SessionLocal()
    try:
        inst = db.query(WorkflowInstance).filter(WorkflowInstance.id == instance_id).first()
        if not inst:
            return jsonify({"error": "Instance not found"}), 404
        w = db.query(Workflow).filter(Workflow.id == inst.workflow_id).first()
        stages = w.stages_json or [] if w else []
        if inst.status != "open":
            return jsonify({"error": "Instance is not open"}), 400
        if inst.current_stage + 1 >= len(stages):
            inst.status = "done"
        else:
            inst.current_stage += 1
        db.commit()
        db.refresh(inst)
        return jsonify({"success": True, "instance": _serialize_instance(inst, w)})
    finally:
        db.close()
