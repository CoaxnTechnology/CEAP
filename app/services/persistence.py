import json
import os
import sqlite3
import time
import uuid

from werkzeug.security import generate_password_hash


DB_PATH = os.getenv("APP_DB_PATH", "./documind.sqlite3")


def _ensure_db_dir():
    db_dir = os.path.dirname(os.path.abspath(DB_PATH))
    os.makedirs(db_dir, exist_ok=True)


def _connect():
    _ensure_db_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS documents (
                file_id TEXT PRIMARY KEY,
                user_key TEXT NOT NULL,
                name TEXT NOT NULL,
                source_name TEXT NOT NULL,
                size INTEGER NOT NULL,
                chunks INTEGER NOT NULL,
                uploaded_at REAL NOT NULL,
                source TEXT NOT NULL,
                source_ref TEXT NOT NULL DEFAULT ''
            );

            CREATE INDEX IF NOT EXISTS idx_documents_user_key
            ON documents(user_key, uploaded_at DESC);

            CREATE INDEX IF NOT EXISTS idx_documents_source_ref
            ON documents(user_key, source, source_ref);

            CREATE TABLE IF NOT EXISTS chat_sessions (
                session_id TEXT PRIMARY KEY,
                user_key TEXT NOT NULL,
                title TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_key
            ON chat_sessions(user_key, updated_at DESC);

            CREATE TABLE IF NOT EXISTS chat_messages (
                message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                sources_json TEXT NOT NULL DEFAULT '[]',
                created_at REAL NOT NULL,
                FOREIGN KEY(session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_chat_messages_session
            ON chat_messages(session_id, created_at ASC, message_id ASC);

            CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY,
                full_name TEXT NOT NULL DEFAULT '',
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                department TEXT NOT NULL DEFAULT '',
                employee_id TEXT NOT NULL DEFAULT '',
                manager_email TEXT NOT NULL DEFAULT '',
                leave_balance_json TEXT NOT NULL DEFAULT '{"annual": 20, "sick": 12, "personal": 5}',
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS file_chunks (
                user_key TEXT NOT NULL,
                file_id TEXT NOT NULL,
                chunk_count INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_key, file_id)
            );
            """
        )

        # Migration: add full_name if not present
        try:
            conn.execute("ALTER TABLE users ADD COLUMN full_name TEXT NOT NULL DEFAULT ''")
        except Exception:
            pass

        # Migration: add new columns to users table
        for col_def in [
            ("role", "TEXT NOT NULL DEFAULT 'user'"),
            ("department", "TEXT NOT NULL DEFAULT ''"),
            ("employee_id", "TEXT NOT NULL DEFAULT ''"),
            ("manager_email", "TEXT NOT NULL DEFAULT ''"),
            ("leave_balance_json", "TEXT NOT NULL DEFAULT '{\"annual\": 20, \"sick\": 12, \"personal\": 5}'"),
        ]:
            try:
                conn.execute(f"ALTER TABLE users ADD COLUMN {col_def[0]} {col_def[1]}")
            except Exception:
                pass

        # Add feedback column to chat_messages if not present
        try:
            conn.execute("ALTER TABLE chat_messages ADD COLUMN feedback INTEGER DEFAULT NULL")
        except Exception:
            pass


def init_users_from_config():
    from app.config import AuthConfig
    for email, password in AuthConfig.USERS.items():
        email_norm = email.strip().lower()
        if not get_user_by_email(email_norm):
            create_user(email_norm, password)


def get_user_by_email(email: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT email, full_name, password_hash, role, department, employee_id, manager_email, leave_balance_json, created_at FROM users WHERE email = ?",
            (email.strip().lower(),),
        ).fetchone()
    if not row:
        return None
    return {
        "email": row["email"],
        "full_name": row["full_name"],
        "password_hash": row["password_hash"],
        "role": row["role"],
        "department": row["department"],
        "employee_id": row["employee_id"],
        "manager_email": row["manager_email"],
        "leave_balance_json": row["leave_balance_json"],
        "created_at": row["created_at"],
    }


def update_user_role(email: str):
    role_map = {
        "admin": "admin",
        "hr": "hr",
        "accounting": "accounting",
    }
    email_norm = email.strip().lower()
    prefix = email_norm.split("@")[0]
    role = role_map.get(prefix, "user")
    with _connect() as conn:
        conn.execute(
            "UPDATE users SET role = ? WHERE email = ?",
            (role, email_norm),
        )
    return role


def create_user(email: str, password: str) -> dict:
    email_norm = email.strip().lower()
    pw_hash = generate_password_hash(password)
    now = time.time()
    full_name = email_norm.split("@")[0]
    with _connect() as conn:
        try:
            conn.execute(
                "INSERT OR IGNORE INTO users (email, full_name, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (email_norm, full_name, pw_hash, now),
            )
        except Exception:
            conn.execute(
                "INSERT OR IGNORE INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
                (email_norm, pw_hash, now),
            )
    return {"email": email_norm, "created_at": now}


def add_file_chunks(user_key: str, file_id: str, count: int = 0):
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO file_chunks (user_key, file_id, chunk_count) VALUES (?, ?, ?)",
            (user_key, file_id, count),
        )


def remove_file_chunks(user_key: str, file_id: str):
    with _connect() as conn:
        conn.execute(
            "DELETE FROM file_chunks WHERE user_key = ? AND file_id = ?",
            (user_key, file_id),
        )


def list_file_chunks(user_key: str) -> set[str]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT file_id FROM file_chunks WHERE user_key = ?",
            (user_key,),
        ).fetchall()
    return {row["file_id"] for row in rows}


def list_documents(user_key: str) -> dict:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT file_id, name, source_name, size, chunks, uploaded_at, source, source_ref
            FROM documents
            WHERE user_key = ?
            ORDER BY uploaded_at DESC
            """,
            (user_key,),
        ).fetchall()

    return {
        row["file_id"]: {
            "name": row["name"],
            "source_name": row["source_name"],
            "size": row["size"],
            "chunks": row["chunks"],
            "uploaded_at": row["uploaded_at"],
            "source": row["source"],
            "source_ref": row["source_ref"],
        }
        for row in rows
    }


def save_document(user_key: str, file_id: str, entry: dict):
    with _connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO documents
            (file_id, user_key, name, source_name, size, chunks, uploaded_at, source, source_ref)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                file_id,
                user_key,
                entry["name"],
                entry["source_name"],
                entry["size"],
                entry["chunks"],
                entry["uploaded_at"],
                entry["source"],
                entry.get("source_ref", ""),
            ),
        )


