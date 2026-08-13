import hashlib

from flask import Blueprint, jsonify, request

from app.auth_helpers import login_required
from app.db import SessionLocal
from app.models import Assessment, ClassAttendance, CoverageEntry, Student, User
from app.services.gemini import generate_recommendations

academic_bp = Blueprint("academic", __name__)

# class prefix -> department bucket
_CLASS_DEPT = [
    ("Science", ("12", "11")),
    ("Mathematics", ("10", "9")),
    ("Languages", ("8", "7")),
    ("Humanities", ("6", "5")),
    ("Arts & Sports", ("Nursery", "KG")),
]

_DEPARTMENTS = [d for d, _ in _CLASS_DEPT]

# Seed data for coverage (department, class, coverage%) and assessments.
SEED_COVERAGE = [
    ("Science", "12-C", 74),
    ("Science", "11-A", 70),
    ("Mathematics", "10-A", 62),
    ("Mathematics", "9-A", 68),
    ("Languages", "8-B", 70),
    ("Languages", "7-A", 72),
    ("Humanities", "6-A", 66),
    ("Humanities", "5-A", 68),
    ("Arts & Sports", "KG-A", 80),
]

SEED_ASSESSMENTS = [
    {"department": "Mathematics", "class_name": "10-A", "title": "Algebra mid-term", "teacher": "Rahul M.", "due_date": "2026-08-01", "status": "scheduled"},
    {"department": "Mathematics", "class_name": "9-A", "title": "Linear equations quiz", "teacher": "Sneha K.", "due_date": "2026-08-05", "status": "scheduled"},
    {"department": "Science", "class_name": "12-C", "title": "Physics unit test", "teacher": "Meera N.", "due_date": "2026-08-10", "status": "scheduled"},
    {"department": "Languages", "class_name": "8-B", "title": "Essay draft", "teacher": "Anita D.", "due_date": "2026-07-30", "status": "scheduled"},
    {"department": "Humanities", "class_name": "5-A", "title": "Map reading test", "teacher": "Imran K.", "due_date": "2026-07-28", "status": "graded"},
]

# (class_name, present, total) for the most recent session.
SEED_ATTENDANCE = [
    ("12-C", 18, 22),
    ("11-A", 20, 24),
    ("10-A", 28, 30),
    ("9-A", 26, 30),
    ("8-B", 31, 34),
    ("7-A", 29, 32),
    ("6-A", 24, 26),
    ("5-A", 30, 33),
    ("KG-A", 23, 25),
]


def _user_key_for(email: str) -> str:
    return hashlib.sha256(email.encode("utf-8")).hexdigest()[:32]


def _db_key(db):
    from flask import session
    email = (session.get("user") or "").strip().lower()
    return _user_key_for(email) if email else _user_key_for("admin@ceap.school")


def _dept_for(class_name: str) -> str:
    for name, prefixes in _CLASS_DEPT:
        if class_name.startswith(prefixes):
            return name
    return "Arts & Sports"


def seed_academic_if_empty():
    db = SessionLocal()
    try:
        user_key = _db_key(db)
        if db.query(CoverageEntry).filter(CoverageEntry.user_key == user_key).count() == 0:
            for dept, cls, cov in SEED_COVERAGE:
                db.add(CoverageEntry(
                    user_key=user_key, department=dept, class_name=cls, coverage=cov
                ))
        if db.query(Assessment).filter(Assessment.user_key == user_key).count() == 0:
            for row in SEED_ASSESSMENTS:
                db.add(Assessment(user_key=user_key, **row))
        if db.query(ClassAttendance).filter(ClassAttendance.user_key == user_key).count() == 0:
            for cls, present, total in SEED_ATTENDANCE:
                db.add(ClassAttendance(
                    user_key=user_key, class_name=cls, date="2026-08-03",
                    present=present, total=total,
                ))
        db.commit()
    finally:
        db.close()


def _serialize_assessment(a):
    return {
        "id": a.id,
        "department": a.department,
        "class_name": a.class_name,
        "title": a.title,
        "teacher": a.teacher,
        "due_date": a.due_date,
        "status": a.status,
    }


