from flask import Blueprint, jsonify, request, make_response

from app.auth_helpers import login_required
from app.db import SessionLocal
from app.models import Department, SchoolTarget, Notification, User

settings_bp = Blueprint("settings", __name__)

DEFAULTS = {"revenue_mtd": 5200000, "attendance": 90.0, "compliance": 80.0}


def get_targets(db, user_key):
    row = db.query(SchoolTarget).filter(SchoolTarget.user_key == user_key).first()
    if not row:
        return dict(DEFAULTS)
    return {
        "revenue_mtd": row.revenue_mtd or DEFAULTS["revenue_mtd"],
        "attendance": row.attendance or DEFAULTS["attendance"],
        "compliance": row.compliance or DEFAULTS["compliance"],
    }


@settings_bp.route("/api/settings/targets", methods=["GET"])
@login_required
def targets_get():
    from app.services.rag import _user_key

    db = SessionLocal()
    try:
        return jsonify(get_targets(db, _user_key()))
    finally:
        db.close()


@settings_bp.route("/api/settings/targets", methods=["PUT"])
@login_required
def targets_put():
    from app.services.rag import _user_key

    data = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        user_key = _user_key()
        row = db.query(SchoolTarget).filter(SchoolTarget.user_key == user_key).first()
        if not row:
            row = SchoolTarget(user_key=user_key)
            db.add(row)
        for field in DEFAULTS:
            if field in data:
                value = data[field]
                if value is None:
                    continue
                value = float(value)
                if value <= 0:
                    return jsonify({"error": f"{field} must be positive"}), 400
                setattr(row, field, value)
        db.commit()
        return jsonify(get_targets(db, user_key))
    finally:
        db.close()


def _notif_payload(n):
    return {
        "id": n.id,
        "type": n.type,
        "title": n.title,
        "message": n.message,
        "link": n.link,
        "unread": not n.read,
        "time": _fmt_time(n.created_at),
    }


def _fmt_time(ts):
    if not ts:
        return ""
    import time
    from datetime import datetime

    dt = datetime.fromtimestamp(ts)
    delta = int(time.time() - ts)
    if delta < 60:
        return "Just now"
    if delta < 3600:
        return f"{delta // 60}m ago"
    if delta < 86400:
        return f"{delta // 3600}h ago"
    return dt.strftime("%d %b %Y")


def _get_notifs(db):
    from flask import session

    email = session.get("user")
    if not email:
        return []
    rows = (
        db.query(Notification)
        .filter(Notification.user_email == email)
        .order_by(Notification.created_at.desc())
        .limit(20)
        .all()
    )
    return [_notif_payload(n) for n in rows]


def _get_unread(db):
    from flask import session

    email = session.get("user")
    if not email:
        return 0
    return (
        db.query(Notification)
        .filter(Notification.user_email == email, Notification.read == 0)
        .count()
    )


@settings_bp.route("/api/notifications", methods=["GET"])
@login_required
def notifications_get():
    db = SessionLocal()
    try:
        return jsonify(
            {"notifications": _get_notifs(db), "unread": _get_unread(db)}
        )
    finally:
        db.close()


@settings_bp.route("/api/notifications/create", methods=["POST"])
@login_required
def notifications_create():
    from flask import session

    from app.services.notification_service import create_notification

    data = request.get_json(silent=True) or {}
    email = session.get("user")
    if not email:
        return jsonify({"error": "Not authenticated"}), 401
    notif = create_notification(
        user_email=email,
        notif_type=data.get("type", "info"),
        title=data.get("title", ""),
        message=data.get("message", ""),
        link=data.get("link", ""),
    )
    return jsonify({"success": True, "id": notif["id"]})


@settings_bp.route("/api/departments", methods=["GET"])
@login_required
def list_departments():
    """Dynamic departments for current user's school. General is always implicit."""
    from flask import session
    db = SessionLocal()
    try:
        email = (session.get("user") or "").strip().lower()
        user = db.query(User).filter(User.email == email).first() if email else None
        if not user or not user.school_id:
            resp = make_response(jsonify({"departments": []}))
            resp.headers["Cache-Control"] = "no-store"
            return resp
        depts = db.query(Department).filter(Department.school_id == user.school_id).order_by(Department.name).all()
        payload = [{"id": d.id, "name": d.name, "code": d.code or ""} for d in depts]
        resp = make_response(jsonify({"departments": payload}))
        resp.headers["Cache-Control"] = "no-store"
        return resp
    finally:
        db.close()


@settings_bp.route("/api/notifications/read", methods=["POST"])
@login_required
def notifications_read():
    from flask import session

    data = request.get_json(silent=True) or {}
    email = session.get("user")
    ids = data.get("ids") or []
    if not ids or not email:
        return jsonify({"error": "Missing ids"}), 400

    db = SessionLocal()
    try:
        for nid in ids:
            db.query(Notification).filter(
                Notification.id == nid, Notification.user_email == email
            ).update({"read": 1})
        db.commit()
        return jsonify({"success": True, "unread": _get_unread(db)})
    finally:
        db.close()
