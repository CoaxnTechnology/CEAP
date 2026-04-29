from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    session,
    redirect,
    url_for,
)
from app.auth_helpers import login_required
from app.config import AuthConfig
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
    if AuthConfig.USERS.get(email) == password:
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
