import hashlib
import time

from flask import Blueprint, jsonify, request, session

from app.auth_helpers import login_required
from app.db import SessionLocal
from app.models import ApprovalRequest, Ticket

ops_bp = Blueprint("operations", __name__)


def _cur_key():
    return hashlib.sha256((session.get("user") or "admin@ceap.school").encode("utf-8")).hexdigest()[:32]


def _serialize_ticket(t):
    return {
        "id": t.id,
        "title": t.title,
        "description": t.description,
        "category": t.category,
        "priority": t.priority,
        "status": t.status,
        "created_by": t.created_by,
        "assignee": t.assignee,
        "due": time.strftime("%Y-%m-%d", time.localtime(t.created_at)),
        "workspace": t.category.title(),
        "created_at": t.created_at,
        "updated_at": t.updated_at,
    }


def _serialize_approval(a):
    meta = a.metadata_json or {}
    label = meta.get("student", a.workflow_type.replace("_", " ").title())
    amount = ""
    if "amount" in meta:
        amount = f"₹{float(meta['amount']):,.0f}"
    return {
        "id": a.id,
        "title": label,
        "type": a.workflow_type.replace("_", " ").title(),
        "requester": a.requester,
        "amount": amount or "—",
        "status": "Approved" if a.status == "approved" else "Rejected" if a.status == "rejected" else "Pending",
        "sla": "Done" if a.status != "pending" else f"{time.strftime('%Hh', time.localtime(a.created_at))} ago",
        "created_at": a.created_at,
    }


@ops_bp.route("/api/tasks", methods=["GET"])
@login_required
def list_tasks():
    db = SessionLocal()
    try:
        rows = db.query(Ticket).filter(Ticket.user_key == _cur_key()).order_by(Ticket.created_at.desc()).all()
        return jsonify({"tasks": [_serialize_ticket(t) for t in rows]})
    finally:
        db.close()


@ops_bp.route("/api/tasks", methods=["POST"])
@login_required
def create_task():
    data = request.json or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400
    db = SessionLocal()
    try:
        t = Ticket(
            user_key=_cur_key(),
            title=title,
            description=(data.get("description") or "").strip(),
            category=(data.get("workspace") or data.get("category") or "general").strip(),
            priority=(data.get("priority") or "medium").strip(),
            status="open",
            created_by=data.get("created_by") or "admin@ceap.school",
            assignee=(data.get("assignee") or "").strip(),
        )
        db.add(t)
        db.commit()
        db.refresh(t)
        return jsonify({"success": True, "task": _serialize_ticket(t)}), 201
    finally:
        db.close()


@ops_bp.route("/api/tasks/<task_id>", methods=["PATCH"])
@login_required
def update_task(task_id):
    db = SessionLocal()
    try:
        t = db.query(Ticket).filter(Ticket.id == task_id).first()
        if not t:
            return jsonify({"error": "Task not found"}), 404
        data = request.json or {}
        if data.get("status") in ("open", "done", "in_progress", "review"):
            t.status = data["status"]
        if data.get("priority"):
            t.priority = data["priority"]
        if data.get("title"):
            t.title = data["title"]
        db.commit()
        db.refresh(t)
        return jsonify({"success": True, "task": _serialize_ticket(t)})
    finally:
        db.close()


@ops_bp.route("/api/approvals", methods=["GET"])
@login_required
def list_approvals():
    db = SessionLocal()
    try:
        rows = db.query(ApprovalRequest).filter(ApprovalRequest.user_key == _cur_key()).order_by(ApprovalRequest.created_at.desc()).all()
        return jsonify({"approvals": [_serialize_approval(a) for a in rows]})
    finally:
        db.close()


@ops_bp.route("/api/approvals/<request_id>", methods=["PATCH"])
@login_required
def decide_approval(request_id):
    data = request.json or {}
    decision = data.get("status")
    if decision not in ("approved", "rejected"):
        return jsonify({"error": "status must be approved or rejected"}), 400
    db = SessionLocal()
    try:
        req = db.query(ApprovalRequest).filter(ApprovalRequest.id == request_id).first()
        if not req:
            return jsonify({"error": "Request not found"}), 404
        req.status = decision
        req.updated_at = time.time()
        db.commit()
        db.refresh(req)
        return jsonify({"success": True, "id": req.id, "status": decision})
    finally:
        db.close()


def seed_tasks_if_empty():
    db = SessionLocal()
    try:
        if db.query(Ticket).count() == 0:
            seeds = [
                {"title": "Renew Fire Safety Certificate", "category": "Compliance", "priority": "urgent", "status": "open", "created_by": "admin@ceap.school", "assignee": "Vikram Singh"},
                {"title": "Parent conference – Aarav Mehta", "category": "Students", "priority": "high", "status": "open", "created_by": "admin@ceap.school", "assignee": "Meera Nair"},
                {"title": "Review Annual Day circular draft", "category": "Studio", "priority": "high", "status": "review", "created_by": "admin@ceap.school", "assignee": "Priya Sharma"},
                {"title": "Close Q1 fee follow-ups Class 10", "category": "Finance", "priority": "medium", "status": "open", "created_by": "admin@ceap.school", "assignee": "Sneha Kapoor"},
                {"title": "Interview slot – Myra Singh", "category": "Admissions", "priority": "medium", "status": "open", "created_by": "admin@ceap.school", "assignee": "Rahul Mehta"},
                {"title": "Approve leave – Pooja Iyer", "category": "HR", "priority": "low", "status": "open", "created_by": "admin@ceap.school", "assignee": "Rahul Mehta"},
            ]
            for row in seeds:
                db.add(Ticket(**row))
            db.commit()
    finally:
        db.close()