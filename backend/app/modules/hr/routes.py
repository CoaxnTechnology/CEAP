import hashlib
import json
import time
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request, session
from sqlalchemy import desc

from app.auth_helpers import login_required
from app.db import SessionLocal
from app.models import (
    ActivityLog,
    ApprovalRequest,
    Department,
    HRPolicy,
    JobRequisition,
    LeaveRequest,
    Notification,
    User,
)
from app.services.groq_service import (
    GeminiServiceError,
    generate_answer,
    generate_recommendations,
    _cached_generate_recommendations,
)
from app.services.rag import _user_key
from app.services.workflow_engine import process_approval

hr_bp = Blueprint("hr", __name__)


def _school_emails(db):
    email = (session.get("user") or "").strip().lower()
    me = db.query(User).filter(User.email == email).first()
    if not me or not me.school_id:
        return [email]
    return [
        u.email
        for u in db.query(User).filter(User.school_id == me.school_id).all()
    ]

TRAINING_DUE = 6
EXPIRING_CONTRACTS = 2

DEFAULT_RULES = {
    "leave_types": {
        "annual": {"balance_key": "annual", "max_days": 20, "half_day_allowed": False},
        "earned": {"balance_key": "annual", "max_days": 20, "half_day_allowed": False},
        "sick": {"balance_key": "sick", "max_days": 12, "half_day_allowed": False},
        "personal": {"balance_key": "personal", "max_days": 5, "half_day_allowed": False},
        "casual": {"balance_key": "personal", "max_days": 5, "half_day_allowed": False},
        "maternity": {"balance_key": None, "max_days": 180, "half_day_allowed": False},
        "paternity": {"balance_key": None, "max_days": 15, "half_day_allowed": False},
    },
    "approver_routing": "department_head",
    "exclude_weekends": False,
}


def _get_rules(db, user_key):
    policy = (
        db.query(HRPolicy)
        .filter(HRPolicy.user_key == user_key, HRPolicy.category == "leave", HRPolicy.active == 1)
        .first()
    )
    if policy and policy.rules_json:
        return policy.rules_json
    return DEFAULT_RULES


def _leave_type_rules(rules, leave_type):
    return rules.get("leave_types", {}).get(leave_type.lower())


def _today_str():
    return time.strftime("%Y-%m-%d")


def _date_range(start_str, end_str):
    fmt = "%Y-%m-%d"
    start = datetime.strptime(start_str, fmt)
    end = datetime.strptime(end_str or start_str, fmt)
    return start, end


def _working_days(start, end, exclude_weekends):
    days = 0
    current = start
    while current <= end:
        if not (exclude_weekends and current.weekday() >= 5):
            days += 1
        current += timedelta(days=1)
    return max(days, 0)


def _leave_days(leave, rules):
    try:
        start, end = _date_range(leave.start_date, leave.end_date)
    except ValueError:
        return 0.5 if leave.half_day else 1
    if leave.half_day:
        return 0.5
    return _working_days(start, end, bool(rules.get("exclude_weekends")))


def _deduct_balance(db, user, leave, rules):
    lt = _leave_type_rules(rules, leave.leave_type)
    key = lt.get("balance_key") if lt else None
    if not key:
        return
    try:
        balance = json.loads(user.leave_balance_json or "{}")
    except (ValueError, TypeError):
        balance = {}
    if key not in balance:
        return
    balance[key] = max(0, balance[key] - _leave_days(leave, rules))
    user.leave_balance_json = json.dumps(balance)


def _approver_for(db, user, rules):
    routing = rules.get("approver_routing", "department_head")
    if routing in ("department_head", "manager") and user and user.department:
        dept = (
            db.query(Department)
            .filter(Department.name == user.department, Department.head_email != "")
            .first()
        )
        if dept and routing == "department_head" and dept.head_email != user.email:
            return dept.head_email
            # ponytail: dept head == self (e.g. HOD) -> fall through to manager/admin, no self-approval
    if user and user.manager_email:
        return user.manager_email
    return "admin@ceap.school"


def _leave_status(leave, name_by_email):
    return {
        "id": leave.id,
        "name": name_by_email.get(leave.user_email, leave.user_email),
        "type": leave.leave_type,
        "dates": f"{leave.start_date}–{leave.end_date}"
        if leave.end_date != leave.start_date
        else leave.start_date,
        "halfDay": bool(leave.half_day),
        "status": leave.status,
    }