def get_document_by_source_ref(
    user_key: str, source_ref: str, source: str | None = None
) -> dict | None:
    if not source_ref:
        return None

    query = """
        SELECT file_id, name, source_name, size, chunks, uploaded_at, source, source_ref
        FROM documents
        WHERE user_key = ? AND source_ref = ?
    """
    params: tuple = (user_key, source_ref)

    if source is not None:
        query += " AND source = ?"
        params = (user_key, source_ref, source)

    query += " ORDER BY uploaded_at DESC LIMIT 1"

    with _connect() as conn:
        row = conn.execute(query, params).fetchone()

    if not row:
        return None

    return {
        "file_id": row["file_id"],
        "name": row["name"],
        "source_name": row["source_name"],
        "size": row["size"],
        "chunks": row["chunks"],
        "uploaded_at": row["uploaded_at"],
        "source": row["source"],
        "source_ref": row["source_ref"],
    }


def delete_document(user_key: str, file_id: str) -> bool:
    with _connect() as conn:
        cur = conn.execute(
            "DELETE FROM documents WHERE user_key = ? AND file_id = ?",
            (user_key, file_id),
        )
        return cur.rowcount > 0


def delete_all_documents(user_key: str):
    with _connect() as conn:
        conn.execute("DELETE FROM documents WHERE user_key = ?", (user_key,))


DEFAULT_CHAT_TITLE = "New Chat"


def _row_to_session(row) -> dict:
    return {
        "session_id": row["session_id"],
        "title": row["title"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "message_count": row["message_count"] if "message_count" in row.keys() else 0,
    }


def get_chat_session(user_key: str, session_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT s.session_id, s.title, s.created_at, s.updated_at, COUNT(m.message_id) AS message_count
            FROM chat_sessions s
            LEFT JOIN chat_messages m ON m.session_id = s.session_id
            WHERE s.user_key = ? AND s.session_id = ?
            GROUP BY s.session_id, s.title, s.created_at, s.updated_at
            """,
            (user_key, session_id),
        ).fetchone()

    return _row_to_session(row) if row else None


def list_chat_sessions(user_key: str) -> list:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT s.session_id, s.title, s.created_at, s.updated_at, COUNT(m.message_id) AS message_count
            FROM chat_sessions s
            LEFT JOIN chat_messages m ON m.session_id = s.session_id
            WHERE s.user_key = ?
            GROUP BY s.session_id, s.title, s.created_at, s.updated_at
            ORDER BY s.updated_at DESC, s.created_at DESC
            """,
            (user_key,),
        ).fetchall()

    return [_row_to_session(row) for row in rows]


def create_chat_session(user_key: str, title: str = DEFAULT_CHAT_TITLE) -> dict:
    now = time.time()
    session_id = uuid.uuid4().hex
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO chat_sessions (session_id, user_key, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, user_key, title, now, now),
        )
    return {
        "session_id": session_id,
        "title": title,
        "created_at": now,
        "updated_at": now,
        "message_count": 0,
    }


