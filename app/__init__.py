"""DocuMind — Flask application package."""

import os
import warnings
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from app.config import Config
from app.db import init_db as init_sqlalchemy_db

csrf = CSRFProtect()


def create_app():
    warnings.filterwarnings("ignore", message="resource_tracker: There appear to be .* leaked semaphore objects")
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app = Flask(
        __name__,
        template_folder=os.path.join(base_dir, "templates"),
        static_folder=os.path.join(base_dir, "static"),
    )
    app.secret_key = Config.SECRET_KEY or "documind-dev-secret-key"
    app.config['SESSION_PERMANENT'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = 86400
    app.config['WTF_CSRF_TIME_LIMIT'] = None

    from app.routes.auth import auth_bp
    from app.routes.files import files_bp
    from app.routes.onedrive import onedrive_bp
    from app.routes.chat import chat_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(onedrive_bp)
    app.register_blueprint(chat_bp)

    with app.app_context():
        init_sqlalchemy_db()

    csrf.init_app(app)
    csrf.exempt(auth_bp)

    logs_dir = os.path.join(base_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_path = os.path.join(logs_dir, "documind.log")

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
