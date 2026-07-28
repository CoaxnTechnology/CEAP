import time
from app.db import SessionLocal
from app.models import ApprovalRequest, Notification


def create_approval_request(
    workflow_type: str,
    requester: str,
    approver: str,
    metadata: dict = None,
    steps: list = None,
) -> dict:
    db = SessionLocal()
    try:
        req = ApprovalRequest(
            workflow_type=workflow_type,
            requester=requester,
            approver=approver,
            metadata_json=metadata or {},
            steps_json=steps or [{"order": 1, "role": "approver", "status": "pending"}],
        )
        db.add(req)

        notif = Notification(
            user_email=approver,
            type="approval",
            title=f"New {workflow_type} approval request",
            message=f"You have a pending {workflow_type} request from {requester}.",
        )
        db.add(notif)
        db.commit()
        return {"id": req.id, "status": "pending"}
    finally:
        db.close()


def process_approval(request_id: str, approver: str, decision: str, comment: str = "") -> dict:
    db = SessionLocal()
    try:
        req = db.query(ApprovalRequest).filter(ApprovalRequest.id == request_id).first()
        if not req:
            return {"error": "Request not found"}
        if req.approver != approver:
            return {"error": "User is not the approver for this request"}

        req.status = decision
        req.updated_at = time.time()

        notif = Notification(
            user_email=req.requester,
            type="approval",
            title=f"Request {decision}",
            message=f"Your {req.workflow_type} request was {decision} by {approver}.",
        )
        db.add(notif)
        db.commit()

        return {"id": req.id, "status": decision, "message": f"Request {decision}"}
    finally:
        db.close()


def get_pending_for_user(user_email: str) -> list:
    db = SessionLocal()
    try:
        requests = (
            db.query(ApprovalRequest)
            .filter(
                (ApprovalRequest.approver == user_email) | (ApprovalRequest.requester == user_email),
                ApprovalRequest.status == "pending",
            )
            .order_by(ApprovalRequest.created_at.desc())
            .all()
        )
        return [
            {
                "id": r.id,
                "type": r.workflow_type,
                "requester": r.requester,
                "approver": r.approver,
                "status": r.status,
                "details": r.metadata_json,
                "created": r.created_at,
            }
            for r in requests
        ]
    finally:
        db.close()