@hr_bp.route("/api/hr/overview", methods=["GET"])
@login_required
def overview():
    user_key = _user_key()
    db = SessionLocal()
    try:
        users = (
            db.query(User)
            .filter(User.status == "active", User.email.in_(_school_emails(db)))
            .order_by(User.full_name)
            .all()
        )
        headcount = len(users)
        name_by_email = {u.email: u.full_name or u.email for u in users}

        open_reqs = (
            db.query(JobRequisition)
            .filter(JobRequisition.user_key == user_key, JobRequisition.status == "open")
            .order_by(desc(JobRequisition.created_at))
            .all()
        )
        open_role_name = open_reqs[0].title if open_reqs else "None"

        rules = _get_rules(db, user_key)

        leaves = (
            db.query(LeaveRequest)
            .filter(LeaveRequest.user_email.in_(_school_emails(db)))
            .order_by(desc(LeaveRequest.created_at))
            .all()
        )
        pending = [l for l in leaves if l.status == "pending"]
        on_leave = [
            l
            for l in leaves
            if l.status in ("approved", "pending")
            and l.start_date <= _today_str() <= (l.end_date or l.start_date)
        ]

        staff = []
        for u in users:
            try:
                balance = json.loads(u.leave_balance_json or "{}")
            except (ValueError, TypeError):
                balance = {}
            staff.append({
                "id": u.email,
                "name": u.full_name or u.email,
                "role": u.role or "Staff",
                "dept": u.department or "",
                "status": "On Leave" if any(l.user_email == u.email for l in on_leave) else "Present",
                "leaveBalance": balance.get("annual", 0),
            })

        return jsonify({
            "headcount": headcount,
            "presentToday": headcount - len(on_leave),
            "onLeave": len(on_leave),
            "openRoles": len(open_reqs),
            "openRoleName": open_role_name,
            "trainingDue": TRAINING_DUE,
            "expiringContracts": EXPIRING_CONTRACTS,
            "leaveTypes": list(rules.get("leave_types", {}).keys()),
            "requisitions": [{
                "id": r.id,
                "title": r.title,
                "department": r.department,
                "status": r.status,
            } for r in open_reqs],
            "staff": staff,
            "leaveRequests": [_leave_status(l, name_by_email) for l in leaves],
            "insights": _cached_generate_recommendations(
                (
                    f"Headcount: {headcount} (on leave: {len(on_leave)}).\n"
                    f"Open roles: {[f'{r.title} ({r.department})' for r in open_reqs]}.\n"
                    f"Contracts expiring within 45 days: {EXPIRING_CONTRACTS}.\n"
                    f"Staff overdue safety training: {TRAINING_DUE}.\n"
                    f"Pending leave requests: {len(pending)}."
                ),
                fallback=[
                    f"{EXPIRING_CONTRACTS} contracts expire within 45 days — start renewal workflow",
                    f"Safeguarding refresh overdue for {TRAINING_DUE} staff",
                    f"Leave request backlog: {len(pending)} pending manager action",
                ],
            ),
        })
    finally:
        db.close()


@hr_bp.route("/api/hr/leave/<leave_id>/decide", methods=["POST"])
@login_required
def decide_leave(leave_id):
    data = request.json or {}
    decision = data.get("decision", "")
    if decision not in ("approved", "rejected"):
        return jsonify({"error": "Invalid decision"}), 400

    user_key = _user_key()
    from flask import session as _session
    approver_email = _session.get("user", user_key)
    db = SessionLocal()
    try:
        leave = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
        if not leave:
            return jsonify({"error": "Leave request not found"}), 404

        rules = _get_rules(db, user_key)

        leave.status = decision
        if decision == "approved":
            leave.approved_by = approver_email
            user = db.query(User).filter(User.email == leave.user_email).first()
            if user:
                _deduct_balance(db, user, leave, rules)
                db.flush()

        approval = (
            db.query(ApprovalRequest)
            .filter(ApprovalRequest.workflow_type == "leave")
            .order_by(desc(ApprovalRequest.created_at))
            .all()
        )
        approval = next(
            (a for a in approval if a.metadata_json and a.metadata_json.get("leave_id") == leave_id),
            None,
        )

        if approval:
            process_approval(approval.id, approver_email, decision)

        user = db.query(User).filter(User.email == leave.user_email).first()
        requester_name = user.full_name or user.email if user else leave.user_email

        db.add(ActivityLog(
            user_email=approver_email,
            action="approve",
            resource_type="leave",
            resource_id=leave_id,
            resource_name=requester_name,
            details=f"{decision.capitalize()} {leave.leave_type} leave for {requester_name} ({leave.start_date} to {leave.end_date})",
        ))
        db.commit()
        return jsonify({"success": True, "status": decision, "message": f"Leave {decision} for {requester_name}"})
    finally:
        db.close()


