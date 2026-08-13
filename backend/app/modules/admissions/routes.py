import hashlib
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from app.auth_helpers import login_required
from app.db import SessionLocal
from app.models import ActivityLog, AdmissionApplication, Student, User
from app.services.gemini import generate_recommendations
from app.services.rag import _user_key

admissions_bp = Blueprint("admissions", __name__)

STAGES = ["Applied", "Tour", "Interview", "Offer", "Enrolled"]
TARGET_SEATS = 120
SEATS_FILLED = 86


def _user_key_for(email: str) -> str:
    return hashlib.sha256(email.encode("utf-8")).hexdigest()[:32]


def _serialize(a):
    return {
        "id": a.id,
        "name": a.student_name,
        "grade": a.grade,
        "stage": a.stage,
        "score": a.score,
        "counselor": a.counselor,
        "parentName": a.parent_name,
        "parentContact": a.parent_contact,
        "date": a.date,
        "student_id": a.student_id or "",
        "removed_at": a.removed_at,
    }


RETAIN_HOURS = 24


def _db_key(db):
    from flask import session
    email = (session.get("user") or "").strip().lower()
    return _user_key_for(email) if email else _user_key_for("admin@ceap.school")


def _ensure_student(db, app_row):
    """Create/link a Student record when an application reaches Enrolled."""
    if app_row.stage != "Enrolled":
        return None
    existing = db.query(Student).filter(Student.admission_id == app_row.id).first()
    if not existing:
        student = Student(
            user_key=app_row.user_key,
            name=app_row.student_name,
            class_name=app_row.grade,
            admission_no=f"GIS/{(app_row.date or '')} / {app_row.id[:4].upper()}",
            risk_level="Low",
            attendance=100,
            fees_status="Cleared",
            parent_name=app_row.parent_name,
            admission_id=app_row.id,
        )
        db.add(student)
        db.flush()
        db.refresh(student)
        app_row.student_id = student.id
        return student.id
    app_row.student_id = existing.id
    return existing.id


@admissions_bp.route("/api/admissions/overview", methods=["GET"])
@login_required
def overview():
    db = SessionLocal()
    try:
        user_key = _db_key(db)
        apps = (
            db.query(AdmissionApplication)
            .filter(AdmissionApplication.user_key == user_key)
            .order_by(AdmissionApplication.date.desc())
            .all()
        )

        now = datetime.now(timezone.utc).timestamp()
        for a in apps:
            if a.removed_at and now - a.removed_at >= RETAIN_HOURS * 3600:
                db.query(Student).filter(Student.admission_id == a.id).delete()
                db.delete(a)
        db.commit()
        apps = (
            db.query(AdmissionApplication)
            .filter(AdmissionApplication.user_key == user_key)
            .order_by(AdmissionApplication.date.desc())
            .all()
        )
        pipeline = [a for a in apps if not a.removed_at]
        all_apps = apps

        high_apps = sorted(
            [a for a in pipeline if a.score], key=lambda a: -a.score
        )[:3]
        by_stage = {"Applied": 0, "Interview": 0, "Offer": 0, "Enrolled": 0}
        for a in pipeline:
            st = a.stage or "Applied"
            if st in by_stage:
                by_stage[st] += 1

        fallback_insights = []
        top = next(
            (a for a in sorted(pipeline, key=lambda a: -a.score) if a.stage == "Interview"),
            None,
        )
        if top:
            fallback_insights.append(f"{top.student_name} (Grade {top.grade}) scores {top.score} — prioritize appointment {top.date}")
        fallback_insights.append("Nursery pipeline light — recommend open house push")
        fallback_insights.append("Conversion 33% · top schools in city average 28%")

        insights = generate_recommendations(
            (
                f"Total applications: {len(pipeline)}.\n"
                f"By stage: {by_stage}.\n"
                f"Top-scoring applicants: {[f'{a.student_name} (Grade {a.grade}, {a.score})' for a in high_apps]}.\n"
                f"Seats: {SEATS_FILLED}/{TARGET_SEATS} filled."
            ),
            fallback=fallback_insights,
        )

        return jsonify({
            "stats": {
                "applied": by_stage["Applied"],
                "interview": by_stage["Interview"],
                "offer": by_stage["Offer"],
                "enrolled": by_stage["Enrolled"],
                "conversion": f"{round(by_stage['Enrolled'] / len(pipeline) * 100) if pipeline else 0}%",
                "targetSeats": TARGET_SEATS,
                "filled": SEATS_FILLED,
            },
            "insights": insights,
            "pipeline": [_serialize(a) for a in pipeline],
            "applications": [_serialize(a) for a in all_apps],
        })
    finally:
        db.close()


@admissions_bp.route("/api/admissions", methods=["POST"])
@login_required
def create_inquiry():
    from flask import session as _session
    email = _session.get("user", _user_key())
    data = request.json or {}
    student_name = (data.get("studentName") or "").strip()
    if not student_name:
        return jsonify({"error": "Applicant name is required"}), 400

    db = SessionLocal()
    try:
        user_key = _db_key(db)
        app_row = AdmissionApplication(
            user_key=user_key,
            student_name=student_name,
            grade=(data.get("grade") or "").strip(),
            stage="Applied",
            score=0,
            counselor=(data.get("counselor") or "").strip(),
            parent_name=(data.get("parentName") or "").strip(),
            parent_contact=(data.get("parentContact") or "").strip(),
            date=datetime.now().strftime("%Y-%m-%d"),
        )
        db.add(app_row)
        db.add(ActivityLog(
            user_email=email,
            action="approve",
            resource_type="admission",
            resource_name=student_name,
            details=f"New inquiry logged: {student_name} (Grade {app_row.grade or 'n/a'})",
        ))
        db.commit()
        return jsonify({"success": True, **_serialize(app_row)})
    finally:
        db.close()