def _dept_coverage(db, user_key):
    """department -> rounded avg coverage from coverage_entries."""
    rows = db.query(CoverageEntry).filter(CoverageEntry.user_key == user_key).all()
    buckets = {}
    for r in rows:
        buckets.setdefault(r.department, []).append(r.coverage)
    return {
        dept: round(sum(vals) / len(vals))
        for dept, vals in buckets.items()
    }


def _latest_dept_attendance(db, user_key):
    """department -> latest per-class present/total rolled up to %.

    Falls back to no data (None) when no class attendance recorded yet.
    """
    rows = db.query(ClassAttendance).filter(ClassAttendance.user_key == user_key).all()
    buckets = {}
    for r in rows:
        buckets.setdefault(r.class_name, []).append(r)
    dept_sums, dept_totals = {}, {}
    for cls, recs in buckets.items():
        latest = max(recs, key=lambda r: r.date)
        dept = _dept_for(cls)
        dept_sums[dept] = dept_sums.get(dept, 0) + (latest.present or 0)
        dept_totals[dept] = dept_totals.get(dept, 0) + (latest.total or 0)
    return {
        dept: round(dept_sums[dept] * 100 / dept_totals[dept], 1)
        for dept in dept_totals if dept_totals[dept] > 0
    }


def _serialize_attendance(a):
    return {
        "id": a.id,
        "class_name": a.class_name,
        "department": _dept_for(a.class_name),
        "date": a.date,
        "present": a.present,
        "total": a.total,
        "rate": round((a.present or 0) * 100 / a.total) if a.total else 0,
    }


@academic_bp.route("/api/academic/overview", methods=["GET"])
@login_required
def overview():
    db = SessionLocal()
    try:
        user_key = _db_key(db)
        students = (
            db.query(Student)
            .filter(Student.user_key == user_key)
            .order_by(Student.class_name, Student.name)
            .all()
        )
        classes = sorted({s.class_name for s in students})
        avg_attendance = round(
            sum(s.attendance or 0 for s in students) / len(students), 1
        ) if students else 0

        coverage = _dept_coverage(db, user_key)
        attendance = _latest_dept_attendance(db, user_key)
        dept_map = {d: {"name": d, "coverage": coverage.get(d, 0), "attendance": None, "risk": 0, "students": []} for d in _DEPARTMENTS}
        for s in students:
            dept = dept_map[_dept_for(s.class_name)]
            dept["students"].append(s)
        for dept in dept_map.values():
            if attendance.get(dept["name"]):
                dept["attendance"] = attendance[dept["name"]]
            elif dept["students"]:
                dept["attendance"] = round(
                    sum(s.attendance or 0 for s in dept["students"]) / len(dept["students"]), 1
                )
            dept["risk"] = sum(1 for s in dept["students"] if s.risk_level in ("High", "Medium"))
            dept.pop("students", None)
        departments = list(dept_map.values())

        assessments = db.query(Assessment).filter(
            Assessment.user_key == user_key, Assessment.status != "graded"
        ).count()

        high = sum(1 for s in students if s.risk_level == "High")

        fallback_insights = []
        math = next((d for d in departments if d["name"] == "Mathematics"), None)
        if math and math["coverage"] and math["coverage"] < 70:
            fallback_insights.append(f"Math coverage at {math['coverage']}% — check Classes 9–10 pacing.")
        if high:
            fallback_insights.append(f"{high} student(s) flagged high risk — coordinate intervention.")
        fallback_insights.append("Academic leadership intervenes early — not a gradebook.")

        insights = generate_recommendations(
            (
                f"Average attendance: {avg_attendance}%.\n"
                f"Assessments pending grading: {assessments}.\n"
                f"Curriculum coverage: "
                + ", ".join(f"{d['name']} {d['coverage']}%" for d in departments)
                + ".\n"
                f"Departments at risk: {[d['name'] for d in departments if d.get('risk', 0) > 0]}.\n"
                f"High-risk students: {high}."
            ),
            fallback=fallback_insights,
        )

        return jsonify({
            "stats": {
                "classesInSession": len(classes),
                "avgClassAttendance": avg_attendance,
                "assessmentsDue": assessments,
                "curriculumCoverage": round(
                    sum(d["coverage"] for d in departments) / len(departments), 1
                ) if departments else 0,
            },
            "insights": insights,
            "departments": departments,
            "assessments": [
                _serialize_assessment(a)
                for a in db.query(Assessment).filter(Assessment.user_key == user_key).order_by(Assessment.due_date).all()
            ],
            "coverage": [
                {"id": c.id, "department": c.department, "class_name": c.class_name, "coverage": c.coverage}
                for c in db.query(CoverageEntry).filter(CoverageEntry.user_key == user_key).order_by(CoverageEntry.department, CoverageEntry.class_name).all()
            ],
            "attendance": [
                _serialize_attendance(a)
                for a in db.query(ClassAttendance).filter(ClassAttendance.user_key == user_key).order_by(ClassAttendance.date.desc(), ClassAttendance.class_name).all()
            ],
        })
    finally:
        db.close()


