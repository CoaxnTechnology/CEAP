"""Meetings + activity feed API."""

import time

from flask import Blueprint, jsonify, request, session

from app.auth_helpers import login_required
from app.db import SessionLocal
from app.models import ActivityLog, Meeting

meetings_bp = Blueprint("meetings", __name__)

# Backend status -> frontend badge
_STATUS_FRONTEND = {"scheduled": "Upcoming", "completed": "Completed", "cancelled": "Cancelled"}


def _serialize_meeting(m):
    return {
        "id": m.id,
        "title": m.title,
        "agenda": m.description or "",
        "date": m.date,
        "time": m.time or "10:00 AM",
        "attendees": m.attendees or [],
        "organizer": m.organizer,
        "status": _STATUS_FRONTEND.get(m.status, "Upcoming"),
    }


def _relative(ts):
    diff = time.time() - ts
    if diff < 60:
        return "Just now"
    if diff < 3600:
        return f"{int(diff // 60)} min ago"
    if diff < 86400:
        return f"{int(diff // 3600)} hr ago"
    return f"{int(diff // 86400)}d ago"


def _serialize_activity(a):
    user = (a.user_email or "").split("@")[0].replace(".", " ").replace("_", " ").title()
    return {
        "id": a.id,
        "user": user,
        "action": (a.action or "").title(),
        "target": a.resource_name or a.details or "Record",
        "time": _relative(a.created_at or time.time()),
        "type": a.resource_type or "update",
    }


def seed_meetings_if_empty():
    db = SessionLocal()
    try:
        if db.query(Meeting).count() == 0:
            seeds = [
                {"title": "Leadership Knowledge Review", "date": "2025-07-30", "time": "10:00 AM",
                 "description": "Review open knowledge gaps before board inspection",
                 "attendees": ["Priya Sharma", "Meera Nair", "Rahul Mehta"], "organizer": "rio@ceap.school", "status": "scheduled"},
                {"title": "Compliance Evidence Sync", "date": "2025-07-28", "time": "2:00 PM",
                 "description": "Fire safety cert renewal & transport SOP",
                 "attendees": ["Anita Desai", "Vikram Singh"], "organizer": "rio@ceap.school", "status": "scheduled"},
            ]
            for row in seeds:
                db.add(Meeting(**row))
            db.commit()
    finally:
        db.close()


@meetings_bp.route("/api/meetings", methods=["GET"])
@login_required
def list_meetings():
    db = SessionLocal()
    try:
        rows = db.query(Meeting).order_by(Meeting.date.desc(), Meeting.time.desc()).all()
        return jsonify({"meetings": [_serialize_meeting(m) for m in rows]})
    finally:
        db.close()


@meetings_bp.route("/api/meetings", methods=["POST"])
@login_required
def create_meeting():
    data = request.json or {}
    title = (data.get("title") or "").strip()
    if not title or not data.get("date"):
        return jsonify({"error": "title and date are required"}), 400
    db = SessionLocal()
    try:
        m = Meeting(
            title=title[:255],
            description=(data.get("agenda") or "").strip(),
            date=data.get("date"),
            time=(data.get("time") or "10:00 AM"),
            attendees=(
                data.get("attendees") or [session.get("username") or "You"]
            ),
            organizer=session.get("user") or "admin@ceap.school",
            status="scheduled",
        )
        db.add(m)
        db.commit()
        db.refresh(m)
        return jsonify({"success": True, "meeting": _serialize_meeting(m)}), 201
    finally:
        db.close()


@meetings_bp.route("/api/meetings/<meeting_id>", methods=["PATCH"])
@login_required
def update_meeting(meeting_id):
    data = request.json or {}
    status = data.get("status")
    if status not in ("completed", "cancelled"):
        if not status:
            return jsonify({"error": "status is required"}), 400
    db = SessionLocal()
    try:
        m = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not m:
            return jsonify({"error": "Meeting not found"}), 404
        m.status = status
        if data.get("title"):
            m.title = str(data["title"])[:255]
        db.commit()
        db.refresh(m)
        return jsonify({"success": True, "meeting": _serialize_meeting(m)})
    finally:
        db.close()


@meetings_bp.route("/api/meetings/<meeting_id>", methods=["DELETE"])
@login_required
def delete_meeting(meeting_id):
    db = SessionLocal()
    try:
        m = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not m:
            return jsonify({"error": "Meeting not found"}), 404
        db.delete(m)
        db.commit()
        return jsonify({"success": True})
    finally:
        db.close()


@meetings_bp.route("/api/activity", methods=["GET"])
@login_required
def list_activity():
    db = SessionLocal()
    try:
        rows = db.query(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(50).all()
        return jsonify({"activity": [_serialize_activity(a) for a in rows]})
    finally:
        db.close()