@hr_bp.route("/api/hr/leave", methods=["POST"])
@login_required
def apply_leave():
    data = request.json or {}
    leave_type = (data.get("leave_type") or "").strip()
    start_date = (data.get("start_date") or "").strip()
    end_date = (data.get("end_date") or start_date).strip()
    if not leave_type or not start_date:
        return jsonify({"error": "Leave type and start date are required"}), 400

    from flask import session as _session
    requester = _session.get("user", "")
    if not requester:
        return jsonify({"error": "Authentication required"}), 401

    db = SessionLocal()
    try:
        user_key = _user_key()
        rules = _get_rules(db, user_key)
        lt = _leave_type_rules(rules, leave_type)
        if not lt:
            return jsonify({
                "error": f"Leave type '{leave_type}' is not allowed by the active leave policy",
            }), 400
        if data.get("half_day") and not lt.get("half_day_allowed"):
            return jsonify({"error": f"Half-day leave is not allowed for {leave_type} by policy"}), 400

        try:
            start, end = _date_range(start_date, end_date)
        except ValueError:
            return jsonify({"error": "Invalid dates — use YYYY-MM-DD"}), 400
        if end < start:
            return jsonify({"error": "End date cannot be before start date"}), 400
        requested = _working_days(start, end, bool(rules.get("exclude_weekends")))
        if data.get("half_day"):
            requested = 0.5
        if lt.get("max_days") and requested > lt["max_days"]:
            return jsonify({
                "error": f"{leave_type} leave is capped at {lt['max_days']} days by policy (requested {requested})",
            }), 400

        user = db.query(User).filter(User.email == requester).first()
        approver = _approver_for(db, user, rules)

        leave = LeaveRequest(
            user_email=requester,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            half_day=1 if data.get("half_day") else 0,
            reason=(data.get("reason") or "").strip(),
        )
        db.add(leave)
        db.flush()

        db.add(ApprovalRequest(
            workflow_type="leave",
            requester=requester,
            approver=approver,
            metadata_json={
                "leave_id": leave.id,
                "leave_type": leave_type,
                "start_date": start_date,
                "end_date": end_date,
            },
            steps_json=[{"order": 1, "role": "manager", "status": "pending"}],
        ))
        db.add(Notification(
            user_email=approver,
            type="approval",
            title="Leave request pending",
            message=f"{user.full_name or requester} requested {leave_type} leave ({start_date} to {end_date}).",
        ))
        db.add(ActivityLog(
            user_email=requester,
            action="leave",
            resource_type="leave",
            resource_id=leave.id,
            resource_name=user.full_name or requester,
            details=f"Applied for {leave_type} leave ({start_date} to {end_date})",
        ))
        db.commit()
        return jsonify({
            "success": True,
            "id": leave.id,
            "status": leave.status,
            "message": f"{leave_type} leave requested for approval",
        }), 201
    finally:
        db.close()


@hr_bp.route("/api/hr/leaves/mine", methods=["GET"])
@login_required
def my_leaves():
    from flask import session as _session
    requester = _session.get("user", "")
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == requester).first()
        try:
            balance = json.loads(user.leave_balance_json or "{}") if user else {}
        except (ValueError, TypeError):
            balance = {}
        leaves = (
            db.query(LeaveRequest)
            .filter(LeaveRequest.user_email == requester)
            .order_by(desc(LeaveRequest.created_at))
            .all()
        )
        return jsonify({
            "balance": balance,
            "leaves": [{
                "id": l.id,
                "type": l.leave_type,
                "dates": f"{l.start_date}–{l.end_date}" if l.end_date != l.start_date else l.start_date,
                "halfDay": bool(l.half_day),
                "status": l.status,
            } for l in leaves],
        })
    finally:
        db.close()


