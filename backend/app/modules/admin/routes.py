import os
from pathlib import Path
from flask import Blueprint, request, jsonify, session, redirect, url_for, send_from_directory
from werkzeug.security import check_password_hash
from flask_wtf.csrf import generate_csrf
from app.auth_helpers import login_required
from app.config import AuthConfig
from app.services.persistence import (
    create_user, get_user_by_email, update_user_role, get_dashboard_stats,
    list_users, create_user_with_details, update_user, delete_user,
)
from app.services.rag import cleanup_user_store

auth_bp = Blueprint("auth", __name__)

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
        return jsonify({"success": True, "username": session["username"], "role": session["role"]})

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
        return jsonify({"success": True, "username": session["username"], "role": session["role"]})

    return jsonify({"success": False, "error": "Invalid credentials"}), 401


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
    password = data.get("password", "")
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
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
    )
    if "error" in result:
        return jsonify(result), 409
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


@auth_bp.route("/<path:path>")
def catch_all(path):
    if path.startswith("api/") or path.startswith("assets/"):
        return jsonify({"error": "Not found"}), 404
    return _serve_spa()
