import uuid
import time
from sqlalchemy import (
    Column, String, Integer, Float, Text, JSON, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from app.db import Base


def _ts():
    return time.time()


def _uuid():
    return uuid.uuid4().hex


class User(Base):
    __tablename__ = "users"

    email = Column(String(255), primary_key=True)
    full_name = Column(String(255), nullable=False, default="")
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="user")
    department = Column(String(100), default="")
    employee_id = Column(String(50), default="")
    manager_email = Column(String(255), default="")
    leave_balance_json = Column(Text, default='{"annual": 20, "sick": 12, "personal": 5}')
    created_at = Column(Float, default=_ts)


class Document(Base):
    __tablename__ = "documents"

    file_id = Column(String(64), primary_key=True)
    user_key = Column(String(64), nullable=False)
    name = Column(String(255), nullable=False)
    source_name = Column(String(255), nullable=False)
    size = Column(Integer, nullable=False)
    chunks = Column(Integer, nullable=False)
    uploaded_at = Column(Float, nullable=False)
    source = Column(String(50), nullable=False)
    source_ref = Column(String(255), default="")

    __table_args__ = (
        Index("idx_documents_user_key", user_key, uploaded_at.desc()),
        Index("idx_documents_source_ref", user_key, source, source_ref),
    )


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    session_id = Column(String(64), primary_key=True)
    user_key = Column(String(64), nullable=False)
    title = Column(String(255), nullable=False)
    created_at = Column(Float, nullable=False)
    updated_at = Column(Float, nullable=False)

    __table_args__ = (
        Index("idx_chat_sessions_user_key", user_key, updated_at.desc()),
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    message_id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), ForeignKey("chat_sessions.session_id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    sources_json = Column(Text, default="[]")
    feedback = Column(Integer, default=None)
    created_at = Column(Float, nullable=False)

    __table_args__ = (
        Index("idx_chat_messages_session", session_id, created_at.asc(), message_id.asc()),
    )


class FileChunk(Base):
    __tablename__ = "file_chunks"

    user_key = Column(String(64), primary_key=True)
    file_id = Column(String(64), primary_key=True)
    chunk_count = Column(Integer, default=0)


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id = Column(String(64), primary_key=True, default=_uuid)
    user_email = Column(String(255), ForeignKey("users.email"), nullable=False)
    leave_type = Column(String(50), nullable=False)
    start_date = Column(String(20), nullable=False)
    end_date = Column(String(20), nullable=False)
    reason = Column(Text, default="")
    status = Column(String(20), default="pending")
    approved_by = Column(String(255), default="")
    created_at = Column(Float, default=_ts)
    updated_at = Column(Float, default=_ts, onupdate=_ts)


class AttendanceLog(Base):
    __tablename__ = "attendance_logs"

    id = Column(String(64), primary_key=True, default=_uuid)
    user_email = Column(String(255), ForeignKey("users.email"), nullable=False)
    date = Column(String(20), nullable=False)
    check_in = Column(String(20), default="")
    check_out = Column(String(20), default="")
    source = Column(String(50), default="manual")

    __table_args__ = (
        UniqueConstraint("user_email", "date", name="uq_attendance_user_date"),
    )


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(String(64), primary_key=True, default=_uuid)
    user_key = Column(String(64), nullable=False)
    invoice_number = Column(String(100), default="")
    vendor_name = Column(String(255), default="")
    date = Column(String(20), default="")
    due_date = Column(String(20), default="")
    total_amount = Column(Float, default=0.0)
    tax = Column(Float, default=0.0)
    currency = Column(String(10), default="USD")
    status = Column(String(20), default="pending")
    file_ref = Column(String(255), default="")
    extracted_data = Column(JSON, default=dict)
    created_at = Column(Float, default=_ts)


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(String(64), primary_key=True, default=_uuid)
    user_email = Column(String(255), ForeignKey("users.email"), nullable=False)
    category = Column(String(100), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(Text, default="")
    receipt_file = Column(String(255), default="")
    status = Column(String(20), default="pending")
    approved_by = Column(String(255), default="")
    created_at = Column(Float, default=_ts)


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(String(64), primary_key=True, default=_uuid)
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    date = Column(String(20), nullable=False)
    time = Column(String(20), default="")
    duration_minutes = Column(Integer, default=60)
    room = Column(String(100), default="")
    attendees = Column(JSON, default=list)
    organizer = Column(String(255), nullable=False)
    status = Column(String(20), default="scheduled")
    created_at = Column(Float, default=_ts)


class Asset(Base):
    __tablename__ = "assets"

    id = Column(String(64), primary_key=True, default=_uuid)
    name = Column(String(255), nullable=False)
    asset_type = Column(String(100), default="")
    serial_number = Column(String(100), default="")
    assigned_to = Column(String(255), default="")
    location = Column(String(255), default="")
    status = Column(String(20), default="available")
    purchase_date = Column(String(20), default="")
    purchase_price = Column(Float, default=0.0)
    notes = Column(Text, default="")
    created_at = Column(Float, default=_ts)


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(String(64), primary_key=True, default=_uuid)
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    category = Column(String(100), default="general")
    priority = Column(String(20), default="medium")
    status = Column(String(20), default="open")
    created_by = Column(String(255), nullable=False)
    assignee = Column(String(255), default="")
    created_at = Column(Float, default=_ts)
    updated_at = Column(Float, default=_ts, onupdate=_ts)


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id = Column(String(64), primary_key=True, default=_uuid)
    workflow_type = Column(String(50), nullable=False)
    requester = Column(String(255), nullable=False)
    approver = Column(String(255), nullable=False)
    status = Column(String(20), default="pending")
    metadata_json = Column(JSON, default=dict)
    steps_json = Column(JSON, default=list)
    current_step = Column(Integer, default=0)
    created_at = Column(Float, default=_ts)
    updated_at = Column(Float, default=_ts, onupdate=_ts)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(64), primary_key=True, default=_uuid)
    user_email = Column(String(255), ForeignKey("users.email"), nullable=False)
    type = Column(String(50), nullable=False)
    title = Column(String(255), default="")
    message = Column(Text, nullable=False)
    link = Column(String(255), default="")
    read = Column(Integer, default=0)
    created_at = Column(Float, default=_ts)

    __table_args__ = (
        Index("idx_notifications_user", user_email, created_at.desc()),
    )


class OfficeSupply(Base):
    __tablename__ = "office_supplies"

    id = Column(String(64), primary_key=True, default=_uuid)
    name = Column(String(255), nullable=False)
    category = Column(String(100), default="")
    quantity = Column(Integer, default=0)
    min_quantity = Column(Integer, default=5)
    unit = Column(String(50), default="pcs")
    location = Column(String(100), default="")
    created_at = Column(Float, default=_ts)


class SupplyRequest(Base):
    __tablename__ = "supply_requests"

    id = Column(String(64), primary_key=True, default=_uuid)
    user_email = Column(String(255), ForeignKey("users.email"), nullable=False)
    supply_name = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False)
    reason = Column(Text, default="")
    status = Column(String(20), default="pending")
    created_at = Column(Float, default=_ts)


