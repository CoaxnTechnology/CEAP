import os
import secrets
from pathlib import Path
from flask import Blueprint, request, jsonify, session, redirect, url_for, send_from_directory
from werkzeug.security import check_password_hash
from flask_wtf.csrf import generate_csrf
from app.auth_helpers import login_required
from app.config import AuthConfig
from app.db import SessionLocal
from app.models import Role
from app.services.persistence import (
    create_user, get_user_by_email, update_user_role, get_dashboard_stats,
    list_users, create_user_with_details, update_user, delete_user,
)
from app.services.rag import cleanup_user_store
from app.services.notification_service import send_invite_email

auth_bp = Blueprint("auth", __name__)

DEFAULT_ROLES = [
    ("Principal", ["Executive", "Academic", "Students", "Admissions", "Finance", "HR", "Compliance", "Knowledge", "AI Studio", "Admin", "Tasks", "Approvals", "Calendar", "Analytics", "Workflows"], 1),
    ("HOD", ["Academic", "Students", "Knowledge", "AI Studio", "Tasks", "Calendar"], 4),
    ("Teacher", ["Academic", "Students", "AI Studio"], 28),
    ("Admin Staff", ["Compliance", "Knowledge", "Finance", "Tasks", "Approvals"], 6),
    ("Viewer", ["Executive", "Knowledge"], 12),
]

# routes.py → backend/app/modules/admin/routes.py → project root = parents[4]
_PROJECT_ROOT = Path(__file__).parents[4]
SPA_DIST = str(_PROJECT_ROOT / "frontend" / "dist")
SPA_INDEX = str(_PROJECT_ROOT / "frontend" / "dist" / "index.html")


def _serve_spa():
    if os.path.exists(SPA_INDEX):
        return send_from_directory(SPA_DIST, "index.html")
    return redirect(url_for("auth.api_me"))


@auth_bp.route("/assets/<path:filename>")
def serve_assets(filename):
    assets_dir = os.path.join(SPA_DIST, "assets")
    if os.path.exists(os.path.join(assets_dir, filename)):
        return send_from_directory(assets_dir, filename)
    return _serve_spa()


@auth_bp.route("/favicon.svg")
def serve_favicon():
    return send_from_directory(SPA_DIST, "favicon.svg")


@auth_bp.route("/")
def index():
    landing = os.path.join(SPA_DIST, "landing.html")
    if "user" not in session and os.path.exists(landing):
        return send_from_directory(SPA_DIST, "landing.html")
    if "user" in session:
        return _serve_spa()
    if os.path.exists(SPA_INDEX):
        return _serve_spa()
    return jsonify({"error": "Not found"}), 404


@auth_bp.route("/api/login", methods=["POST"])
def api_login():
    data = request.json or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    user = get_user_by_email(email)
    if user and check_password_hash(user["password_hash"], password):
        update_user_role(email)
        user = get_user_by_email(email) or user
        generate_csrf()
        session.permanent = True
        session["user"] = email
        session["username"] = email.split("@")[0]
        session["role"] = user.get("role", "user")
        session.pop("user_key", None)
        return jsonify({
            "success": True,
            "username": session["username"],
            "role": session["role"],
            "must_change_password": bool(user.get("must_change_password")),
        })

    if email in AuthConfig.USERS and AuthConfig.USERS[email] == password:
        create_user(email, password)
        update_user_role(email)
        user = get_user_by_email(email) or {"email": email, "role": "user", "password_hash": ""}
        generate_csrf()
        session.permanent = True
        session["user"] = email
        session["username"] = email.split("@")[0]
        session["role"] = user.get("role", "user")
        session.pop("user_key", None)
        return jsonify({
            "success": True,
            "username": session["username"],
            "role": session["role"],
            "must_change_password": bool(user.get("must_change_password")),
        })

    return jsonify({"success": False, "error": "Invalid credentials"}), 401


@auth_bp.route("/api/me/password", methods=["POST"])
@login_required
def api_change_own_password():
    data = request.json or {}
    current_pw = data.get("current_password", "")
    new_pw = data.get("new_password", "")
    if not new_pw or len(new_pw) < 4:
        return jsonify({"error": "New password must be at least 4 characters"}), 400
    email = session.get("user")
    user = get_user_by_email(email)
    if user and not check_password_hash(user["password_hash"], current_pw):
        return jsonify({"error": "Current password is incorrect"}), 400
    result = update_user(email, {"password": new_pw, "must_change_password": 0})
    if not result:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"success": True, "must_change_password": False})


@auth_bp.route("/dashboard")
@login_required
def dashboard():
    return _serve_spa()


@auth_bp.route("/chat")
@login_required
def chat():
    return _serve_spa()


@auth_bp.route("/ai-chat")
@login_required
def ai_chat():
    return _serve_spa()


@auth_bp.route("/repository")
@login_required
def repository():
    return _serve_spa()


@auth_bp.route("/staff")
@login_required
def staff_page():
    return _serve_spa()


@auth_bp.route("/api/staff", methods=["GET"])
@login_required
def api_list_staff():
    department = request.args.get("department", "")
    role = request.args.get("role", "")
    search = request.args.get("search", "")
    users = list_users(department=department, role=role, search=search)
    return jsonify(users)


