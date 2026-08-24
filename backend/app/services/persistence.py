import json
import time
import uuid

from werkzeug.security import generate_password_hash
from sqlalchemy import func
from flask import session

from app.db import SessionLocal
from app.models import (
    Document, ChatSession, ChatMessage, User, FileChunk,
    School, Department, DocumentCategory, RepositoryDocument,
)


DEFAULT_CHAT_TITLE = "New Chat"


def _to_dict(model_instance, columns=None):
    if model_instance is None:
        return None
    if columns is None:
        columns = [c.name for c in model_instance.__table__.columns]
    return {c: getattr(model_instance, c) for c in columns}


def _row_to_session(row) -> dict:
    if row is None:
        return None
    return {
        "session_id": row.session_id,
        "title": row.title,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "message_count": getattr(row, "message_count", 0),
    }


def init_db():
    pass


def init_users_from_config():
    from app.config import AuthConfig
    db = SessionLocal()
    try:
        for email, password in AuthConfig.USERS.items():
            email_norm = email.strip().lower()
            existing = db.query(User).filter(User.email == email_norm).first()
            if existing:
                continue
            full_name = email_norm.split("@")[0]
            pw_hash = generate_password_hash(password)
            now = time.time()
            user = User(
                email=email_norm,
                full_name=full_name,
                password_hash=pw_hash,
                created_at=now,
            )
            db.add(user)
        db.commit()
    finally:
        db.close()


def get_user_by_email(email: str) -> dict | None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email.strip().lower()).first()
        return _to_dict(user) if user else None
    finally:
        db.close()


def update_user_role(email: str) -> str:
    role_map = {
        "admin": "admin",
        "hr": "hr",
        "accounting": "accounting",
    }
    email_norm = email.strip().lower()
    prefix = email_norm.split("@")[0]
    role = role_map.get(prefix, "user")
    db = SessionLocal()
    try:
        db.query(User).filter(User.email == email_norm).update({"role": role})
        db.commit()
    finally:
        db.close()
    return role


def create_user(email: str, password: str) -> dict:
    email_norm = email.strip().lower()
    pw_hash = generate_password_hash(password)
    now = time.time()
    full_name = email_norm.split("@")[0]
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email_norm).first()
        if existing:
            return {"email": email_norm, "created_at": existing.created_at}
        user = User(
            email=email_norm,
            full_name=full_name,
            password_hash=pw_hash,
            created_at=now,
        )
        db.add(user)
        db.commit()
        return {"email": email_norm, "created_at": now}
    finally:
        db.close()


def create_user_with_details(
    email: str, password: str, full_name: str = "", role: str = "user",
    department: str = "", employee_id: str = "", phone: str = "",
    qualification: str = "", joining_date: str = "", subjects: str = "",
    class_teacher: str = "", date_of_birth: str = "", address: str = "",
    emergency_contact: str = "", manager_email: str = "",
    must_change_password: int = 0,
) -> dict:
    email_norm = email.strip().lower()
    pw_hash = generate_password_hash(password)
    now = time.time()
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email_norm).first()
        if existing:
            return {"error": "A user with this email already exists."}
        user = User(
            email=email_norm,
            full_name=full_name or email_norm.split("@")[0],
            password_hash=pw_hash,
            role=role,
            department=department,
            employee_id=employee_id,
            phone=phone,
            qualification=qualification,
            joining_date=joining_date,
            subjects=subjects,
            class_teacher=class_teacher,
            date_of_birth=date_of_birth,
            address=address,
            emergency_contact=emergency_contact,
            manager_email=manager_email,
            must_change_password=must_change_password,
            created_at=now,
        )
        db.add(user)
        db.commit()
        return _to_dict(user)
    finally:
        db.close()


def list_users(department: str = "", role: str = "", search: str = "") -> list:
    db = SessionLocal()
    try:
        q = db.query(User)
        if department:
            q = q.filter(User.department == department)
        if role:
            q = q.filter(User.role == role)
        if search:
            like = f"%{search.strip()}%"
            q = q.filter(
                User.email.ilike(like) |
                User.full_name.ilike(like) |
                User.department.ilike(like)
            )
        users = q.order_by(User.full_name).all()
        return [_to_dict(u) for u in users]
    finally:
        db.close()


