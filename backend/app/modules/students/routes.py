import hashlib
import os

from flask import Blueprint, jsonify, request
from flask import session as _session

from app.auth_helpers import login_required
from app.db import SessionLocal
from app.models import Document, Student, StudentCommunication, User

STUDENT_UPLOADS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "uploads", "students",
)
os.makedirs(STUDENT_UPLOADS, exist_ok=True)

students_bp = Blueprint("students", __name__)


def _user_key_for(email: str) -> str:
    return hashlib.sha256(email.encode("utf-8")).hexdigest()[:32]


def _db_key(db):
    admin = db.query(User).filter(User.is_admin == 1).first()
    return _user_key_for(admin.email) if admin else _user_key_for("admin@ceap.school")


def _serialize(s, full=False):
    data = {
        "id": s.id,
        "name": s.name,
        "class": s.class_name,
        "roll": s.roll,
        "photo": "".join(w[0] for w in s.name.split())[:2].upper(),
        "gender": s.gender,
        "dob": s.dob,
        "bloodGroup": s.blood_group,
        "admissionNo": s.admission_no,
        "house": s.house,
        "riskScore": s.risk_score,
        "riskLevel": s.risk_level,
        "attendance": s.attendance,
        "feesDue": s.fees_due,
        "feesStatus": s.fees_status,
        "gpa": s.gpa,
        "parent": {
            "name": s.parent_name,
            "phone": s.parent_phone,
            "email": s.parent_email,
            "relation": s.parent_relation,
        },
        "aiSummary": s.ai_summary,
    }
    if not full:
        return data

    data.update({
        "recommendations": s.recommendations_json or [],
        "achievements": s.achievements_json or [],
        "medical": s.medical_json or {},
        "behavior": s.behavior,
        "timeline": s.timeline_json or [],
        "documents": s.documents_json or [],
    })
    return data


@students_bp.route("/api/students", methods=["GET"])
@login_required
def list_students():
    db = SessionLocal()
    try:
        user_key = _db_key(db)
        rows = (
            db.query(Student)
            .filter(Student.user_key == user_key)
            .order_by(Student.class_name, Student.name)
            .all()
        )
        return jsonify({"students": [_serialize(s) for s in rows]})
    finally:
        db.close()


@students_bp.route("/api/students/<student_id>", methods=["GET"])
@login_required
def get_student(student_id):
    db = SessionLocal()
    try:
        s = db.query(Student).filter(Student.id == student_id).first()
        if not s:
            return jsonify({"error": "Student not found"}), 404
        return jsonify(_serialize(s, full=True))
    finally:
        db.close()


DEMO_TIMELINE_S1 = [
    {"id": 1, "date": "2025-07-25", "type": "attendance", "title": "Absent – uninformed", "detail": "Class 10-A period 1–4"},
    {"id": 2, "date": "2025-07-20", "type": "fees", "title": "Fee reminder sent", "detail": "Installment 3 overdue ₹45,000"},
    {"id": 3, "date": "2025-07-10", "type": "academic", "title": "Mid-term results", "detail": "Math 58 · Science 62 · English 74"},
    {"id": 4, "date": "2025-06-28", "type": "meeting", "title": "Parent call logged", "detail": "Discussed attendance pattern"},
    {"id": 5, "date": "2025-06-01", "type": "document", "title": "Medical note uploaded", "detail": "Asthma action plan"},
    {"id": 6, "date": "2025-04-15", "type": "achievement", "title": "Science Olympiad Bronze", "detail": "Inter-school 2025"},
    {"id": 7, "date": "2020-04-01", "type": "admission", "title": "Admitted to GIS", "detail": "Class 5 entry"},
]

DEMO_TIMELINE_S2 = [
    {"id": 1, "date": "2025-07-22", "type": "achievement", "title": "Math League Gold", "detail": "State level"},
    {"id": 2, "date": "2025-07-01", "type": "fees", "title": "Annual fees cleared", "detail": "Full payment"},
    {"id": 3, "date": "2025-05-12", "type": "academic", "title": "Top of class 8-B", "detail": "GPA 9.4"},
    {"id": 4, "date": "2021-06-01", "type": "admission", "title": "Admitted to GIS", "detail": "Class 4 entry"},
]