@hr_bp.route("/api/hr/requisitions", methods=["POST"])
@login_required
def create_requisition():
    data = request.json or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "Role title is required"}), 400

    user_key = _user_key()
    db = SessionLocal()
    try:
        req = JobRequisition(
            user_key=user_key,
            title=title,
            department=(data.get("department") or "").strip(),
            status="open",
        )
        db.add(req)
        db.add(ActivityLog(
            user_email=user_key,
            action="approve",
            resource_type="requisition",
            resource_name=title,
            details=f"Opened new requisition: {title} ({req.department or 'no dept'})",
        ))
        db.commit()
        return jsonify({
            "success": True,
            "id": req.id,
            "title": req.title,
            "department": req.department,
            "status": req.status,
            "message": f"Requisition opened for {title}",
        }), 201
    finally:
        db.close()


_EXTRACT_PROMPT = """You are a school policy parser. Parse the policy below into structured JSON.

Return ONLY valid JSON with this exact shape:
{{
  "summary": "<one-line summary of the policy>",
  "rules": {{ "<rule topic>": "<rule text>" }},
  "leave_types": {{ "<type>": {{"balance_key": "<annual|sick|personal|null>", "max_days": <int or null>, "half_day_allowed": <bool>}} }},
  "approver_routing": "<department_head|manager|admin>",
  "exclude_weekends": <bool>
}}

Rules:
- Always include "summary" and "rules" (topics like approval chain, eligibility, notices, dress code, attendance, fees, etc.).
- Only populate "leave_types", "approver_routing" and "exclude_weekends" IF the policy is a leave policy. For any other policy type, leave these as empty object / null / false.
- leave_types: balance_key is which allowance it draws from (annual, sick, personal, or null for maternity/paternity). max_days is the cap, null if unlimited. half_day_allowed reflects whether the policy permits half-day leave.

POLICY:
{content}"""


def _extract_rules(content: str) -> dict:
    try:
        raw = generate_answer(_EXTRACT_PROMPT.format(content=content[:8000]))
    except GeminiServiceError:
        raw = None
    if raw:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1:
            try:
                parsed = json.loads(raw[start:end + 1])
                if isinstance(parsed, dict) and ("summary" in parsed or "leave_types" in parsed):
                    parsed["leave_types"] = {
                        str(k).strip().lower(): v
                        for k, v in (parsed.get("leave_types") or {}).items()
                    }
                    return parsed
            except (ValueError, TypeError):
                pass
    return {"summary": content[:200], "rules": {}, "leave_types": {}, "approver_routing": None, "exclude_weekends": False}


@hr_bp.route("/api/hr/policies", methods=["GET"])
@login_required
def list_policies():
    user_key = _user_key()
    db = SessionLocal()
    try:
        policies = (
            db.query(HRPolicy)
            .filter(HRPolicy.user_key == user_key)
            .order_by(desc(HRPolicy.updated_at))
            .all()
        )
        return jsonify({
            "policies": [{
                "id": p.id,
                "name": p.name,
                "category": p.category,
                "content": p.content,
                "rules": p.rules_json or {},
                "active": bool(p.active),
                "updatedAt": time.strftime("%Y-%m-%d %H:%M", time.localtime(p.updated_at)) if p.updated_at else "",
            } for p in policies],
            "defaults": DEFAULT_RULES,
            "categories": ["leave", "attendance", "conduct", "safety", "general"],
        })
    finally:
        db.close()


@hr_bp.route("/api/hr/policies", methods=["POST"])
@login_required
def create_policy():
    data = request.json or {}
    name = (data.get("name") or "").strip()
    content = (data.get("content") or "").strip()
    category = (data.get("category") or "leave").strip()
    if not name or not content:
        return jsonify({"error": "Policy name and content are required"}), 400

    user_key = _user_key()
    rules = _extract_rules(content)
    db = SessionLocal()
    try:
        policy = HRPolicy(
            user_key=user_key,
            name=name,
            category=category,
            content=content,
            rules_json=rules,
            active=1,
        )
        db.query(HRPolicy).filter(
            HRPolicy.user_key == user_key, HRPolicy.category == category
        ).update({"active": 0})
        db.add(policy)
        db.add(ActivityLog(
            user_email=user_key,
            action="approve",
            resource_type="hr_policy",
            resource_name=name,
            details=f"Created {category} policy '{name}'",
        ))
        db.commit()
        return jsonify({
            "success": True,
            "id": policy.id,
            "name": policy.name,
            "category": policy.category,
            "rules": rules,
            "message": f"Policy '{name}' created and activated",
        }), 201
    finally:
        db.close()