@academic_bp.route("/api/academic/coverage", methods=["POST"])
@login_required
def upsert_coverage():
    data = request.json or {}
    dept = (data.get("department") or "").strip()
    cls = (data.get("class_name") or "").strip()
    cov = data.get("coverage")
    try:
        cov = int(cov)
    except (TypeError, ValueError):
        return jsonify({"error": "coverage must be an integer"}), 400
    if not dept or not cls or not (0 <= cov <= 100):
        return jsonify({"error": "department, class_name required and coverage 0-100"}), 400

    db = SessionLocal()
    try:
        user_key = _db_key(db)
        entry = db.query(CoverageEntry).filter(
            CoverageEntry.user_key == user_key,
            CoverageEntry.department == dept,
            CoverageEntry.class_name == cls,
        ).first()
        if entry:
            entry.coverage = cov
        else:
            entry = CoverageEntry(user_key=user_key, department=dept, class_name=cls, coverage=cov)
            db.add(entry)
        db.commit()
        db.refresh(entry)
        return jsonify({"success": True, "coverage": entry.coverage}), 201
    finally:
        db.close()


@academic_bp.route("/api/academic/attendance", methods=["POST"])
@login_required
def record_attendance():
    data = request.json or {}
    cls = (data.get("class_name") or "").strip()
    date = (data.get("date") or "").strip()
    try:
        present = int(data.get("present", 0))
        total = int(data.get("total", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "present and total must be integers"}), 400
    if not cls or not date or total <= 0 or not (0 <= present <= total):
        return jsonify({"error": "class_name, date required; 0 <= present <= total"}), 400

    db = SessionLocal()
    try:
        user_key = _db_key(db)
        existing = db.query(ClassAttendance).filter(
            ClassAttendance.user_key == user_key,
            ClassAttendance.class_name == cls,
            ClassAttendance.date == date,
        ).first()
        if existing:
            existing.present, existing.total = present, total
            row = existing
        else:
            row = ClassAttendance(user_key=user_key, class_name=cls, date=date,
                                  present=present, total=total)
            db.add(row)
        db.commit()
        db.refresh(row)
        return jsonify({"success": True, "attendance": _serialize_attendance(row)}), 201
    finally:
        db.close()


@academic_bp.route("/api/academic/assessments", methods=["POST"])
@login_required
def create_assessment():
    data = request.json or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400

    db = SessionLocal()
    try:
        user_key = _db_key(db)
        a = Assessment(
            user_key=user_key,
            department=(data.get("department") or "").strip(),
            class_name=(data.get("class_name") or "").strip(),
            title=title,
            teacher=(data.get("teacher") or "").strip(),
            due_date=(data.get("due_date") or "").strip(),
            status="scheduled",
        )
        db.add(a)
        db.commit()
        db.refresh(a)
        return jsonify({"success": True, "assessment": _serialize_assessment(a)}), 201
    finally:
        db.close()


@academic_bp.route("/api/academic/assessments/<assess_id>", methods=["PATCH"])
@login_required
def update_assessment(assess_id):
    data = request.json or {}
    db = SessionLocal()
    try:
        user_key = _db_key(db)
        a = db.query(Assessment).filter(
            Assessment.id == assess_id, Assessment.user_key == user_key
        ).first()
        if not a:
            return jsonify({"error": "Assessment not found"}), 404
        if data.get("status") in ("scheduled", "graded"):
            a.status = data["status"]
        if data.get("due_date"):
            a.due_date = str(data["due_date"])
        if data.get("teacher"):
            a.teacher = data["teacher"]
        db.commit()
        db.refresh(a)
        return jsonify({"success": True, "assessment": _serialize_assessment(a)})
    finally:
        db.close()