DEMO_DOCS_S1 = [
    {"id": 1, "name": "Birth Certificate.pdf", "type": "Identity", "updated": "2020-04-01"},
    {"id": 2, "name": "Aadhaar.pdf", "type": "Identity", "updated": "2023-01-12"},
    {"id": 3, "name": "Report Card Term 1.pdf", "type": "Academic", "updated": "2025-07-10"},
    {"id": 4, "name": "Fee Receipt Apr.pdf", "type": "Finance", "updated": "2025-04-05"},
    {"id": 5, "name": "Asthma Action Plan.pdf", "type": "Medical", "updated": "2025-06-01"},
]


DEMO_STUDENTS = [
    {
        "name": "Aarav Mehta", "class_name": "10-A", "roll": "10A-14", "gender": "M", "dob": "2010-03-12",
        "house": "Blue", "risk_score": 78, "risk_level": "High", "attendance": 82, "fees_due": 45000,
        "fees_status": "Overdue", "gpa": 6.8, "parent_name": "Rohit Mehta", "parent_phone": "+91 98765 41001",
        "parent_email": "rohit.mehta@email.com", "parent_relation": "Father", "blood_group": "B+",
        "ai_summary": "Declining attendance over 6 weeks and two overdue fee installments. Recommend counselor check-in and parent finance conversation.",
        "behavior": "Generally cooperative; 1 late arrival warning this term",
        "recommendations_json": ["Schedule counselor session this week", "Send fee reminder with flexible plan option", "Math remedial support via Academic AI"],
        "achievements_json": ["Science Olympiad Bronze 2024", "Inter-house Debate Finalist"],
        "medical_json": {"allergies": "None", "conditions": "Mild asthma", "lastCheckup": "2025-01-15"},
        "timeline_json": DEMO_TIMELINE_S1,
        "documents_json": DEMO_DOCS_S1,
    },
    {
        "name": "Ananya Krishnan", "class_name": "8-B", "roll": "8B-07", "gender": "F", "dob": "2012-07-22",
        "house": "Green", "risk_score": 18, "risk_level": "Low", "attendance": 98, "fees_due": 0,
        "fees_status": "Cleared", "gpa": 9.4, "parent_name": "Lakshmi Krishnan", "parent_phone": "+91 98765 41022",
        "parent_email": "lakshmi.k@email.com", "parent_relation": "Mother", "blood_group": "O+",
        "ai_summary": "High-performing student with excellent attendance and cleared fees. Strong in STEM.",
        "behavior": "Exemplary", "recommendations_json": ["Nominate for Student Council", "STEM enrichment track"],
        "achievements_json": ["Gold – Math League", "Perfect attendance 2024-25"],
        "medical_json": {"allergies": "Peanuts", "conditions": "None", "lastCheckup": "2025-02-01"},
        "timeline_json": DEMO_TIMELINE_S2,
        "documents_json": [
            {"id": 1, "name": "Birth Certificate.pdf", "type": "Identity", "updated": "2021-06-01"},
            {"id": 2, "name": "Report Card Term 1.pdf", "type": "Academic", "updated": "2025-07-08"},
            {"id": 3, "name": "Allergy Note.pdf", "type": "Medical", "updated": "2025-02-01"},
        ],
    },
    {
        "name": "Vihaan Patel", "class_name": "12-C", "roll": "12C-03", "gender": "M", "dob": "2008-11-05",
        "house": "Red", "risk_score": 42, "risk_level": "Medium", "attendance": 91, "fees_due": 15000,
        "fees_status": "Partial", "gpa": 8.1, "parent_name": "Meera Patel", "parent_phone": "+91 98765 41033",
        "parent_email": "meera.patel@email.com", "parent_relation": "Mother", "blood_group": "A+",
        "ai_summary": "Board year student with solid academics. One pending fee installment. Monitor stress during pre-boards.",
        "behavior": "Positive peer influence",
        "recommendations_json": ["Confirm board exam registration", "Offer wellness workshop"],
        "achievements_json": ["Football Captain", "Service Learning Award"],
        "medical_json": {"allergies": "None", "conditions": "None", "lastCheckup": "2024-11-20"},
    },
    {
        "name": "Sara Khan", "class_name": "5-A", "roll": "5A-19", "gender": "F", "dob": "2015-01-30",
        "house": "Yellow", "risk_score": 25, "risk_level": "Low", "attendance": 95, "fees_due": 0,
        "fees_status": "Cleared", "gpa": 8.9, "parent_name": "Imran Khan", "parent_phone": "+91 98765 41044",
        "parent_email": "imran.k@email.com", "parent_relation": "Father", "blood_group": "AB+",
        "ai_summary": "Well-adjusted primary student. Strong reading scores. No operational risks.",
        "behavior": "Cheerful and engaged", "recommendations_json": ["Reading club invitation"],
        "achievements_json": ["Art Exhibition Winner"],
        "medical_json": {"allergies": "Dust", "conditions": "None", "lastCheckup": "2025-03-10"},
    },
    {
        "name": "Kabir Sharma", "class_name": "9-A", "roll": "9A-11", "gender": "M", "dob": "2011-09-18",
        "house": "Blue", "risk_score": 65, "risk_level": "High", "attendance": 79, "fees_due": 28000,
        "fees_status": "Overdue", "gpa": 6.2, "parent_name": "Neha Sharma", "parent_phone": "+91 98765 41055",
        "parent_email": "neha.s@email.com", "parent_relation": "Mother", "blood_group": "B-",
        "ai_summary": "Elevated risk: attendance + fees + academic dip. Parent meeting overdue since May.",
        "behavior": "2 disciplinary notes this term",
        "recommendations_json": ["Urgent parent conference", "Attendance intervention plan", "Fee counseling"],
        "achievements_json": [],
        "medical_json": {"allergies": "None", "conditions": "None", "lastCheckup": "2024-08-12"},
    },
]