def update_user(email: str, data: dict) -> dict | None:
    email_norm = email.strip().lower()
    allowed = {
        "full_name", "role", "department", "employee_id", "phone",
        "qualification", "joining_date", "subjects", "class_teacher",
        "date_of_birth", "address", "emergency_contact", "manager_email",
        "must_change_password", "status",
    }
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email_norm).first()
        if not user:
            return None
        for key, val in data.items():
            if key in allowed:
                setattr(user, key, val)
        if "password" in data and data["password"]:
            user.password_hash = generate_password_hash(data["password"])
        db.commit()
        return _to_dict(user)
    finally:
        db.close()


def delete_user(email: str) -> bool:
    email_norm = email.strip().lower()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email_norm).first()
        if not user:
            return False
        db.delete(user)
        db.commit()
        return True
    finally:
        db.close()


def add_file_chunks(user_key: str, file_id: str, count: int = 0):
    db = SessionLocal()
    try:
        existing = db.query(FileChunk).filter(
            FileChunk.user_key == user_key,
            FileChunk.file_id == file_id,
        ).first()
        if existing:
            existing.chunk_count = count
        else:
            db.add(FileChunk(user_key=user_key, file_id=file_id, chunk_count=count))
        db.commit()
    finally:
        db.close()


def remove_file_chunks(user_key: str, file_id: str):
    db = SessionLocal()
    try:
        db.query(FileChunk).filter(
            FileChunk.user_key == user_key,
            FileChunk.file_id == file_id,
        ).delete()
        db.commit()
    finally:
        db.close()


def list_file_chunks(user_key: str) -> set[str]:
    db = SessionLocal()
    try:
        rows = db.query(FileChunk.file_id).filter(FileChunk.user_key == user_key).all()
        return {row.file_id for row in rows}
    finally:
        db.close()


def list_documents(user_key: str) -> dict:
    db = SessionLocal()
    try:
        rows = (
            db.query(Document)
            .filter(Document.user_key == user_key)
            .order_by(Document.uploaded_at.desc())
            .all()
        )
        result = {}
        for doc in rows:
            result[doc.file_id] = {
                "name": doc.name,
                "source_name": doc.source_name,
                "size": doc.size,
                "chunks": doc.chunks,
                "uploaded_at": doc.uploaded_at,
                "source": doc.source,
                "source_ref": doc.source_ref,
                "category_id": doc.category_id,
                "department": doc.department,
                "file_path": doc.file_path or "",
                "student_id": doc.student_id or "",
                "tags": doc.tags or [],
            }
        return result
    finally:
        db.close()


def save_document(user_key: str, file_id: str, entry: dict):
    db = SessionLocal()
    try:
        existing = db.query(Document).filter(Document.file_id == file_id).first()
        if existing:
            existing.name = entry["name"]
            existing.source_name = entry["source_name"]
            existing.size = entry["size"]
            existing.chunks = entry["chunks"]
            existing.uploaded_at = entry["uploaded_at"]
            existing.source = entry["source"]
            existing.source_ref = entry.get("source_ref", "")
            existing.category_id = entry.get("category_id") or existing.category_id
            existing.department = entry.get("department") or existing.department
            existing.tags = entry.get("tags") or existing.tags
            existing.student_id = entry.get("student_id", "") or existing.student_id
            if entry.get("file_path"):
                existing.file_path = entry["file_path"]
        else:
            doc = Document(
                file_id=file_id,
                user_key=user_key,
                name=entry["name"],
                source_name=entry["source_name"],
                size=entry["size"],
                chunks=entry["chunks"],
                uploaded_at=entry["uploaded_at"],
                source=entry["source"],
                source_ref=entry.get("source_ref", ""),
                category_id=entry.get("category_id"),
                department=entry.get("department"),
                file_path=entry.get("file_path", ""),
                tags=entry.get("tags", []),
                student_id=entry.get("student_id", ""),
            )
            db.add(doc)
        db.commit()
    finally:
        db.close()


