import hashlib

from flask import Blueprint, jsonify, request

from app.auth_helpers import login_required
from app.db import SessionLocal
from app.models import (
    ActivityLog,
    FeeWaiver,
    FinanceAccount,
    MonthlyCollection,
    User,
)
from app.services.gemini import generate_recommendations
from app.services.rag import _user_key
from app.services.workflow_engine import create_approval_request
from app.modules.settings.routes import get_targets

finance_bp = Blueprint("finance", __name__)

SCHOLARSHIP_BUDGET = 800000
SCHOLARSHIP_USED = 180000
MONTH_ORDER = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


def _user_key_for(email: str) -> str:
    return hashlib.sha256(email.encode("utf-8")).hexdigest()[:32]


@finance_bp.route("/api/finance/overview", methods=["GET"])
@login_required
def overview():
    user_key = _user_key()
    db = SessionLocal()
    try:
        if not db.query(FinanceAccount).filter(FinanceAccount.user_key == user_key).first():
            admin = db.query(User).filter(User.is_admin == 1).first()
            if admin:
                user_key = _user_key_for(admin.email)

        accounts = (
            db.query(FinanceAccount)
            .filter(FinanceAccount.user_key == user_key)
            .all()
        )
        mtd_target = get_targets(db, user_key)["revenue_mtd"]

        outstanding = sum(a.outstanding for a in accounts)
        families = len({a.family_email for a in accounts if a.family_email})
        predicted = sum(1 for a in accounts if a.predicted_default)
        scholarships = sum(1 for a in accounts if a.scholarship)

        cols = (
            db.query(MonthlyCollection)
            .filter(MonthlyCollection.user_key == user_key)
            .order_by(MonthlyCollection.month)
            .all()
        )
        cols = sorted(cols, key=lambda c: MONTH_ORDER.get(c.month, 99))
        trend = {"values": [c.amount_lakhs for c in cols], "labels": [c.month for c in cols]}
        mtd_collected = trend["values"][-1] * 100000 if trend["values"] else 0

        by_class = {}
        for a in accounts:
            key = a.class_name if a.class_name in ("10", "12", "9", "11", "8") else "Other"
            by_class[key] = by_class.get(key, 0) + a.outstanding
        outstanding_by_class = [
            {"cls": k, "amount": round(v / 100000, 1)}
            for k, v in sorted(by_class.items(), key=lambda kv: -kv[1])
        ]

        total = outstanding or 1
        class_10_12 = sum(v for k, v in by_class.items() if k in ("10", "12"))
        overdue_60 = sum(1 for a in accounts if a.overdue_days > 60)

        fallback_insights = [
            f"Class 10 & 12 drive {round(class_10_12 / total * 100)}% of outstanding balance.",
            f"Predicted {predicted} families may default without intervention this month.",
            f"Scholarship disbursements on track — ₹{(SCHOLARSHIP_BUDGET - SCHOLARSHIP_USED) / 100000:.1f}L remaining budget.",
            f"AI: Offer 2-installment plans to {overdue_60} families with >60 days overdue.",
        ]

        insights = generate_recommendations(
            (
                f"MTD collections: ₹{mtd_collected / 100000:.1f}L vs target ₹{mtd_target / 100000:.0f}L.\n"
                f"Outstanding: ₹{outstanding / 100000:.1f}L across {families} families "
                f"({predicted} predicted to default).\n"
                f"Class 10 & 12 share of outstanding: {round(class_10_12 / total * 100)}%.\n"
                f"Families over 60 days overdue: {overdue_60}.\n"
                f"Outstanding by class: "
                + ", ".join(f"{o['cls']} ₹{o['amount']}L" for o in outstanding_by_class)
                + "."
            ),
            fallback=fallback_insights,
        )

        risk_families = [
            {
                "studentName": a.student_name,
                "className": a.class_name,
                "familyEmail": a.family_email,
                "outstanding": a.outstanding,
                "overdueDays": a.overdue_days,
                "predictedDefault": bool(a.predicted_default),
            }
            for a in sorted(accounts, key=lambda a: -a.overdue_days)
            if a.outstanding > 0
        ]

        return jsonify({
            "kpis": {
                "mtdCollected": mtd_collected,
                "target": mtd_target,
                "outstanding": outstanding,
                "predictedDefaulters": predicted,
                "scholarships": scholarships,
                "families": families,
                "scholarshipBudgetLeft": SCHOLARSHIP_BUDGET - SCHOLARSHIP_USED,
            },
            "trend": trend,
            "outstandingByClass": outstanding_by_class,
            "insights": insights,
            "riskFamilies": risk_families,
        })
    finally:
        db.close()