def seed_students_if_empty():
    db = SessionLocal()
    try:
        user_key = _db_key(db)
        if db.query(Student).filter(Student.user_key == user_key).count() < 5:
            existing = {s.name for s in db.query(Student).filter(Student.user_key == user_key).all()}
            for row in DEMO_STUDENTS:
                if row["name"] not in existing:
                    db.add(Student(user_key=user_key, **row))
            db.commit()
    finally:
        db.close()


SEED_COMMUNICATIONS = [
    {"student_id": "s1", "channel": "call", "subject": "Parent call — attendance", "body": "Discussed declining attendance pattern over 6 weeks. Parent agreed to monitor daily check-ins.", "author": "Meera Nair"},
    {"student_id": "s1", "channel": "sms", "subject": "Fee reminder", "body": "Installment 3 overdue (₹45,000). Flexible payment plan offered.", "author": "Finance AI"},
    {"student_id": "s1", "channel": "email", "subject": "Mid-term results shared", "body": "Math 58 · Science 62 · English 74. Results uploaded to parent portal.", "author": "Academic AI"},
]


def seed_communications_if_empty():
    db = SessionLocal()
    try:
        user_key = _db_key(db)
        if db.query(StudentCommunication).count() == 0:
            for row in SEED_COMMUNICATIONS:
                db.add(StudentCommunication(user_key=user_key, **row))
            db.commit()
    finally:
        db.close()


@students_bp.route("/api/students/<student_id>/communications", methods=["GET"])
@login_required
def list_communications(student_id):
    db = SessionLocal()
    try:
        user_key = _db_key(db)
        rows = (
            db.query(StudentCommunication)
            .filter(StudentCommunication.student_id == student_id, StudentCommunication.user_key == user_key)
            .order_by(StudentCommunication.created_at.desc())
            .all()
        )
        return jsonify({"communications": [
            {
                "id": c.id,
                "channel": c.channel,
                "subject": c.subject,
                "body": c.body,
                "author": c.author,
                "createdAt": c.created_at,
            }
            for c in rows
        ]})
    finally:
        db.close()


