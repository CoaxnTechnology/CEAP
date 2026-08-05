"""CEAP for Schools — Flask application package."""

import logging
import os
import warnings
from logging.handlers import RotatingFileHandler

from flask import Flask
from flask_cors import CORS
from flask_wtf.csrf import CSRFProtect

from app.config import Config
from app.db import init_db as init_sqlalchemy_db
from app.services.persistence import init_users_from_config
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

    from app.modules.academic.routes import academic_bp
    from app.modules.admin.routes import auth_bp
    from app.modules.admissions.routes import admissions_bp
    from app.modules.ai.routes import chat_bp
    from app.modules.ai.studio_routes import studio_bp
    from app.modules.calendar.routes import calendar_bp
    from app.modules.cloud.routes import onedrive_bp
    from app.modules.compliance.routes import compliance_bp
    from app.modules.documents.repository_routes import repo_bp
    from app.modules.documents.routes import files_bp
    from app.modules.executive.routes import executive_bp
    from app.modules.finance.routes import finance_bp
    from app.modules.hr.routes import hr_bp
    from app.modules.knowledge.routes import knowledge_bp
    from app.modules.onboarding.routes import onboarding_bp
    from app.modules.operations.routes import ops_bp
    from app.modules.students.routes import students_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(onedrive_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(repo_bp)
    app.register_blueprint(studio_bp)
    app.register_blueprint(onboarding_bp)
    app.register_blueprint(knowledge_bp)
    app.register_blueprint(compliance_bp)
    app.register_blueprint(hr_bp)
    app.register_blueprint(finance_bp)
    app.register_blueprint(admissions_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(calendar_bp)
    app.register_blueprint(academic_bp)
    app.register_blueprint(executive_bp)
    app.register_blueprint(ops_bp)

    with app.app_context():
        init_sqlalchemy_db()
        init_storage()
        init_users_from_config()
        from app.modules.ai.studio_routes import seed_templates_if_empty
        seed_templates_if_empty()
        from app.modules.hr.routes import seed_hr_if_empty
        seed_hr_if_empty()
        from app.modules.finance.routes import seed_finance_if_empty
        seed_finance_if_empty()
        from app.modules.admissions.routes import seed_admissions_if_empty
        seed_admissions_if_empty()
        from app.modules.students.routes import (
            seed_communications_if_empty,
            seed_documents_if_empty,
            seed_students_if_empty,
        )
        seed_students_if_empty()
        seed_communications_if_empty()
        seed_documents_if_empty()
        from app.modules.calendar.routes import seed_calendar_if_empty
        seed_calendar_if_empty()
        from app.modules.academic.routes import seed_academic_if_empty
        seed_academic_if_empty()
        from app.modules.executive.routes import seed_executive_if_empty
        seed_executive_if_empty()
        from app.modules.operations.routes import seed_tasks_if_empty
        seed_tasks_if_empty()

    csrf.init_app(app)
    csrf.exempt(auth_bp)
    csrf.exempt(chat_bp)
    csrf.exempt(files_bp)
    csrf.exempt(onedrive_bp)
    csrf.exempt(repo_bp)
    csrf.exempt(studio_bp)
    csrf.exempt(onboarding_bp)
    csrf.exempt(knowledge_bp)
    csrf.exempt(compliance_bp)
    csrf.exempt(hr_bp)
    csrf.exempt(finance_bp)
    csrf.exempt(admissions_bp)
    csrf.exempt(students_bp)
    csrf.exempt(calendar_bp)
    csrf.exempt(academic_bp)
    csrf.exempt(executive_bp)
    csrf.exempt(ops_bp)

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