def update_chat_session_title(user_key: str, session_id: str, title: str) -> dict | None:
    title = (title or "").strip() or DEFAULT_CHAT_TITLE
    now = time.time()
    with _connect() as conn:
        cur = conn.execute(
            """
            UPDATE chat_sessions
            SET title = ?, updated_at = ?
            WHERE user_key = ? AND session_id = ?
            """,
            (title, now, user_key, session_id),
        )
        if cur.rowcount == 0:
            return None

    return get_chat_session(user_key, session_id)


def delete_chat_session(user_key: str, session_id: str) -> bool:
    with _connect() as conn:
        cur = conn.execute(
            "DELETE FROM chat_sessions WHERE user_key = ? AND session_id = ?",
            (user_key, session_id),
        )
        return cur.rowcount > 0


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
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT m.message_id, m.role, m.content, m.sources_json, m.feedback, m.created_at
            FROM chat_messages m
            JOIN chat_sessions s ON s.session_id = m.session_id
            WHERE s.user_key = ? AND s.session_id = ?
            ORDER BY m.created_at ASC, m.message_id ASC
            """,
            (user_key, session_id),
        ).fetchall()

    messages = []
    for row in rows:
        try:
            sources = json.loads(row["sources_json"] or "[]")
        except json.JSONDecodeError:
            sources = []
        messages.append(
            {
                "message_id": row["message_id"],
                "role": row["role"],
                "content": row["content"],
                "sources": sources,
                "feedback": row["feedback"],
                "timestamp": row["created_at"],
            }
        )
    return messages


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

    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO chat_messages (session_id, role, content, sources_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session["session_id"], role, content, serialized_sources, now),
        )
        message_id = cursor.lastrowid

        title = session["title"]
        if role == "user" and title == DEFAULT_CHAT_TITLE:
            title = content.strip()[:60] or DEFAULT_CHAT_TITLE

        conn.execute(
            """
            UPDATE chat_sessions
            SET title = ?, updated_at = ?
            WHERE session_id = ? AND user_key = ?
            """,
            (title, now, session["session_id"], user_key),
        )

    return message_id


def set_message_feedback(message_id: int, user_key: str, feedback: int | None):
    if feedback is not None and feedback not in (-1, 1):
        raise ValueError("feedback must be -1, 1, or None")
    with _connect() as conn:
        conn.execute(
            """
            UPDATE chat_messages
            SET feedback = ?
            WHERE message_id IN (
                SELECT m.message_id FROM chat_messages m
                JOIN chat_sessions s ON s.session_id = m.session_id
                WHERE m.message_id = ? AND s.user_key = ?
            )
            """,
            (feedback, message_id, user_key),
        )


def clear_chat_messages(user_key: str, session_id: str):
    ensure_chat_session(user_key, session_id)
    now = time.time()
    with _connect() as conn:
        conn.execute(
            """
            DELETE FROM chat_messages
            WHERE session_id IN (
                SELECT session_id FROM chat_sessions WHERE user_key = ? AND session_id = ?
            )
            """,
            (user_key, session_id),
        )
        conn.execute(
            """
            UPDATE chat_sessions
            SET title = ?, updated_at = ?
            WHERE user_key = ? AND session_id = ?
            """,
            (DEFAULT_CHAT_TITLE, now, user_key, session_id),
        )


def delete_all_chat_data(user_key: str):
    with _connect() as conn:
        conn.execute("DELETE FROM chat_messages WHERE session_id IN (SELECT session_id FROM chat_sessions WHERE user_key = ?)", (user_key,))
        conn.execute("DELETE FROM chat_sessions WHERE user_key = ?", (user_key,))


init_db()
init_users_from_config()
