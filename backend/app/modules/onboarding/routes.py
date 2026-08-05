"""Onboarding API - School setup, departments, admin, OneDrive, invitations."""

import time
import uuid
import secrets
from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash
from sqlalchemy import func

from app.auth_helpers import login_required
from app.db import SessionLocal
from app.models import School, Department, User, DocumentCategory

onboarding_bp = Blueprint("onboarding", __name__, url_prefix="/api/onboarding")


# ─── Default Roles (hardcoded) ───
DEFAULT_ROLES = [
    {"name": "Principal", "description": "Full access to all modules, school settings, and user management"},
    {"name": "HOD", "description": "Department head - manage department documents, staff, and compliance"},
    {"name": "Teacher", "description": "Access academic documents, student records, and AI chat for teaching"},
    {"name": "Admin Staff", "description": "Administrative operations - finance, HR, transport, general admin"},
    {"name": "Viewer", "description": "Read-only access to assigned documents and dashboards"},
]


# ─── Default Departments (matching frontend) ───
DEFAULT_DEPARTMENTS = [
    {"id": "academic", "name": "Academic", "code": "ACAD"},
    {"id": "hr", "name": "HR", "code": "HR"},
    {"id": "finance", "name": "Finance", "code": "FIN"},
    {"id": "admin", "name": "Admin", "code": "ADMIN"},
    {"id": "transport", "name": "Transport", "code": "TRANS"},
    {"id": "it", "name": "IT", "code": "IT"},
    {"id": "sports", "name": "Sports", "code": "SPORT"},
    {"id": "library", "name": "Library", "code": "LIB"},
]


# ─── Helper: Create default document categories for school ───
def _create_default_categories(db, school_id: str):
    """Create standard school document categories."""
    categories = [
        {"name": "Circulars & Notices", "icon": "megaphone", "children": [
            {"name": "General Circulars", "icon": "file-text"},
            {"name": "Holiday Notices", "icon": "calendar-days"},
            {"name": "Event Notifications", "icon": "calendar-check"},
        ]},
        {"name": "Student Records", "icon": "users", "children": [
            {"name": "Admission Forms", "icon": "file-plus"},
            {"name": "Academic Records", "icon": "graduation-cap"},
            {"name": "Transfer Certificates", "icon": "file-up"},
            {"name": "Student Reports", "icon": "clipboard-list"},
        ]},
        {"name": "Staff Records", "icon": "id-card", "children": [
            {"name": "Appointment Letters", "icon": "file-text"},
            {"name": "Salary Documents", "icon": "wallet"},
            {"name": "Leave Records", "icon": "calendar"},
        ]},
        {"name": "Finance & Accounts", "icon": "landmark", "children": [
            {"name": "Fee Structure", "icon": "file-text"},
            {"name": "Fee Receipts", "icon": "receipt"},
            {"name": "Vendor Invoices", "icon": "file-invoice"},
            {"name": "Audit Reports", "icon": "file-search"},
        ]},
        {"name": "Government & Compliance", "icon": "shield", "children": [
            {"name": "Inspection Reports", "icon": "clipboard-check"},
            {"name": "Affiliation Documents", "icon": "file-check"},
            {"name": "Safety Certificates", "icon": "badge-check"},
        ]},
        {"name": "Academic", "icon": "book-open", "children": [
            {"name": "Curriculum", "icon": "book"},
            {"name": "Examination Records", "icon": "scroll-text"},
            {"name": "Timetables", "icon": "calendar-range"},
        ]},
        {"name": "Meeting Minutes", "icon": "file-clock", "children": []},
        {"name": "Policies & Handbooks", "icon": "book-marked", "children": []},
    ]

    for cat_data in categories:
        parent = DocumentCategory(
            school_id=school_id,
            name=cat_data["name"],
            icon=cat_data.get("icon", "folder"),
        )
        db.add(parent)
        db.flush()
        for child_data in cat_data.get("children", []):
            child = DocumentCategory(
                school_id=school_id,
                name=child_data["name"],
                icon=child_data.get("icon", "folder"),
                parent_id=parent.id,
            )
            db.add(child)


