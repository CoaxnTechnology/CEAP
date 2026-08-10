from flask import Blueprint, jsonify, request

from app.auth_helpers import login_required
from app.db import SessionLocal
from app.models import SchoolTarget

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