@hr_bp.route("/api/hr/policies/<policy_id>", methods=["PUT"])
@login_required
def update_policy(policy_id):
    data = request.json or {}
    user_key = _user_key()
    db = SessionLocal()
    try:
        policy = db.query(HRPolicy).filter(
            HRPolicy.id == policy_id, HRPolicy.user_key == user_key
        ).first()
        if not policy:
            db.close()
            return jsonify({"error": "Policy not found"}), 404
        if "content" in data and data["content"].strip():
            policy.content = data["content"].strip()
            policy.rules_json = _extract_rules(policy.content)
        if "name" in data and data["name"].strip():
            policy.name = data["name"].strip()
        if "category" in data and data["category"].strip():
            policy.category = data["category"].strip()
        if data.get("active"):
            db.query(HRPolicy).filter(
                HRPolicy.user_key == user_key,
                HRPolicy.id != policy_id,
                HRPolicy.category == policy.category,
            ).update({"active": 0})
            policy.active = 1
        db.add(ActivityLog(
            user_email=user_key,
            action="approve",
            resource_type="hr_policy",
            resource_name=policy.name,
            details=f"Updated {policy.category} policy '{policy.name}'",
        ))
        db.commit()
        return jsonify({
            "success": True,
            "id": policy.id,
            "name": policy.name,
            "category": policy.category,
            "rules": policy.rules_json,
            "message": f"Policy '{policy.name}' updated",
        })
    finally:
        db.close()


DEMO_STAFF = [
    {"email": "pooja.iyer@ceap.school", "full_name": "Pooja Iyer", "role": "user", "department": "Academic"},
    {"email": "arjun.menon@ceap.school", "full_name": "Arjun Menon", "role": "user", "department": "Academic"},
    {"email": "meera.nair@ceap.school", "full_name": "Meera Nair", "role": "HOD", "department": "Academic"},
]

DEMO_LEAVES = [
    {"email": "pooja.iyer@ceap.school", "leave_type": "Sick", "start_date": "2026-08-03", "end_date": "2026-08-03", "reason": "Fever"},
    {"email": "arjun.menon@ceap.school", "leave_type": "Earned", "start_date": "2026-08-04", "end_date": "2026-08-08", "reason": "Planned leave"},
]


def _user_key_for(email: str) -> str:
    return hashlib.sha256(email.encode("utf-8")).hexdigest()[:32]


def seed_hr_if_empty():
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.is_admin == 1).first()
        user_key = _user_key_for(admin.email) if admin else _user_key_for("admin@ceap.school")

        if not db.query(JobRequisition).filter(JobRequisition.user_key == user_key).first():
            db.add(JobRequisition(
                user_key=user_key,
                title="PGT Science",
                department="Academic",
                status="open",
            ))

        if db.query(LeaveRequest).first():
            db.commit()
            return

        for s in DEMO_STAFF:
            existing = db.query(User).filter(User.email == s["email"]).first()
            if not existing:
                db.add(User(
                    email=s["email"],
                    full_name=s["full_name"],
                    password_hash="",
                    role=s["role"],
                    department=s["department"],
                    status="active",
                    leave_balance_json=json.dumps({"annual": 20, "sick": 12, "personal": 5}),
                ))
        db.flush()

        for lv in DEMO_LEAVES:
            leave = LeaveRequest(
                user_email=lv["email"],
                leave_type=lv["leave_type"],
                start_date=lv["start_date"],
                end_date=lv["end_date"],
                reason=lv["reason"],
            )
            db.add(leave)
            db.flush()
            db.add(ApprovalRequest(
                workflow_type="leave",
                requester=lv["email"],
                approver="admin@ceap.school",
                metadata_json={"leave_id": leave.id, "leave_type": lv["leave_type"]},
                steps_json=[{"order": 1, "role": "manager", "status": "pending"}],
            ))
            db.add(Notification(
                user_email="admin@ceap.school",
                type="approval",
                title="Leave request pending",
                message=f"{lv['email']} requested {lv['leave_type']} leave ({lv['start_date']} to {lv['end_date']}).",
            ))
        db.commit()
    finally:
        db.close()