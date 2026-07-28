"""Activity logging service and decorator."""

import time
from functools import wraps
from flask import request, session
from app.db import SessionLocal
from app.models import ActivityLog


def log_activity(action, resource_type="", resource_id="", resource_name="", details=""):
    """Log an activity to the audit trail."""
    user_email = session.get("user", "")
    if not user_email:
        return

    ip = request.remote_addr or ""
    ua = request.headers.get("User-Agent", "")[:500]

    db = SessionLocal()
    try:
        entry = ActivityLog(
            user_email=user_email,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=str(resource_name)[:255],
            details=str(details)[:1000],
            ip_address=ip,
            user_agent=ua,
            department=session.get("role", ""),
        )
        db.add(entry)
        db.commit()
    finally:
        db.close()


def audit_log(action, resource_type=None):
    """Decorator that logs an activity after the view runs successfully."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            result = fn(*args, **kwargs)

            if 200 <= result.status_code < 300:
                rid = ""
                rname = ""
                if resource_type == "document":
                    rid = request.view_args.get("doc_id", "")
                    if not rid:
                        rid = (request.json or {}).get("file_id", "")
                    rname = (request.json or {}).get("name", "")
                elif resource_type == "folder":
                    rid = request.view_args.get("folder_id", "")
                    rname = (request.json or {}).get("name", "")

                log_activity(
                    action=action,
                    resource_type=resource_type or "",
                    resource_id=rid,
                    resource_name=rname,
                )

            return result
        return wrapper
    return decorator
