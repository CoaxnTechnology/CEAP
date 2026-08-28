import time
import uuid

from sqlalchemy import (
    JSON,
    Column,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import backref, relationship

from app.db import Base


def _ts():
    return time.time()


def _uuid():
    return uuid.uuid4().hex


class School(Base):
    __tablename__ = "schools"

    id = Column(String(64), primary_key=True, default=_uuid)
    name = Column(String(255), nullable=False)
    code = Column(String(50), unique=True, default="")
    address = Column(Text, default="")
    phone = Column(String(50), default="")
    email = Column(String(255), default="")
    logo_url = Column(String(500), default="")
    status = Column(String(20), default="active")
    created_at = Column(Float, default=_ts)
    # Onboarding fields
    board = Column(String(100), default="")
    city = Column(String(100), default="")
    state = Column(String(100), default="")
    academic_year = Column(String(20), default="")
    student_count = Column(Integer, default=0)
    staff_count = Column(Integer, default=0)
    website = Column(String(255), default="")


class Department(Base):
    __tablename__ = "departments"

    id = Column(String(64), primary_key=True, default=_uuid)
    school_id = Column(String(64), ForeignKey("schools.id"), nullable=False)
    name = Column(String(255), nullable=False)
    code = Column(String(50), default="")
    head_email = Column(String(255), default="")
    created_at = Column(Float, default=_ts)

    school = relationship("School", backref="departments")


class DocumentCategory(Base):
    __tablename__ = "document_categories"

    id = Column(String(64), primary_key=True, default=_uuid)
    school_id = Column(String(64), ForeignKey("schools.id"), nullable=False)
    name = Column(String(255), nullable=False)
    parent_id = Column(String(64), ForeignKey("document_categories.id"), nullable=True)
    icon = Column(String(50), default="folder")
    sort_order = Column(Integer, default=0)
    created_at = Column(Float, default=_ts)

    school = relationship("School", backref="document_categories")
    parent = relationship("DocumentCategory", remote_side="DocumentCategory.id", backref="children")


class User(Base):
    __tablename__ = "users"

    email = Column(String(255), primary_key=True)
    full_name = Column(String(255), nullable=False, default="")
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="user")
    department = Column(String(100), default="")
    employee_id = Column(String(50), default="")
    manager_email = Column(String(255), default="")
    school_id = Column(String(64), ForeignKey("schools.id"), nullable=True)
    phone = Column(String(50), default="")
    qualification = Column(String(255), default="")
    joining_date = Column(String(20), default="")
    subjects = Column(Text, default="")
    class_teacher = Column(String(100), default="")
    date_of_birth = Column(String(20), default="")
    address = Column(Text, default="")
    emergency_contact = Column(String(50), default="")
    leave_balance_json = Column(Text, default='{"annual": 20, "sick": 12, "personal": 5}')
    # Invitation fields
    invited_by = Column(String(255), default="")
    invited_at = Column(Float, default=None)
    status = Column(String(20), default="active")  # active, invited, disabled
    must_change_password = Column(Integer, default=0)
    is_admin = Column(Integer, default=0)
    created_at = Column(Float, default=_ts)
    # Cloud connector persistence (OneDrive / Google Drive)
    od_token = Column(Text, default="")
    od_cache = Column(Text, default="")
    od_user = Column(String(255), default="")
    od_email = Column(String(255), default="")
    gd_token = Column(Text, default="")
    gd_user = Column(String(255), default="")
    gd_email = Column(String(255), default="")

    school = relationship("School", backref="users")


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
    category_id = Column(String(64), ForeignKey("document_categories.id"), nullable=True)
    department = Column(String(50), nullable=True)
    tags = Column(JSON, default=list)
    version = Column(Integer, default=1)
    file_path = Column(String(500), default="")
    student_id = Column(String(64), default="")

    category = relationship("DocumentCategory", backref="documents")

    __table_args__ = (
        Index("idx_documents_user_key", user_key, uploaded_at.desc()),
        Index("idx_documents_source_ref", user_key, source, source_ref),
        Index("idx_documents_category", category_id),
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
    half_day = Column(Integer, default=0)
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
    user_key = Column(String(64), default="")
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
    user_key = Column(String(64), default="")
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
    user_key = Column(String(64), default="")
    workflow_type = Column(String(50), nullable=False)
    requester = Column(String(255), nullable=False)
    approver = Column(String(255), nullable=False)
    status = Column(String(20), default="pending")
    metadata_json = Column(JSON, default=dict)
    steps_json = Column(JSON, default=list)
    current_step = Column(Integer, default=0)
    created_at = Column(Float, default=_ts)
    updated_at = Column(Float, default=_ts, onupdate=_ts)


class JobRequisition(Base):
    __tablename__ = "job_requisitions"

    id = Column(String(64), primary_key=True, default=_uuid)
    user_key = Column(String(64), nullable=False)
    title = Column(String(255), nullable=False)
    department = Column(String(100), default="")
    status = Column(String(20), default="open")
    created_at = Column(Float, default=_ts)


class FinanceAccount(Base):
    __tablename__ = "finance_accounts"

    id = Column(String(64), primary_key=True, default=_uuid)
    user_key = Column(String(64), nullable=False)
    student_name = Column(String(255), nullable=False)
    class_name = Column(String(20), default="")
    family_email = Column(String(255), default="")
    outstanding = Column(Float, default=0.0)
    overdue_days = Column(Integer, default=0)
    predicted_default = Column(Integer, default=0)
    scholarship = Column(Integer, default=0)
    created_at = Column(Float, default=_ts)


class FeeWaiver(Base):
    __tablename__ = "fee_waivers"

    id = Column(String(64), primary_key=True, default=_uuid)
    user_key = Column(String(64), nullable=False)
    student_name = Column(String(255), default="")
    class_name = Column(String(20), default="")
    family_email = Column(String(255), default="")
    amount = Column(Float, default=0.0)
    reason = Column(Text, default="")
    status = Column(String(20), default="pending")
    created_at = Column(Float, default=_ts)


class MonthlyCollection(Base):
    __tablename__ = "monthly_collections"

    id = Column(String(64), primary_key=True, default=_uuid)
    user_key = Column(String(64), nullable=False)
    month = Column(String(10), nullable=False)
    amount_lakhs = Column(Float, default=0.0)


class SchoolTarget(Base):
    __tablename__ = "school_targets"

    user_key = Column(String(64), primary_key=True)
    revenue_mtd = Column(Float, default=5200000)
    attendance = Column(Float, default=90.0)
    compliance = Column(Float, default=80.0)
    updated_at = Column(Float, default=_ts)


class AdmissionApplication(Base):
    __tablename__ = "admission_applications"

    id = Column(String(64), primary_key=True, default=_uuid)
    user_key = Column(String(64), nullable=False)
    student_name = Column(String(255), nullable=False)
    grade = Column(String(20), default="")
    stage = Column(String(20), default="Applied")
    score = Column(Integer, default=0)
    counselor = Column(String(255), default="")
    parent_name = Column(String(255), default="")
    parent_contact = Column(String(50), default="")
    date = Column(String(20), default="")
    student_id = Column(String(64), default="")
    removed_at = Column(Float, nullable=True)
    created_at = Column(Float, default=_ts)


class Student(Base):
    __tablename__ = "students"

    id = Column(String(64), primary_key=True, default=_uuid)
    user_key = Column(String(64), nullable=False)
    name = Column(String(255), nullable=False)
    class_name = Column(String(20), default="")
    roll = Column(String(20), default="")
    admission_no = Column(String(100), default="")
    gender = Column(String(10), default="")
    dob = Column(String(20), default="")
    house = Column(String(20), default="")
    risk_score = Column(Integer, default=0)
    risk_level = Column(String(20), default="Low")
    attendance = Column(Integer, default=100)
    fees_due = Column(Float, default=0.0)
    fees_status = Column(String(20), default="Cleared")
    gpa = Column(Float, default=0.0)
    parent_name = Column(String(255), default="")
    parent_phone = Column(String(50), default="")
    parent_email = Column(String(255), default="")
    parent_relation = Column(String(50), default="")
    blood_group = Column(String(10), default="")
    behavior = Column(Text, default="")
    recommendations_json = Column(JSON, default=list)
    achievements_json = Column(JSON, default=list)
    medical_json = Column(JSON, default=dict)
    timeline_json = Column(JSON, default=list)
    documents_json = Column(JSON, default=list)
    marks_json = Column(JSON, default=list)
    ai_summary = Column(Text, default="")
    admission_id = Column(String(64), default="")
    created_at = Column(Float, default=_ts)


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id = Column(String(64), primary_key=True, default=_uuid)
    user_key = Column(String(64), nullable=False)
    title = Column(String(255), nullable=False)
    date = Column(String(20), nullable=False)
    time = Column(String(20), default="")
    type = Column(String(20), default="Meeting")
    status = Column(String(20), default="Upcoming")
    created_at = Column(Float, default=_ts)


class HRPolicy(Base):
    __tablename__ = "hr_policies"

    id = Column(String(64), primary_key=True, default=_uuid)
    user_key = Column(String(64), nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(50), default="leave")  # leave, attendance, conduct, general, ...
    content = Column(Text, nullable=False)
    rules_json = Column(JSON, default=dict)
    active = Column(Integer, default=0)
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


class KnowledgeCard(Base):
    __tablename__ = "knowledge_cards"

    id = Column(String(64), primary_key=True, default=_uuid)
    user_key = Column(String(64), nullable=False)
    title = Column(String(255), nullable=False)
    card_type = Column(String(50), nullable=False)
    dept = Column(String(100), default="")
    status = Column(String(20), default="Current")
    summary = Column(Text, default="")
    relations = Column(Integer, default=0)
    updated_at = Column(String(20), default="")
    created_at = Column(Float, default=_ts)


class ComplianceEvidence(Base):
    __tablename__ = "compliance_evidence"

    id = Column(String(64), primary_key=True, default=_uuid)
    user_key = Column(String(64), nullable=False)
    title = Column(String(255), nullable=False)
    framework = Column(String(50), nullable=False)
    status = Column(String(20), default="Missing")
    category = Column(String(100), default="")
    last_updated = Column(String(20), default="—")
    notes = Column(Text, default="")
    file_path = Column(String(500), default="")
    source_name = Column(String(255), default="")
    owner = Column(String(100), default="")
    created_at = Column(Float, default=_ts)
    updated_at = Column(Float, default=_ts, onupdate=_ts)


# ─── Document Repository 2.0 ────────────────────────────────────────────

class Folder(Base):
    __tablename__ = "folders"

    id = Column(String(64), primary_key=True, default=_uuid)
    name = Column(String(255), nullable=False)
    parent_id = Column(String(64), ForeignKey("folders.id"), nullable=True)
    school_id = Column(String(64), ForeignKey("schools.id"), nullable=True)
    created_by = Column(String(255), default="")
    created_at = Column(Float, default=_ts)
    updated_at = Column(Float, default=_ts, onupdate=_ts)

    parent = relationship("Folder", remote_side="Folder.id", backref="children")


class RepositoryDocument(Base):
    __tablename__ = "repository_documents"

    id = Column(String(64), primary_key=True, default=_uuid)
    user_key = Column(String(64), nullable=False)
    name = Column(String(255), nullable=False)
    folder_id = Column(String(64), ForeignKey("folders.id"), nullable=True)
    file_hash = Column(String(64), default="")
    size = Column(Integer, default=0)
    mime_type = Column(String(100), default="application/octet-stream")
    current_version = Column(Integer, default=1)
    file_id = Column(String(64), nullable=True)

    category_id = Column(String(64), ForeignKey("document_categories.id"), nullable=True)
    department_id = Column(String(64), ForeignKey("departments.id"), nullable=True)
    tags = Column(JSON, default=list)
    owner_email = Column(String(255), default="")
    description = Column(Text, default="")

    is_favorite = Column(Integer, default=0)
    is_archived = Column(Integer, default=0)

    status = Column(String(20), default="active")  # active, trashed
    trashed_at = Column(Float, nullable=True)

    expiry_date = Column(String(20), default="")
    created_at = Column(Float, default=_ts)
    updated_at = Column(Float, default=_ts, onupdate=_ts)

    folder = relationship("Folder", backref="documents")
    category = relationship("DocumentCategory", backref="repository_documents")
    department = relationship("Department", backref="repository_documents")

    __table_args__ = (
        Index("idx_repo_docs_user", user_key, status, folder_id),
        Index("idx_repo_docs_hash", file_hash),
        Index("idx_repo_docs_favorite", user_key, is_favorite),
    )


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id = Column(String(64), primary_key=True, default=_uuid)
    document_id = Column(String(64), ForeignKey("repository_documents.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, default=0)
    file_hash = Column(String(64), default="")
    mime_type = Column(String(100), default="application/octet-stream")
    uploaded_by = Column(String(255), default="")
    change_notes = Column(Text, default="")
    created_at = Column(Float, default=_ts)

    document = relationship("RepositoryDocument", backref=backref("versions", cascade="all, delete-orphan"))

    __table_args__ = (
        Index("idx_doc_versions_doc", document_id, version_number.desc()),
    )


class DocumentComment(Base):
    __tablename__ = "document_comments"

    id = Column(String(64), primary_key=True, default=_uuid)
    document_id = Column(String(64), ForeignKey("repository_documents.id", ondelete="CASCADE"), nullable=False)
    user_email = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(Float, default=_ts)

    __table_args__ = (
        Index("idx_doc_comments_doc", document_id, created_at.desc()),
    )


# ─── End Document Repository 2.0 ────────────────────────────────────────


class DocumentTemplate(Base):
    __tablename__ = "document_templates"

    id = Column(String(64), primary_key=True, default=_uuid)
    doc_type = Column(String(100), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    is_active = Column(Integer, default=1)
    created_at = Column(Float, default=_ts)


class AIDraft(Base):
    __tablename__ = "ai_drafts"

    id = Column(String(64), primary_key=True, default=_uuid)
    user_key = Column(String(64), nullable=False, index=True)
    doc_type = Column(String(100), nullable=False)
    template_id = Column(String(64), default="")
    template_name = Column(String(255), default="")
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    department = Column(String(100), default="")
    academic_year = Column(String(20), default="")
    audience = Column(String(100), default="")
    topic = Column(String(255), default="")
    status = Column(String(20), default="draft")  # draft, published
    created_at = Column(Float, default=_ts)


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(String(64), primary_key=True, default=_uuid)
    user_email = Column(String(255), nullable=False, index=True)
    action = Column(String(50), nullable=False)  # login, logout, upload, delete, download, search, chat, approve
    resource_type = Column(String(50), default="")  # document, folder, chat, user, settings
    resource_id = Column(String(64), default="")
    resource_name = Column(String(255), default="")
    details = Column(Text, default="")
    ip_address = Column(String(50), default="")
    user_agent = Column(String(500), default="")
    department = Column(String(100), default="")
    created_at = Column(Float, default=_ts)

    __table_args__ = (
        Index("idx_activity_user", user_email, created_at.desc()),
        Index("idx_activity_action", action, created_at.desc()),
        Index("idx_activity_created", created_at.desc()),
    )


class StudentCommunication(Base):
    __tablename__ = "student_communications"

    id = Column(String(64), primary_key=True, default=_uuid)
    user_key = Column(String(64), nullable=False)
    student_id = Column(String(64), nullable=False)
    channel = Column(String(20), default="call")
    subject = Column(String(255), default="")
    body = Column(Text, default="")
    author = Column(String(255), default="")
    created_at = Column(Float, default=_ts)


class CoverageEntry(Base):
    __tablename__ = "coverage_entries"

    id = Column(String(64), primary_key=True, default=_uuid)
    user_key = Column(String(64), nullable=False)
    department = Column(String(100), nullable=False)
    class_name = Column(String(20), default="")
    coverage = Column(Integer, default=0)
    updated_at = Column(Float, default=_ts)


class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(String(64), primary_key=True, default=_uuid)
    user_key = Column(String(64), nullable=False)
    department = Column(String(100), default="")
    class_name = Column(String(20), default="")
    title = Column(String(255), default="")
    teacher = Column(String(255), default="")
    due_date = Column(String(20), default="")
    status = Column(String(20), default="scheduled")  # scheduled | graded
    created_at = Column(Float, default=_ts)


class ClassAttendance(Base):
    __tablename__ = "class_attendances"

    id = Column(String(64), primary_key=True, default=_uuid)
    user_key = Column(String(64), nullable=False)
    class_name = Column(String(20), nullable=False)
    date = Column(String(20), default="")
    present = Column(Integer, default=0)
    total = Column(Integer, default=0)
    recorded_at = Column(Float, default=_ts)


class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(String(64), primary_key=True, default=_uuid)
    user_key = Column(String(64), nullable=False)
    key = Column(String(64), default="")
    name = Column(String(255), nullable=False)
    color = Column(String(20), default="#1E3A5F")
    stages_json = Column(JSON, default=list)
    status = Column(String(20), default="draft")  # draft, published
    created_at = Column(Float, default=_ts)
    updated_at = Column(Float, default=_ts, onupdate=_ts)


class WorkflowInstance(Base):
    __tablename__ = "workflow_instances"

    id = Column(String(64), primary_key=True, default=_uuid)
    workflow_id = Column(String(64), ForeignKey("workflows.id"), nullable=False)
    title = Column(String(255), nullable=False)
    current_stage = Column(Integer, default=0)
    status = Column(String(20), default="open")  # open, done, cancelled
    created_at = Column(Float, default=_ts)
    updated_at = Column(Float, default=_ts, onupdate=_ts)


class Role(Base):
    __tablename__ = "roles"

    id = Column(String(64), primary_key=True, default=_uuid)
    user_key = Column(String(64), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    permissions = Column(JSON, default=list)
    users = Column(Integer, default=0)
    created_at = Column(Float, default=_ts)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    token = Column(String(128), primary_key=True)
    email = Column(String(255), nullable=False, index=True)
    expires_at = Column(Float, nullable=False)
    created_at = Column(Float, default=_ts)

    __table_args__ = (
        Index("idx_reset_tokens_email", email),
        Index("idx_reset_tokens_expires", expires_at),
    )


class AppSetting(Base):
    __tablename__ = "app_settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, default="")
    updated_at = Column(Float, default=_ts, onupdate=_ts)