@finance_bp.route("/api/finance/outreach", methods=["POST"])
@login_required
def outreach():
    user_key = _user_key()
    from flask import session as _session
    email = _session.get("user", user_key)
    db = SessionLocal()
    try:
        db.add(ActivityLog(
            user_email=email,
            action="approve",
            resource_type="outreach",
            resource_name="Collection campaign",
            details="Launched collection campaign (parent SMS/email)",
        ))
        db.commit()
    finally:
        db.close()

    from app.services.notification_service import send_email
    db = SessionLocal()
    try:
        families = (
            db.query(FinanceAccount)
            .filter(
                FinanceAccount.user_key == user_key,
                FinanceAccount.outstanding > 0,
                FinanceAccount.family_email != "",
            )
            .all()
        )
    finally:
        db.close()

    recipients = {f.family_email for f in families}
    subject = "CEAP – Fee payment reminder"
    sent = 0
    for to in recipients:
        body = (
            f"Dear Parent,\n\n"
            f"This is a reminder from {email.split('@')[0].title() or 'your school'} that the "
            f"following fee balance is outstanding:\n\n"
            f"  Student: {next((f.student_name for f in families if f.family_email == to), '—')}\n"
            f"  Outstanding: ₹{next((f.outstanding for f in families if f.family_email == to), 0):,.0f}\n\n"
            f"Please settle at your earliest convenience.\n"
            f"Regards,\nCEAP School Finance"
        )
        if send_email(to, subject, body):
            sent += 1

    return jsonify({
        "success": True,
        "message": f"Collection campaign launched — email sent to {sent} of {len(recipients)} families.",
    })


@finance_bp.route("/api/finance/waivers", methods=["POST"])
@login_required
def create_waiver():
    user_key = _user_key()
    from flask import session as _session
    email = _session.get("user", user_key)
    data = request.json or {}
    student_name = (data.get("studentName") or "").strip()
    amount = float(data.get("amount") or 0)
    if not student_name or amount <= 0:
        return jsonify({"error": "Student name and amount are required"}), 400

    db = SessionLocal()
    try:
        waiver = FeeWaiver(
            user_key=user_key,
            student_name=student_name,
            class_name=(data.get("className") or "").strip(),
            family_email=(data.get("familyEmail") or "").strip(),
            amount=amount,
            reason=(data.get("reason") or "").strip(),
        )
        db.add(waiver)
        db.flush()

        approver = "admin@ceap.school"
        admin = db.query(User).filter(User.is_admin == 1).first()
        if admin:
            approver = admin.email

        create_approval_request(
            "fee_waiver",
            requester=email,
            approver=approver,
            metadata={"waiver_id": waiver.id, "student": student_name, "amount": amount},
            steps=[{"order": 1, "role": "finance_review", "status": "pending"},
                   {"order": 2, "role": "principal", "status": "pending"}],
        )

        db.add(ActivityLog(
            user_email=email,
            action="approve",
            resource_type="fee_waiver",
            resource_name=student_name,
            details=f"Fee waiver requested for {student_name} (₹{amount:,.0f}) — sent to Approvals",
        ))
        db.commit()
        return jsonify({
            "success": True,
            "id": waiver.id,
            "message": f"Fee waiver for {student_name} sent to Approvals for review.",
        })
    finally:
        db.close()


@finance_bp.route("/api/finance/collections", methods=["PUT"])
@login_required
def update_collections():
    user_key = _user_key()
    db = SessionLocal()
    try:
        data = request.get_json(silent=True) or []
        if not isinstance(data, list):
            return jsonify({"error": "expected list of {month, amountLakhs}"}), 400
        for row in data:
            month = (row.get("month") or "").strip()
            amount = float(row.get("amountLakhs") or 0)
            if month not in MONTH_ORDER:
                return jsonify({"error": f"unknown month {month!r}"}), 400
            existing = (
                db.query(MonthlyCollection)
                .filter(MonthlyCollection.user_key == user_key, MonthlyCollection.month == month)
                .first()
            )
            if existing:
                existing.amount_lakhs = amount
            else:
                db.add(MonthlyCollection(user_key=user_key, month=month, amount_lakhs=amount))
        db.commit()
        return jsonify({"success": True})
    finally:
        db.close()