def get_document_by_source_ref(user_key: str, source_ref: str, source: str | None = None) -> dict | None:
    if not source_ref:
        return None
    db = SessionLocal()
    try:
        query = db.query(Document).filter(
            Document.user_key == user_key,
            Document.source_ref == source_ref,
        )
        if source is not None:
            query = query.filter(Document.source == source)
        doc = query.order_by(Document.uploaded_at.desc()).first()
        if not doc:
            return None
        return {
            "file_id": doc.file_id,
            "name": doc.name,
            "source_name": doc.source_name,
            "size": doc.size,
            "chunks": doc.chunks,
            "uploaded_at": doc.uploaded_at,
            "source": doc.source,
            "source_ref": doc.source_ref,
            "student_id": doc.student_id or "",
        }
    finally:
        db.close()


def delete_document(user_key: str, file_id: str) -> bool:
    db = SessionLocal()
    try:
        result = (
            db.query(Document)
            .filter(Document.user_key == user_key, Document.file_id == file_id)
            .delete()
        )
        db.commit()
        return result > 0
    finally:
        db.close()


def delete_all_documents(user_key: str):
    db = SessionLocal()
    try:
        db.query(Document).filter(Document.user_key == user_key).delete()
        db.commit()
    finally:
        db.close()


def get_chat_session(user_key: str, session_id: str) -> dict | None:
    db = SessionLocal()
    try:
        row = (
            db.query(
                ChatSession.session_id,
                ChatSession.title,
                ChatSession.created_at,
                ChatSession.updated_at,
                func.count(ChatMessage.message_id).label("message_count"),
            )
            .outerjoin(ChatMessage, ChatMessage.session_id == ChatSession.session_id)
            .filter(ChatSession.user_key == user_key, ChatSession.session_id == session_id)
            .group_by(ChatSession.session_id, ChatSession.title, ChatSession.created_at, ChatSession.updated_at)
            .first()
        )
        if not row:
            return None
        return {
            "session_id": row.session_id,
            "title": row.title,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            "message_count": row.message_count or 0,
        }
    finally:
        db.close()


def list_chat_sessions(user_key: str) -> list:
    db = SessionLocal()
    try:
        rows = (
            db.query(
                ChatSession.session_id,
                ChatSession.title,
                ChatSession.created_at,
                ChatSession.updated_at,
                func.count(ChatMessage.message_id).label("message_count"),
            )
            .outerjoin(ChatMessage, ChatMessage.session_id == ChatSession.session_id)
            .filter(ChatSession.user_key == user_key)
            .group_by(ChatSession.session_id, ChatSession.title, ChatSession.created_at, ChatSession.updated_at)
            .order_by(ChatSession.updated_at.desc(), ChatSession.created_at.desc())
            .all()
        )
        return [
            {
                "session_id": r.session_id,
                "title": r.title,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
                "message_count": r.message_count or 0,
            }
            for r in rows
        ]
    finally:
        db.close()


def create_chat_session(user_key: str, title: str = DEFAULT_CHAT_TITLE) -> dict:
    now = time.time()
    session_id = uuid.uuid4().hex
    db = SessionLocal()
    try:
        session = ChatSession(
            session_id=session_id,
            user_key=user_key,
            title=title,
            created_at=now,
            updated_at=now,
        )
        db.add(session)
        db.commit()
        return {
            "session_id": session_id,
            "title": title,
            "created_at": now,
            "updated_at": now,
            "message_count": 0,
        }
    finally:
        db.close()


def update_chat_session_title(user_key: str, session_id: str, title: str) -> dict | None:
    title = (title or "").strip() or DEFAULT_CHAT_TITLE
    now = time.time()
    db = SessionLocal()
    try:
        result = (
            db.query(ChatSession)
            .filter(ChatSession.user_key == user_key, ChatSession.session_id == session_id)
            .update({"title": title, "updated_at": now})
        )
        db.commit()
        if result == 0:
            return None
        return get_chat_session(user_key, session_id)
    finally:
        db.close()


def delete_chat_session(user_key: str, session_id: str) -> bool:
    db = SessionLocal()
    try:
        result = (
            db.query(ChatSession)
            .filter(ChatSession.user_key == user_key, ChatSession.session_id == session_id)
            .delete()
        )
        db.commit()
        return result > 0
    finally:
        db.close()


