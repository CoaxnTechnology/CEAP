from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    session,
    redirect,
    url_for,
)
from werkzeug.security import check_password_hash
from flask_wtf.csrf import generate_csrf
from app.auth_helpers import login_required
from app.config import AuthConfig
from app.services.persistence import create_user, get_user_by_email
from app.services.rag import cleanup_user_store

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/")
def index():
    if "user" in session:
        return redirect(url_for("auth.chat"))
    return render_template("index.html")


@auth_bp.route("/api/login", methods=["POST"])
def api_login():
    data = request.json or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    user = get_user_by_email(email)
    if user and check_password_hash(user["password_hash"], password):
        generate_csrf()
        session.permanent = True
        session["user"] = email
        session["username"] = email.split("@")[0]
        session.pop("user_key", None)
        return jsonify({"success": True, "username": session["username"]})

    if email in AuthConfig.USERS and AuthConfig.USERS[email] == password:
        create_user(email, password)
        generate_csrf()
        session.permanent = True
        session["user"] = email
        session["username"] = email.split("@")[0]
        session.pop("user_key", None)
        return jsonify({"success": True, "username": session["username"]})

    return jsonify({"success": False, "error": "Invalid credentials"}), 401


@auth_bp.route("/chat")
@login_required
def chat():
    return render_template("chat.html", username=session.get("username", "User"))


@auth_bp.route("/logout")
def logout():
    cleanup_user_store()
    session.clear()
    return redirect(url_for("auth.index"))