@students_bp.route("/api/students/<student_id>/communications", methods=["POST"])
@login_required
def create_communication(student_id):
    db = SessionLocal()
    try:
        user_key = _db_key(db)
        body = request.get_json(force=True)
        channel = (body.get("channel") or "call").strip()
        subject = (body.get("subject") or "").strip()
        if not subject:
            return jsonify({"error": "subject is required"}), 400
        c = StudentCommunication(
            user_key=user_key,
            student_id=student_id,
            channel=channel,
            subject=subject,
            body=body.get("body", ""),
            author=body.get("author") or _session.get("user", user_key),
        )
        db.add(c)
        db.commit()
        db.refresh(c)
        return jsonify({
            "id": c.id,
            "channel": c.channel,
            "subject": c.subject,
            "body": c.body,
            "author": c.author,
            "createdAt": c.created_at,
        }), 201
    finally:
        db.close()


SEED_DOCUMENTS = [
    {"student_id": "s1", "name": "Birth Certificate.pdf", "type": "Identity", "size": 245000},
    {"student_id": "s1", "name": "Aadhaar.pdf", "type": "Identity", "size": 312000},
    {"student_id": "s1", "name": "Report Card Term 1.pdf", "type": "Academic", "size": 189000},
    {"student_id": "s1", "name": "Fee Receipt Apr.pdf", "type": "Finance", "size": 156000},
    {"student_id": "s1", "name": "Asthma Action Plan.pdf", "type": "Medical", "size": 98000},
    {"student_id": "s2", "name": "Birth Certificate.pdf", "type": "Identity", "size": 230000},
    {"student_id": "s2", "name": "Report Card Term 1.pdf", "type": "Academic", "size": 175000},
    {"student_id": "s2", "name": "Allergy Note.pdf", "type": "Medical", "size": 45000},
]


def seed_documents_if_empty():
    from app.services.rag import register_and_index_for_user

    db = SessionLocal()
    try:
        user_key = _db_key(db)
        existing = {d.name for d in db.query(Document).filter(Document.user_key == user_key).all()}
        for row in SEED_DOCUMENTS:
            if row["name"] in existing:
                continue
            student_dir = os.path.join(STUDENT_UPLOADS, row["student_id"])
            os.makedirs(student_dir, exist_ok=True)
            file_path = os.path.join(student_dir, row["name"])
            if not os.path.exists(file_path):
                with open(file_path, "wb") as f:
                    f.write(b"%PDF-1.4\n% Demo placeholder for " + row["name"].encode() + b"\n")
            text = f"{row['name']} — demo document for student {row['student_id']}. " + (
                "Record includes this " + row["type"].lower() + " document on file for reference."
            )
            try:
                entry = register_and_index_for_user(
                    user_key=user_key,
                    name=row["name"],
                    text=text,
                    size=row["size"],
                    source="local",
                    source_ref=row["student_id"],
                    file_path=file_path,
                )
                doc = db.query(Document).filter(Document.file_id == entry["file_id"]).first()
                if doc:
                    doc.student_id = row["student_id"]
                    doc.tags = [row["type"]]
            except Exception:
                continue

        staff_dir = os.path.join(STUDENT_UPLOADS, "staff")
        os.makedirs(staff_dir, exist_ok=True)
        leave_policy_name = "Staff Leave Policy.txt"
        if leave_policy_name not in existing:
            leave_text = (
                "Staff Leave Policy\n"
                "Leave requests are submitted through the HR portal and routed for approval.\n"
                "Approval chain: leave routes to the department head for the employee's department. "
                "If no department head is configured, the employee's manager approves. "
                "Otherwise the school admin (Principal) approves.\n"
                "Heads of Department (HODs) report to the Principal; HOD leave is approved by the school admin (Principal). "
                "Staff cannot approve their own leave.\n"
                "Leave types: Annual 20 days, Earned 20 days, Sick 12 days, Personal/Casual 5 days, "
                "Maternity 180 days, Paternity 15 days."
            )
            leave_policy_path = os.path.join(staff_dir, leave_policy_name)
            if not os.path.exists(leave_policy_path):
                with open(leave_policy_path, "w", encoding="utf-8") as f:
                    f.write(leave_text)
            try:
                register_and_index_for_user(
                    user_key=user_key,
                    name=leave_policy_name,
                    text=leave_text,
                    size=len(leave_text),
                    source="local",
                    source_ref="staff",
                    file_path=leave_policy_path,
                )
            except Exception:
                pass
        db.commit()
    finally:
        db.close()