def ensure_chat_session(user_key: str, session_id: str | None = None) -> dict:
    if session_id:
        session = get_chat_session(user_key, session_id)
        if session:
            return session

    sessions = list_chat_sessions(user_key)
    if sessions:
        return sessions[0]

    return create_chat_session(user_key)


def list_chat_messages(user_key: str, session_id: str) -> list:
    db = SessionLocal()
    try:
        rows = (
            db.query(ChatMessage)
            .join(ChatSession, ChatSession.session_id == ChatMessage.session_id)
            .filter(ChatSession.user_key == user_key, ChatSession.session_id == session_id)
            .order_by(ChatMessage.created_at.asc(), ChatMessage.message_id.asc())
            .all()
        )
        messages = []
        for row in rows:
            try:
                sources = json.loads(row.sources_json or "[]")
            except json.JSONDecodeError:
                sources = []
            messages.append({
                "message_id": row.message_id,
                "role": row.role,
                "content": row.content,
                "sources": sources,
                "feedback": row.feedback,
                "timestamp": row.created_at,
            })
        return messages
    finally:
        db.close()


def append_chat_message(
    user_key: str,
    role: str,
    content: str,
    sources: list | None = None,
    session_id: str | None = None,
):
    if not content:
        return

    session = ensure_chat_session(user_key, session_id)
    now = time.time()
    serialized_sources = json.dumps(sources or [])

    db = SessionLocal()
    try:
        msg = ChatMessage(
            session_id=session["session_id"],
            role=role,
            content=content,
            sources_json=serialized_sources,
            created_at=now,
        )
        db.add(msg)
        db.flush()
        message_id = msg.message_id

        title = session["title"]
        if role == "user" and title == DEFAULT_CHAT_TITLE:
            title = content.strip()[:60] or DEFAULT_CHAT_TITLE

        db.query(ChatSession).filter(
            ChatSession.session_id == session["session_id"],
            ChatSession.user_key == user_key,
        ).update({"title": title, "updated_at": now})

        db.commit()
        return message_id
    finally:
        db.close()


def set_message_feedback(message_id: int, user_key: str, feedback: int | None):
    if feedback is not None and feedback not in (-1, 1):
        raise ValueError("feedback must be -1, 1, or None")
    db = SessionLocal()
    try:
        db.query(ChatMessage).filter(
            ChatMessage.message_id == message_id,
            ChatMessage.session_id.in_(
                db.query(ChatSession.session_id).filter(ChatSession.user_key == user_key)
            ),
        ).update({"feedback": feedback})
        db.commit()
    finally:
        db.close()


def clear_chat_messages(user_key: str, session_id: str):
    ensure_chat_session(user_key, session_id)
    now = time.time()
    db = SessionLocal()
    try:
        subquery = (
            db.query(ChatSession.session_id)
            .filter(ChatSession.user_key == user_key, ChatSession.session_id == session_id)
        )
        db.query(ChatMessage).filter(ChatMessage.session_id.in_(subquery)).delete(
            synchronize_session=False
        )
        db.query(ChatSession).filter(
            ChatSession.user_key == user_key,
            ChatSession.session_id == session_id,
        ).update({"title": DEFAULT_CHAT_TITLE, "updated_at": now})
        db.commit()
    finally:
        db.close()


def delete_all_chat_data(user_key: str):
    db = SessionLocal()
    try:
        subquery = db.query(ChatSession.session_id).filter(ChatSession.user_key == user_key)
        db.query(ChatMessage).filter(ChatMessage.session_id.in_(subquery)).delete(
            synchronize_session=False
        )
        db.query(ChatSession).filter(ChatSession.user_key == user_key).delete()
        db.commit()
    finally:
        db.close()


# ─── School Management ──────────────────────────────────────────────