@auth_bp.route("/api/staff", methods=["POST"])
@login_required
def api_create_staff():
    data = request.json or {}
    email = data.get("email", "").strip().lower()
    invite = bool(data.get("invite"))
    password = data.get("password", "")
    if not email:
        return jsonify({"error": "Email and password are required"}), 400
    if not invite and not password:
        return jsonify({"error": "Email and password are required"}), 400
    if invite and not password:
        password = secrets.token_urlsafe(10)
    result = create_user_with_details(
        email=email,
        password=password,
        full_name=data.get("full_name", ""),
        role=data.get("role", "user"),
        department=data.get("department", ""),
        employee_id=data.get("employee_id", ""),
        phone=data.get("phone", ""),
        qualification=data.get("qualification", ""),
        joining_date=data.get("joining_date", ""),
        subjects=data.get("subjects", ""),
        class_teacher=data.get("class_teacher", ""),
        date_of_birth=data.get("date_of_birth", ""),
        address=data.get("address", ""),
        emergency_contact=data.get("emergency_contact", ""),
        manager_email=data.get("manager_email", ""),
        must_change_password=1 if invite else 0,
    )
    if "error" in result:
        return jsonify(result), 409
    if invite:
        result["temp_password"] = password
        send_invite_email(email, data.get("role", "user"), password)
        result["email_sent"] = True
    return jsonify(result), 201


@auth_bp.route("/api/staff/<email>", methods=["PUT"])
@login_required
def api_update_staff(email):
    data = request.json or {}
    result = update_user(email, data)
    if not result:
        return jsonify({"error": "User not found"}), 404
    return jsonify(result)


@auth_bp.route("/api/staff/<email>", methods=["DELETE"])
@login_required
def api_delete_staff(email):
    ok = delete_user(email)
    if not ok:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"success": True})


@auth_bp.route("/logout")
def logout():
    cleanup_user_store()
    session.clear()
    return redirect(url_for("auth.index"))


@auth_bp.route("/api/me", methods=["GET"])
@login_required
def api_me():
    return jsonify({
        "email": session.get("user", ""),
        "username": session.get("username", ""),
        "role": session.get("role", "user"),
    })


@auth_bp.route("/api/dashboard/stats", methods=["GET"])
@login_required
def api_dashboard_stats():
    email = session.get("user", "")
    stats = get_dashboard_stats(email)
    return jsonify(stats)


@auth_bp.route("/api/roles", methods=["GET"])
@login_required
def api_list_roles():
    from app.services.rag import _user_key

    db = SessionLocal()
    try:
        user_key = _user_key()
        roles = db.query(Role).filter(Role.user_key == user_key).order_by(Role.created_at).all()
        if not roles:
            for i, (name, permissions, users) in enumerate(DEFAULT_ROLES):
                db.add(Role(user_key=user_key, name=name, permissions=permissions, users=users))
            db.commit()
            roles = db.query(Role).filter(Role.user_key == user_key).order_by(Role.created_at).all()
        return jsonify([
            {"id": r.id, "name": r.name, "permissions": r.permissions, "users": r.users}
            for r in roles
        ])
    finally:
        db.close()


@auth_bp.route("/api/roles", methods=["POST"])
@login_required
def api_create_role():
    from app.services.rag import _user_key

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Role name is required"}), 400
    db = SessionLocal()
    try:
        user_key = _user_key()
        if db.query(Role).filter(Role.user_key == user_key, Role.name == name).first():
            return jsonify({"error": "Role name already exists"}), 409
        role = Role(user_key=user_key, name=name, permissions=data.get("permissions") or [], users=int(data.get("users") or 0))
        db.add(role)
        db.commit()
        return jsonify({"id": role.id, "name": role.name, "permissions": role.permissions, "users": role.users}), 201
    finally:
        db.close()


@auth_bp.route("/api/roles/<role_id>", methods=["PUT"])
@login_required
def api_update_role(role_id):
    from app.services.rag import _user_key

    data = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        role = db.query(Role).filter(Role.user_key == _user_key(), Role.id == role_id).first()
        if not role:
            return jsonify({"error": "Role not found"}), 404
        if "name" in data:
            role.name = data["name"]
        if "permissions" in data:
            role.permissions = data["permissions"]
        db.commit()
        return jsonify({"id": role.id, "name": role.name, "permissions": role.permissions, "users": role.users})
    finally:
        db.close()


@auth_bp.route("/api/roles/<role_id>", methods=["DELETE"])
@login_required
def api_delete_role(role_id):
    from app.services.rag import _user_key

    db = SessionLocal()
    try:
        role = db.query(Role).filter(Role.user_key == _user_key(), Role.id == role_id).first()
        if not role:
            return jsonify({"error": "Role not found"}), 404
        db.delete(role)
        db.commit()
        return jsonify({"success": True})
    finally:
        db.close()


@auth_bp.route("/<path:path>")
def catch_all(path):
    if path.startswith("api/") or path.startswith("assets/"):
        return jsonify({"error": "Not found"}), 404
    return _serve_spa()
