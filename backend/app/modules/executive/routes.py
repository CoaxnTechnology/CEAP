import hashlib
import time

from flask import Blueprint, jsonify

from app.auth_helpers import login_required
from app.db import SessionLocal
from app.models import (
    AdmissionApplication,
    ApprovalRequest,
    CalendarEvent,
    ComplianceEvidence,
    MonthlyCollection,
    Student,
    User,
)
from app.services.gemini import generate_briefing, generate_recommendations
from app.modules.settings.routes import get_targets

executive_bp = Blueprint("executive", __name__)


def _user_key_for(email: str) -> str:
    return hashlib.sha256(email.encode("utf-8")).hexdigest()[:32]


def _db_key(db):
    admin = db.query(User).filter(User.is_admin == 1).first()
    return _user_key_for(admin.email) if admin else _user_key_for("admin@ceap.school")


def _format_date() -> str:
    return time.strftime("%A, %d %B %Y")


def _task(task_id, title, owner, due, priority, workspace):
    return {"id": task_id, "title": title, "owner": owner, "due": due, "priority": priority, "workspace": workspace}


@executive_bp.route("/api/executive/overview", methods=["GET"])
@login_required
def overview():
    db = SessionLocal()
    try:
        user_key = _db_key(db)
        targets = get_targets(db, user_key)
        mtd_target = targets["revenue_mtd"]
        att_target = targets["attendance"]
        compliance_target = targets["compliance"]

        students = db.query(Student).filter(Student.user_key == user_key).all()
        att = round(sum(s.attendance or 0 for s in students) / len(students), 1) if students else 0
        high = sum(1 for s in students if s.risk_level == "High")
        at_risk = sum(1 for s in students if s.risk_level in ("High", "Medium"))

        cols = db.query(MonthlyCollection).filter(MonthlyCollection.user_key == user_key).all()
        mtd = cols[-1].amount_lakhs * 100000 if cols else 0
        vs_target = round((mtd - mtd_target) / mtd_target * 100)

        apps = db.query(AdmissionApplication).filter(AdmissionApplication.user_key == user_key).all()
        interview = sum(1 for a in apps if a.stage == "Interview")

        pending = (
            db.query(ApprovalRequest)
            .filter(ApprovalRequest.status == "pending")
            .order_by(ApprovalRequest.created_at.desc())
            .all()
        )

        evidence = db.query(ComplianceEvidence).filter(ComplianceEvidence.user_key == user_key).all()
        readiness = None
        if evidence:
            available = sum(1 for e in evidence if e.status == "Available")
            readiness = round(available / len(evidence) * 100)

        risk_students = sorted(
            [s for s in students if s.risk_level in ("High", "Medium")],
            key=lambda s: -s.risk_score,
        )

        events = (
            db.query(CalendarEvent)
            .filter(CalendarEvent.user_key == user_key, CalendarEvent.status != "Completed")
            .order_by(CalendarEvent.date, CalendarEvent.time)
            .all()
        )

        att_summary = "Attendance is strong" if att >= att_target else "Attendance is soft"
        fee_summary = (
            "Fee collections are on target."
            if vs_target >= 0
            else f"Fee collections lag {abs(vs_target)}% vs target."
        )
        risk_summary = (
            f"{high} high-risk student{'s' if high != 1 else ''} need counselor attention."
            if high
            else "No students flagged high risk."
        )
        context = (
            f"Attendance: {att}% (high-risk {high}, at-risk {at_risk}).\n"
            f"Revenue MTD: ₹{mtd / 100000:.1f}L vs target ₹{mtd_target / 100000:.0f}L "
            f"({vs_target:+d}%).\n"
            f"Compliance readiness: {readiness}% (target {compliance_target}%).\n"
            f"Pending approvals: {[a.workflow_type for a in pending]}.\n"
            f"Admissions awaiting interview: {interview}.\n"
            f"High-risk students: {[f'{s.name} ({s.class_name})' for s in risk_students[:3]]}."
        )

        fallback_summary = f"{att_summary} at {att}%. {fee_summary} {risk_summary}"

        fallback_bullets = [
            {"type": "success" if att >= att_target else "warning", "text": f"Attendance {att}% — {'above' if att >= att_target else 'below'} target {att_target}%"},
            {"type": "warning", "text": f"₹{mtd / 100000:.1f}L collected MTD · {abs(vs_target)}% vs target"},
        ]
        if readiness is not None and readiness < compliance_target:
            fallback_bullets.append({"type": "alert", "text": f"Compliance readiness {readiness}% below target {compliance_target}%"})
        if high:
            fallback_bullets.append({"type": "alert", "text": f"{high} high-risk students flagged — coordinate intervention"})
        fallback_bullets.append({"type": "info", "text": f"{interview} admissions applications awaiting interview"})
        fallback_bullets.append({"type": "ai", "text": "AI recommends parent outreach for top fee defaulters"})

        briefing = generate_briefing(
            context,
            fallback={"summary": fallback_summary, "bullets": fallback_bullets},
        )
        summary = briefing["summary"]
        bullets = briefing["bullets"]

        tasks = []
        for i, a in enumerate(pending):
            tasks.append(_task(
                f"approval-{a.id}",
                f"Review {a.workflow_type.replace('_', ' ')} request",
                a.requester,
                time.strftime("%Y-%m-%d", time.localtime(a.created_at)),
                "Urgent",
                "Approvals",
            ))
        for s in risk_students[:2]:
            tasks.append(_task(
                f"risk-{s.id}",
                f"Counselor outreach – {s.name}",
                "Counselor",
                "ASAP",
                "High",
                "Students",
            ))
        if readiness is not None and readiness < 80:
            tasks.append(_task(
                "compliance-gaps",
                "Close compliance evidence gaps",
                "Compliance",
                time.strftime("%Y-%m-%d"),
                "High",
                "Compliance",
            ))

        return jsonify({
            "date": _format_date(),
            "summary": summary,
            "bullets": bullets,
            "kpis": {
                "attendance": {"value": f"{att}%", "delta": "Live"},
                "revenue": {
                    "value": f"₹{mtd / 100000:.1f}L",
                    "delta": f"{vs_target}% vs target" if vs_target < 0 else "+on target",
                    "trend": "down" if vs_target < 0 else "up",
                },
                "admissions": {"value": str(len(apps)), "delta": "Live"},
                "risk": {"value": str(at_risk), "delta": f"{high} high", "trend": "warn"},
                "approvals": {"value": str(len(pending)), "delta": "SLA", "trend": "warn"},
                "compliance": (
                    {"value": f"{readiness}%", "delta": "Live"}
                    if readiness is not None
                    else None
                ),
            },
            "recommendations": generate_recommendations(
                context,
                fallback=[
                    f"Review fee waiver request from {a.requester}" for a in pending[:1]
                ]
                + (
                    ["Start Fire Safety Certificate renewal workflow"]
                    if readiness is not None and readiness < 80
                    else []
                )
                + (
                    [f"Counselor outreach for {s.name} ({s.class_name})" for s in risk_students[:2]]
                ),
            ),
            "tasks": tasks[:5],
            "approvals": [
                {
                    "id": a.id,
                    "title": a.metadata_json.get("student", a.workflow_type.replace("_", " ")),
                    "type": a.workflow_type.replace("_", " ").title(),
                    "requester": a.requester,
                    "sla": "Pending",
                }
                for a in pending[:4]
            ],
            "riskStudents": [
                {"id": s.id, "name": s.name, "class": s.class_name, "riskScore": s.risk_score}
                for s in risk_students[:3]
            ],
            "calendar": [
                {"id": e.id, "title": e.title, "date": e.date, "time": e.time, "type": e.type}
                for e in events[:4]
            ],
            "complianceAlert": (
                {"message": f"Inspection readiness at {readiness}%. Close evidence gaps."}
                if readiness is not None and readiness < 100
                else None
            ),
        })
    finally:
        db.close()


def seed_executive_if_empty():
    db = SessionLocal()
    try:
        if db.query(ApprovalRequest).filter(ApprovalRequest.status == "pending").count() == 0:
            admin = db.query(User).filter(User.is_admin == 1).first()
            approver = admin.email if admin else "admin@ceap.school"
            seeds = [
                {"workflow_type": "fee_waiver", "requester": "finance@ceap.school", "metadata": {"student": "Fee waiver – Kabir Sharma (25%)"}},
                {"workflow_type": "publish_document", "requester": "studio@ceap.school", "metadata": {"student": "Parent Circular – Annual Day 2025"}},
                {"workflow_type": "purchase", "requester": "operations@ceap.school", "metadata": {"student": "Purchase – Lab chemicals Q2"}},
                {"workflow_type": "transport", "requester": "transport@ceap.school", "metadata": {"student": "Transport route change – Whitefield"}},
            ]
            for s in seeds:
                db.add(ApprovalRequest(
                    workflow_type=s["workflow_type"],
                    requester=s["requester"],
                    approver=approver,
                    status="pending",
                    metadata_json=s["metadata"],
                    steps_json=[{"order": 1, "role": "principal", "status": "pending"}],
                ))
            db.commit()
    finally:
        db.close()
