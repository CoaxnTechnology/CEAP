import os
import re
from pathlib import Path

from flask import Blueprint, jsonify, request, make_response, current_app

from app.auth_helpers import login_required
from app.db import SessionLocal
from app.models import AppSetting, Department, Notification, SchoolTarget, User

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


@settings_bp.route("/api/notifications/clear", methods=["POST"])
@login_required
def notifications_clear():
    from flask import session
    email = session.get("user")
    if not email:
        return jsonify({"error": "Not authenticated"}), 401
    db = SessionLocal()
    try:
        db.query(Notification).filter(Notification.user_email == email).delete()
        db.commit()
        return jsonify({"success": True})
    finally:
        db.close()


def _mask_key(key: str) -> str:
    if not key or len(key) < 12:
        return "***" if key else ""
    return f"{key[:7]}...{key[-4:]}"


def _get_groq_setting(db):
    api_row = db.query(AppSetting).filter(AppSetting.key == "groq_api_key").first()
    model_row = db.query(AppSetting).filter(AppSetting.key == "groq_model").first()
    # fallback to env if not in DB
    api_key = (api_row.value if api_row and api_row.value else os.getenv("GROQ_API_KEY") or "")
    model = (model_row.value if model_row and model_row.value else os.getenv("GROQ_MODEL") or "llama-3.3-70b-versatile")
    return api_key, model


@settings_bp.route("/api/settings/llm", methods=["GET"])
@login_required
def llm_get():
    db = SessionLocal()
    try:
        api_key, model = _get_groq_setting(db)
        return jsonify({
            "groq_api_key_masked": _mask_key(api_key),
            "groq_api_key_set": bool(api_key.strip()),
            "groq_model": model,
            "groq_configured": bool(api_key.strip()),
        })
    finally:
        db.close()


@settings_bp.route("/api/settings/llm", methods=["PUT"])
@login_required
def llm_put():
    data = request.get_json(silent=True) or {}
    new_key = (data.get("groq_api_key") or "").strip()
    new_model = (data.get("groq_model") or "").strip()

    # allow clearing key? but require at least model if provided
    if new_key and not re.match(r"^gsk_[a-zA-Z0-9]{20,}$", new_key):
        return jsonify({"error": "Invalid Groq API key format. Must start with gsk_"}), 400
    if new_model and not re.match(r"^[a-zA-Z0-9._\-/]+$", new_model):
        return jsonify({"error": "Invalid model name"}), 400

    db = SessionLocal()
    try:
        # Use provided values, or keep existing if empty (except explicit clear)
        api_key_to_save = new_key
        # if client sent empty string but key already set, don't overwrite with empty unless they explicitly want to clear
        # For now: empty means don't change; to clear, send {"groq_api_key": ""} with clear flag? Simplest: empty = no change
        if not new_key and "groq_api_key" not in data:
            api_key_to_save = None
        elif not new_key and data.get("groq_api_key") == "":
            # explicit clear requested
            api_key_to_save = ""
        # if data didn't include key at all, treat as no change
        if api_key_to_save is not None:
            row = db.query(AppSetting).filter(AppSetting.key == "groq_api_key").first()
            if not row:
                row = AppSetting(key="groq_api_key", value=api_key_to_save)
                db.add(row)
            else:
                row.value = api_key_to_save

        if new_model:
            row = db.query(AppSetting).filter(AppSetting.key == "groq_model").first()
            if not row:
                row = AppSetting(key="groq_model", value=new_model)
                db.add(row)
            else:
                row.value = new_model

        db.commit()

        # also persist to .env for restart persistence
        try:
            env_path = Path(__file__).parents[3] / ".env"
            # backend/.env is at backend/.env, which is parents[2] from this file? Let's resolve both
            candidates = [
                Path(__file__).parents[2] / ".env",  # backend/.env
                Path(__file__).parents[3] / ".env",  # project root .env
            ]
            for p in candidates:
                if p.exists() or p.parent.exists():
                    _update_env_file(p, api_key_to_save, new_model)
                    break
        except Exception as e:
            current_app.logger.warning(f"Failed to update .env: {e}")

        # bust in-memory client so next request uses new key
        try:
            import app.services.groq_service as gs
            gs._client = None
            gs._client_key = None
        except Exception:
            pass

        api_key, model = _get_groq_setting(db)
        return jsonify({
            "success": True,
            "groq_api_key_masked": _mask_key(api_key),
            "groq_api_key_set": bool(api_key.strip()),
            "groq_model": model,
        })
    finally:
        db.close()


def _update_env_file(path: Path, new_key: str | None, new_model: str | None):
    if not path.exists():
        path.write_text("")
    text = path.read_text()
    if new_key is not None:
        if re.search(r"^GROQ_API_KEY=", text, re.MULTILINE):
            text = re.sub(r"^GROQ_API_KEY=.*$", f"GROQ_API_KEY={new_key}", text, flags=re.MULTILINE)
        else:
            text = text.rstrip() + f"\nGROQ_API_KEY={new_key}\n"
    if new_model:
        if re.search(r"^GROQ_MODEL=", text, re.MULTILINE):
            text = re.sub(r"^GROQ_MODEL=.*$", f"GROQ_MODEL={new_model}", text, flags=re.MULTILINE)
        else:
            text = text.rstrip() + f"\nGROQ_MODEL={new_model}\n"
    path.write_text(text)