SCHOOL_DOCUMENT_CATEGORIES = [
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

SCHOOL_DEPARTMENTS = [
    {"name": "Administration", "code": "ADMIN"},
    {"name": "Science", "code": "SCI"},
    {"name": "Mathematics", "code": "MATH"},
    {"name": "Languages", "code": "LANG"},
    {"name": "Social Studies", "code": "SOC"},
    {"name": "Finance & Accounts", "code": "FIN"},
    {"name": "Human Resources", "code": "HR"},
    {"name": "IT Support", "code": "IT"},
]


def init_school_data():
    from app.config import SchoolConfig
    db = SessionLocal()
    try:
        existing = db.query(School).first()
        if existing:
            return existing

        school = School(
            name=SchoolConfig.DEFAULT_SCHOOL_NAME,
            code=SchoolConfig.DEFAULT_SCHOOL_CODE,
        )
        db.add(school)
        db.flush()

        for dept_data in SCHOOL_DEPARTMENTS:
            dept = Department(
                school_id=school.id,
                name=dept_data["name"],
                code=dept_data["code"],
            )
            db.add(dept)

        for cat_data in SCHOOL_DOCUMENT_CATEGORIES:
            parent = DocumentCategory(
                school_id=school.id,
                name=cat_data["name"],
                icon=cat_data.get("icon", "folder"),
            )
            db.add(parent)
            db.flush()
            for child_data in cat_data.get("children", []):
                child = DocumentCategory(
                    school_id=school.id,
                    name=child_data["name"],
                    icon=child_data.get("icon", "folder"),
                    parent_id=parent.id,
                )
                db.add(child)

        db.commit()
        return school
    finally:
        db.close()


def get_dashboard_stats(user_key: str = None) -> dict:
    db = SessionLocal()
    try:
        base = db.query(RepositoryDocument)
        if user_key:
            base = base.filter(RepositoryDocument.user_key == user_key)
        doc_count = base.filter(RepositoryDocument.status == "active").count()

        chat_base = db.query(ChatMessage)
        if user_key:
            chat_base = chat_base.join(ChatSession).filter(ChatSession.user_key == user_key)
        chat_count = chat_base.count()

        email = (session.get("user") or "").strip().lower()
        me = db.query(User).filter(User.email == email).first()
        school_id = me.school_id if me and me.school_id else None

        if school_id:
            user_count = db.query(User).filter(User.school_id == school_id).count()
            category_count = (
                db.query(DocumentCategory).filter(DocumentCategory.school_id == school_id).count()
            )
        elif email:
            user_count = db.query(User).filter(User.email == email).count()
            category_count = 0
        else:
            user_count = db.query(User).count()
            category_count = db.query(DocumentCategory).count()

        recent_base = db.query(RepositoryDocument)
        if user_key:
            recent_base = recent_base.filter(RepositoryDocument.user_key == user_key)
        recent_docs = (
            recent_base
            .filter(RepositoryDocument.status == "active")
            .order_by(RepositoryDocument.created_at.desc())
            .limit(5)
            .all()
        )

        return {
            "doc_count": doc_count,
            "chat_count": chat_count,
            "staff_count": user_count,
            "category_count": category_count,
            "recent_docs": [
                {
                    "file_id": d.file_id or "",
                    "name": d.name,
                    "size": f"{d.size / 1024:.1f} KB" if d.size < 1048576 else f"{d.size / 1048576:.1f} MB",
                    "uploaded_at_str": time.strftime("%b %d, %Y", time.localtime(d.created_at)),
                }
                for d in recent_docs
            ],
        }
    finally:
        db.close()


def list_categories(school_id: str = None) -> list:
    db = SessionLocal()
    try:
        query = db.query(DocumentCategory).filter(DocumentCategory.parent_id == None)
        if school_id:
            query = query.filter(DocumentCategory.school_id == school_id)
        parents = query.order_by(DocumentCategory.sort_order).all()
        result = []
        for parent in parents:
            children = (
                db.query(DocumentCategory)
                .filter(DocumentCategory.parent_id == parent.id)
                .order_by(DocumentCategory.sort_order)
                .all()
            )
            result.append({
                "id": parent.id,
                "name": parent.name,
                "icon": parent.icon,
                "children": [
                    {"id": c.id, "name": c.name, "icon": c.icon} for c in children
                ],
            })
        return result
    finally:
        db.close()