@onboarding_bp.route("/signup", methods=["POST"])
def signup():
    """Create a pending user account. User logs in immediately after."""
    data = request.json or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not name or not email or not password:
        return jsonify({"error": "Name, email, and password are required"}), 400
    if len(password) < 4:
        return jsonify({"error": "Password must be at least 4 characters"}), 400

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            return jsonify({"error": "Email already registered"}), 409

        user = User(
            email=email,
            full_name=name,
            password_hash=generate_password_hash(password),
            role="Principal",
            is_admin=1,
            status="pending",
            created_at=time.time(),
        )
        db.add(user)
        db.commit()

        session["user"] = email
        session["username"] = name.split()[0] if name.split() else name
        session["role"] = "Principal"

        return jsonify({
            "success": True,
            "username": session["username"],
            "role": "Principal",
            "email": email,
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@onboarding_bp.route("/status", methods=["GET"])
def onboarding_status():
    """Check if the current session user has completed onboarding."""
    user_email = session.get("user")
    if not user_email:
        return jsonify({
            "authenticated": False,
            "onboarding_complete": False,
            "school": None,
        })

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == user_email).first()
        if user and user.school_id:
            school = db.query(School).filter(School.id == user.school_id).first()
            return jsonify({
                "authenticated": True,
                "onboarding_complete": True,
                "user": {"full_name": user.full_name, "role": user.role},
                "school": {
                    "id": school.id,
                    "name": school.name,
                    "code": school.code,
                } if school else None,
            })
        return jsonify({
            "authenticated": True,
            "onboarding_complete": False,
            "user": {"full_name": user.full_name, "role": user.role} if user else None,
            "school": None,
        })
    finally:
        db.close()


@onboarding_bp.route("/school", methods=["POST"])
@login_required
def create_school():
    """
    Complete school onboarding for the logged-in user:
    - Create school
    - Create enabled departments
    - Update user with school_id and role
    - Create default document categories
    - Create pending invitation records
    """
    user_email = session.get("user")
    data = request.json or {}
    school_data = data.get("school", {})
    departments = data.get("departments", [])
    admin = data.get("admin", {})
    invitations = data.get("invitations", [])
    connectors = data.get("connectors", [])

    if not school_data.get("name") or not school_data.get("city") or not school_data.get("state"):
        return jsonify({"error": "School name, city, and state are required"}), 400

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            return jsonify({"error": "User not found"}), 404
        if user.school_id:
            return jsonify({"error": "School already exists for this user"}), 400

        school = School(
            name=school_data.get("name", "").strip(),
            code=school_data.get("code", "").strip() or uuid.uuid4().hex[:8].upper(),
            address=school_data.get("address", "").strip(),
            phone=school_data.get("phone", "").strip(),
            email=school_data.get("email", "").strip(),
            website=school_data.get("website", "").strip(),
            status="active",
            created_at=time.time(),
        )
        existing = db.query(School).filter(School.code == school.code).first()
        if existing:
            return jsonify({"error": f'School code "{school.code}" is already in use. Please choose a different code.'}), 400
        db.add(school)
        db.flush()

        dept_map = {}
        for dept_key in departments:
            if dept_key in [d["id"] for d in DEFAULT_DEPARTMENTS]:
                dept_info = next(d for d in DEFAULT_DEPARTMENTS if d["id"] == dept_key)
                dept = Department(
                    school_id=school.id,
                    name=dept_info["name"],
                    code=dept_info["code"],
                )
                db.add(dept)
                db.flush()
                dept_map[dept_key] = dept.id

        user.school_id = school.id
        user.status = "active"
        if admin.get("role"):
            user.role = admin.get("role")
            session["role"] = admin.get("role")
        if admin.get("name"):
            user.full_name = admin.get("name")

        _create_default_categories(db, school.id)

        for invite in invitations:
            invite_email = invite.get("email", "").strip().lower()
            role = invite.get("role", "Teacher")
            dept = invite.get("department", "")
            if invite_email and invite_email != user_email:
                existing = db.query(User).filter(User.email == invite_email).first()
                if not existing:
                    temp_password = secrets.token_urlsafe(10)
                    invited_user = User(
                        email=invite_email,
                        full_name=invite_email.split("@")[0].replace(".", " ").replace("_", " ").title(),
                        password_hash=generate_password_hash(temp_password),
                        role=role,
                        department=dept,
                        school_id=school.id,
                        invited_by=user_email,
                        invited_at=time.time(),
                        status="invited",
                        created_at=time.time(),
                    )
                    db.add(invited_user)

        od_connected = any(c.get("id") == "onedrive" and c.get("status") == "Connected"
                          for c in connectors)

        db.commit()

        return jsonify({
            "success": True,
            "school": {
                "id": school.id,
                "name": school.name,
                "code": school.code,
            },
            "departments_created": list(dept_map.keys()),
            "invitations_sent": len(invitations),
            "onedrive_connected": od_connected,
        }), 201

    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@onboarding_bp.route("/invite", methods=["POST"])
@login_required
def create_invitations():
    """Create pending invitation records for team members."""
    data = request.json or {}
    invitations = data.get("invitations", [])
    school_id = data.get("school_id")

    if not invitations:
        return jsonify({"error": "No invitations provided"}), 400

    db = SessionLocal()
    try:
        created = []
        for invite in invitations:
            email = invite.get("email", "").strip().lower()
            role = invite.get("role", "Teacher")
            department = invite.get("department", "")
            
            if not email:
                continue
            
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                created.append({"email": email, "status": "exists"})
                continue

            temp_password = secrets.token_urlsafe(10)
            user = User(
                email=email,
                full_name=email.split("@")[0].replace(".", " ").replace("_", " ").title(),
                password_hash=generate_password_hash(temp_password),
                role=role,
                department=department,
                school_id=school_id,
                invited_by=session.get("user"),
                invited_at=time.time(),
                status="invited",
                created_at=time.time(),
            )
            db.add(user)
            created.append({"email": email, "role": role, "status": "invited"})

        db.commit()
        return jsonify({"success": True, "invitations": created})
    finally:
        db.close()


@onboarding_bp.route("/departments", methods=["GET"])
def list_department_templates():
    """Get default department templates."""
    return jsonify({"departments": DEFAULT_DEPARTMENTS})


@onboarding_bp.route("/roles", methods=["GET"])
def list_role_templates():
    """Get default role templates."""
    return jsonify({"roles": DEFAULT_ROLES})


@onboarding_bp.route("/connectors/onedrive", methods=["GET"])
def onedrive_status():
    """Check OneDrive connection status from session."""
    od_token = session.get("od_token")
    connected = bool(od_token)
    return jsonify({
        "id": "onedrive",
        "name": "OneDrive",
        "description": "Microsoft 365 school tenant documents",
        "status": "Connected" if connected else "Not Connected",
        "connected": connected,
        "lastSync": None,
    })


@onboarding_bp.route("/connectors/onedrive/connect", methods=["POST"])
@login_required
def onedrive_connect():
    """Redirect to real OneDrive OAuth flow."""
    return jsonify({
        "success": True,
        "auth_url": "/onedrive/connect",
    })


@onboarding_bp.route("/connectors/onedrive/disconnect", methods=["POST"])
@login_required
def onedrive_disconnect():
    """Disconnect OneDrive."""
    return jsonify({
        "success": True,
        "message": "OneDrive disconnected",
    })


@onboarding_bp.route("/invite/<email>/resend", methods=["POST"])
@login_required
def resend_invitation(email):
    """Resend invitation to a pending user."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(
            User.email == email.lower(),
            User.status == "invited"
        ).first()
        if not user:
            return jsonify({"error": "Invitation not found"}), 404
        
        # Generate new temp password
        new_password = secrets.token_urlsafe(10)
        user.password_hash = generate_password_hash(new_password)
        user.invited_at = time.time()
        db.commit()
        
        return jsonify({
            "success": True,
            "message": "Invitation resent",
            "temp_password": new_password,  # In real app, send via email
        })
    finally:
        db.close()