@admissions_bp.route("/api/admissions/<app_id>/advance", methods=["POST"])
@login_required
def advance(app_id):
    from flask import session as _session
    email = _session.get("user", "")
    db = SessionLocal()
    try:
        app_row = db.query(AdmissionApplication).filter(AdmissionApplication.id == app_id).first()
        if not app_row:
            return jsonify({"error": "Application not found"}), 404

        i = STAGES.index(app_row.stage) if app_row.stage in STAGES else -1
        next_stage = STAGES[min(i + 1, len(STAGES) - 1)]
        if next_stage == app_row.stage:
            return jsonify({"error": "Already at final stage (Enrolled)"}), 400
        app_row.stage = next_stage
        created_student_id = _ensure_student(db, app_row)

        db.add(ActivityLog(
            user_email=email,
            action="approve",
            resource_type="admission",
            resource_name=app_row.student_name,
            details=f"{app_row.student_name} advanced to {next_stage}",
        ))
        db.commit()
        return jsonify({"success": True, **_serialize(app_row), "student_id": created_student_id})
    finally:
        db.close()


@admissions_bp.route("/api/admissions/<app_id>", methods=["PATCH"])
@login_required
def move(app_id):
    from flask import session as _session
    email = _session.get("user", "")
    data = request.json or {}
    stage = data.get("stage")
    if stage not in STAGES:
        return jsonify({"error": f"stage must be one of {', '.join(STAGES)}"}), 400

    db = SessionLocal()
    try:
        app_row = db.query(AdmissionApplication).filter(AdmissionApplication.id == app_id).first()
        if not app_row:
            return jsonify({"error": "Application not found"}), 404

        app_row.stage = stage
        created_student_id = _ensure_student(db, app_row)

        db.add(ActivityLog(
            user_email=email,
            action="approve",
            resource_type="admission",
            resource_name=app_row.student_name,
            details=f"{app_row.student_name} moved to {stage}",
        ))
        db.commit()
        return jsonify({"success": True, **_serialize(app_row), "student_id": created_student_id})
    finally:
        db.close()


@admissions_bp.route("/api/admissions/<app_id>", methods=["DELETE"])
@login_required
def remove(app_id):
    from flask import session as _session
    email = _session.get("user", "")
    db = SessionLocal()
    try:
        app_row = db.query(AdmissionApplication).filter(AdmissionApplication.id == app_id).first()
        if not app_row:
            return jsonify({"error": "Application not found"}), 404

        if app_row.stage == "Enrolled":
            app_row.removed_at = datetime.now(timezone.utc).timestamp()
            db.add(ActivityLog(
                user_email=email,
                action="delete",
                resource_type="admission",
                resource_name=app_row.student_name,
                details=f"Enrolled student removed from pipeline — purges after {RETAIN_HOURS}h",
            ))
            db.commit()
            return jsonify({"success": True, "removed_at": app_row.removed_at})

        db.query(Student).filter(Student.admission_id == app_row.id).delete()
        db.add(ActivityLog(
            user_email=email,
            action="delete",
            resource_type="admission",
            resource_name=app_row.student_name,
            details=f"Application removed: {app_row.student_name}",
        ))
        db.delete(app_row)
        db.commit()
        return jsonify({"success": True})
    finally:
        db.close()


DEMO_APPLICANTS = [
    {"student_name": "Ishaan Rao", "grade": "1", "stage": "Applied", "score": 82, "counselor": "Sneha K.", "date": "2025-07-20"},
    {"student_name": "Myra Singh", "grade": "6", "stage": "Interview", "score": 91, "counselor": "Rahul M.", "date": "2025-07-18"},
    {"student_name": "Dev Malhotra", "grade": "9", "stage": "Offer", "score": 88, "counselor": "Sneha K.", "date": "2025-07-15"},
    {"student_name": "Pari Desai", "grade": "Nursery", "stage": "Tour", "score": 70, "counselor": "Anita D.", "date": "2025-07-22"},
    {"student_name": "Reyansh Gupta", "grade": "11", "stage": "Enrolled", "score": 94, "counselor": "Rahul M.", "date": "2025-07-10"},
    {"student_name": "Aisha Banerjee", "grade": "4", "stage": "Applied", "score": 77, "counselor": "Anita D.", "date": "2025-07-24"},
]


def seed_admissions_if_empty():
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.is_admin == 1).first()
        user_key = _user_key_for(admin.email) if admin else _user_key_for("admin@ceap.school")

        if not db.query(AdmissionApplication).filter(AdmissionApplication.user_key == user_key).first():
            for row in DEMO_APPLICANTS:
                db.add(AdmissionApplication(user_key=user_key, **row))
            db.flush()

        for app_row in db.query(AdmissionApplication).filter(
            AdmissionApplication.user_key == user_key, AdmissionApplication.stage == "Enrolled"
        ).all():
            existing_student = db.query(Student).filter(Student.admission_id == app_row.id).first()
            if existing_student and not app_row.student_id:
                app_row.student_id = existing_student.id
            if not db.query(Student).filter(Student.admission_id == app_row.id).first():
                db.add(Student(
                    user_key=user_key,
                    name=app_row.student_name,
                    class_name=app_row.grade,
                    admission_no=f"GIS/{(app_row.date or '')} / {app_row.id[:4].upper()}",
                    risk_level="Low",
                    attendance=100,
                    fees_status="Cleared",
                    parent_name=app_row.parent_name,
                    admission_id=app_row.id,
                ))
        db.commit()
    finally:
        db.close()