class Visitor(Base):
    __tablename__ = "visitors"

    id = Column(String(64), primary_key=True, default=_uuid)
    name = Column(String(255), nullable=False)
    company = Column(String(255), default="")
    email = Column(String(255), default="")
    phone = Column(String(50), default="")
    host_email = Column(String(255), nullable=False)
    purpose = Column(Text, default="")
    check_in = Column(Float, default=None)
    check_out = Column(Float, default=None)
    status = Column(String(20), default="expected")
    created_at = Column(Float, default=_ts)


class CompanyAnnouncement(Base):
    __tablename__ = "company_announcements"

    id = Column(String(64), primary_key=True, default=_uuid)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    priority = Column(String(20), default="normal")
    created_by = Column(String(255), nullable=False)
    created_at = Column(Float, default=_ts)


class AccountingEntry(Base):
    __tablename__ = "accounting_entries"

    id = Column(String(64), primary_key=True, default=_uuid)
    user_key = Column(String(64), nullable=False)
    entry_date = Column(String(20), nullable=False)
    account_code = Column(String(50), nullable=False)
    account_name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    debit_amount = Column(Float, default=0.0)
    credit_amount = Column(Float, default=0.0)
    reference_type = Column(String(50), default="")
    reference_id = Column(String(64), default="")
    created_by = Column(String(255), nullable=False)
    created_at = Column(Float, default=_ts)


class AuditDocument(Base):
    __tablename__ = "audit_documents"

    id = Column(String(64), primary_key=True, default=_uuid)
    user_key = Column(String(64), nullable=False)
    document_name = Column(String(255), nullable=False)
    file_ref = Column(String(255), default="")
    category = Column(String(100), default="")
    tags = Column(JSON, default=list)
    notes = Column(Text, default="")
    uploaded_by = Column(String(255), nullable=False)
    created_at = Column(Float, default=_ts)
