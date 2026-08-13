import hashlib
from flask import Blueprint, jsonify, request
from app.auth_helpers import login_required
from app.db import SessionLocal
from app.models import User, CalendarEvent

calendar_bp = Blueprint("calendar", __name__)


def _user_key_for(email: str) -> str:
    return hashlib.sha256(email.encode("utf-8")).hexdigest()[:32]


def _db_key(db):
    from flask import session
    email = (session.get("user") or "").strip().lower()
    return _user_key_for(email) if email else _user_key_for("admin@ceap.school")


@calendar_bp.route("/api/calendar", methods=["GET"])
@login_required
def list_events():
    db = SessionLocal()
    try:
        user_key = _db_key(db)
        rows = (
            db.query(CalendarEvent)
            .filter(CalendarEvent.user_key == user_key)
            .order_by(CalendarEvent.date, CalendarEvent.time)
            .all()
        )
        return jsonify({"events": [
            {
                "id": e.id,
                "title": e.title,
                "date": e.date,
                "time": e.time,
                "type": e.type,
                "status": e.status,
            }
            for e in rows
        ]})
    finally:
        db.close()


@calendar_bp.route("/api/calendar", methods=["POST"])
@login_required
def create_event():
    db = SessionLocal()
    try:
        user_key = _db_key(db)
        body = request.get_json(force=True)
        title = (body.get("title") or "").strip()
        if not title:
            return jsonify({"error": "title is required"}), 400
        ev = CalendarEvent(
            user_key=user_key,
            title=title,
            date=body.get("date", ""),
            time=body.get("time", ""),
            type=body.get("type", "Meeting"),
            status=body.get("status", "Upcoming"),
        )
        db.add(ev)
        db.commit()
        db.refresh(ev)
        return jsonify({
            "id": ev.id,
            "title": ev.title,
            "date": ev.date,
            "time": ev.time,
            "type": ev.type,
            "status": ev.status,
        }), 201
    finally:
        db.close()


@calendar_bp.route("/api/calendar/<event_id>", methods=["PUT"])
@login_required
def update_event(event_id):
    db = SessionLocal()
    try:
        user_key = _db_key(db)
        ev = db.query(CalendarEvent).filter(
            CalendarEvent.id == event_id, CalendarEvent.user_key == user_key
        ).first()
        if not ev:
            return jsonify({"error": "Event not found"}), 404
        body = request.get_json(force=True)
        title = (body.get("title") or "").strip()
        if not title:
            return jsonify({"error": "title is required"}), 400
        ev.title = title
        ev.date = body.get("date", ev.date)
        ev.time = body.get("time", ev.time)
        ev.type = body.get("type", ev.type)
        ev.status = body.get("status", ev.status)
        db.commit()
        db.refresh(ev)
        return jsonify({
            "id": ev.id,
            "title": ev.title,
            "date": ev.date,
            "time": ev.time,
            "type": ev.type,
            "status": ev.status,
        })
    finally:
        db.close()


@calendar_bp.route("/api/calendar/<event_id>", methods=["DELETE"])
@login_required
def delete_event(event_id):
    db = SessionLocal()
    try:
        user_key = _db_key(db)
        ev = db.query(CalendarEvent).filter(
            CalendarEvent.id == event_id, CalendarEvent.user_key == user_key
        ).first()
        if not ev:
            return jsonify({"error": "Event not found"}), 404
        db.delete(ev)
        db.commit()
        return jsonify({"success": True})
    finally:
        db.close()


SEED_EVENTS = [
    {"title": "Leadership standup", "date": "2025-07-28", "time": "09:00", "type": "Meeting", "status": "Upcoming"},
    {"title": "Compliance Evidence Sync", "date": "2025-07-28", "time": "14:00", "type": "Compliance", "status": "In Progress"},
    {"title": "Admissions interviews", "date": "2025-07-29", "time": "11:00", "type": "Admissions", "status": "Upcoming"},
    {"title": "Fire drill", "date": "2025-07-30", "time": "10:30", "type": "Compliance", "status": "Upcoming"},
    {"title": "Parent conference – Aarav Mehta", "date": "2025-07-30", "time": "15:00", "type": "Parent", "status": "Upcoming"},
    {"title": "Leadership Knowledge Review", "date": "2025-07-30", "time": "10:00", "type": "Meeting", "status": "Upcoming"},
    {"title": "PTA executive", "date": "2025-08-02", "time": "16:00", "type": "Meeting", "status": "Upcoming"},
    {"title": "Board exam briefing Class 12", "date": "2025-08-05", "time": "14:00", "type": "Academic", "status": "Upcoming"},
    {"title": "HR Policy Q&A with Staff", "date": "2025-08-05", "time": "15:30", "type": "HR", "status": "Upcoming"},
    {"title": "Fee last date reminder blast", "date": "2025-08-10", "time": "09:00", "type": "Finance", "status": "Upcoming"},
    {"title": "AI Document Studio Walkthrough", "date": "2025-07-25", "time": "11:30", "type": "Training", "status": "Completed"},
]


def seed_calendar_if_empty():
    db = SessionLocal()
    try:
        user_key = _db_key(db)
        if db.query(CalendarEvent).filter(CalendarEvent.user_key == user_key).count() == 0:
            for row in SEED_EVENTS:
                db.add(CalendarEvent(user_key=user_key, **row))
            db.commit()
    finally:
        db.close()