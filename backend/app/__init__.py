"""CEAP for Schools — Flask application package."""

import os
import warnings
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from flask_cors import CORS
from app.config import Config
from app.db import init_db as init_sqlalchemy_db
from app.services.persistence import init_users_from_config, init_school_data
from app.services.storage import init_storage

csrf = CSRFProtect()


def create_app():
    warnings.filterwarnings("ignore", message="resource_tracker: There appear to be .* leaked semaphore objects")
    app = Flask(__name__, static_folder=None)
    app.secret_key = Config.SECRET_KEY or "ceap-dev-secret-key"
    app.config['SESSION_PERMANENT'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = 86400
    app.config['WTF_CSRF_TIME_LIMIT'] = None

    CORS(app, supports_credentials=True)

    from app.modules.admin.routes import auth_bp
    from app.modules.documents.routes import files_bp
    from app.modules.cloud.routes import onedrive_bp
    from app.modules.ai.routes import chat_bp
    from app.modules.documents.repository_routes import repo_bp
    from app.modules.onboarding.routes import onboarding_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(onedrive_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(repo_bp)
    app.register_blueprint(onboarding_bp)

    with app.app_context():
        init_sqlalchemy_db()
        init_storage()
        init_users_from_config()
        init_school_data()

    csrf.init_app(app)
    csrf.exempt(auth_bp)
    csrf.exempt(chat_bp)
    csrf.exempt(files_bp)
    csrf.exempt(onedrive_bp)
    csrf.exempt(repo_bp)
    csrf.exempt(onboarding_bp)

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logs_dir = os.path.join(os.path.dirname(base_dir), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_path = os.path.join(logs_dir, "ceap.log")

    if not any(
        isinstance(h, RotatingFileHandler) and getattr(h, "baseFilename", "") == log_path
        for h in app.logger.handlers
    ):
        handler = RotatingFileHandler(log_path, maxBytes=2_000_000, backupCount=3)
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
        )
        handler.setLevel(logging.INFO)
        app.logger.addHandler(handler)

    app.logger.setLevel(logging.INFO)
    app.logger.info("Application initialized")

    return app