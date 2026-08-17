"""Layer 1 + Layer 2 — build session context and domain snapshots for chat.

Session context is small and always injected. Domain snapshots reuse the
existing overview endpoints so we don't duplicate SQL.
"""
from app.db import SessionLocal
from app.models import Department, School, User


def get_session_context(user_email: str) -> str:
    """Who the user is + their school, as a short string block."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            return ""
        parts = [
            f"User: {user.full_name} ({user.email})",
            f"Role: {user.role or 'user'}",
        ]
        if user.department:
            parts.append(f"Department: {user.department}")
        if user.manager_email:
            parts.append(f"Manager: {user.manager_email}")

        school = None
        if user.school_id:
            school = db.query(School).filter(School.id == user.school_id).first()
        if school:
            parts.append(f"School: {school.name}")
            if school.academic_year:
                parts.append(f"Academic year: {school.academic_year}")
            if school.board:
                parts.append(f"Board: {school.board}")

        dept = None
        if user.school_id and user.department:
            dept = (
                db.query(Department)
                .filter(
                    Department.school_id == user.school_id,
                    Department.name == user.department,
                )
                .first()
            )
        if dept and dept.head_email:
            parts.append(f"Department head: {dept.head_email}")

        return "\n".join(parts)
    finally:
        db.close()


_SNAPSHOT_SOURCES = {
    "hr": ("app.modules.hr.routes", "overview"),
    "finance": ("app.modules.finance.routes", "overview"),
    "admissions": ("app.modules.admissions.routes", "overview"),
    "executive": ("app.modules.executive.routes", "overview"),
}


def _fetch_snapshot(domain: str) -> dict | None:
    """Call an existing overview route and return its JSON payload."""
    module_path, fn_name = _SNAPSHOT_SOURCES[domain]
    try:
        module = __import__(module_path, fromlist=[fn_name])
        view = getattr(module, fn_name)
        resp = view()
        return resp.get_json() if hasattr(resp, "get_json") else None
    except Exception:  # noqa: BLE001  # ponytail: snapshot is best-effort, never breaks chat
        return None


def build_context(user_email: str, domain: str, question: str) -> str:
    """Assemble session context + a compact domain snapshot (if routable)."""
    block = get_session_context(user_email)
    if domain in _SNAPSHOT_SOURCES:
        snapshot = _fetch_snapshot(domain)
        if snapshot:
            import json

            block += f"\n\nLIVE {domain.upper()} SNAPSHOT:\n" + json.dumps(
                snapshot, default=str
            )[:4000]
    return block