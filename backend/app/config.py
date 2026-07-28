import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / '.env')


class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY")
    PORT = int(os.getenv("PORT", 5000))


class AuthConfig:
    USERS = {
        "admin@ceap.school": "demo1234",
        "user@ceap.school": "password123",
    }


class OneDriveConfig:
    CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
    CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
    TENANT_ID = os.getenv("AZURE_TENANT_ID", "common")
    REDIRECT_URI = os.getenv(
        "AZURE_REDIRECT_URI", "http://localhost:5000/auth/callback"
    )
    AUTHORITY = (
        f"https://login.microsoftonline.com/{os.getenv('AZURE_TENANT_ID', 'common')}"
    )
    SCOPES = ["Files.Read", "Files.Read.All", "User.Read"]

    @classmethod
    def is_enabled(cls):
        return bool(cls.CLIENT_ID and cls.CLIENT_SECRET)


class GeminiConfig:
    API_KEY = os.getenv("GEMINI_API_KEY")
    MODEL = "gemini-3.5-flash-lite"


class DBConfig:
    URL = os.getenv("DB_URI") or os.getenv("DATABASE_URL") or ""
    ECHO = os.getenv("DB_ECHO", "0") == "1"


class RAGConfig:
    CHUNK_SIZE = 800
    CHUNK_OVERLAP = 150
    TOP_K = 6
    RRF_K = 60


class SchoolConfig:
    DEFAULT_SCHOOL_NAME = os.getenv("SCHOOL_NAME", "Demo School")
    DEFAULT_SCHOOL_CODE = os.getenv("SCHOOL_CODE", "DEMO001")
    DEFAULT_ADMIN_EMAIL = os.getenv("SCHOOL_ADMIN_EMAIL", "admin@ceap.school")
    SCHOOL_ROLES = {
        "admin": "Administrator",
        "principal": "Principal",
        "vice_principal": "Vice Principal",
        "coordinator": "Coordinator",
        "teacher": "Teacher",
        "accountant": "Accountant",
        "hr": "HR Officer",
        "it_admin": "IT Admin",
    }


class OfficeConfig:
    OCR_ENABLED = os.getenv("OCR_ENABLED", "1") == "1"
    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASS = os.getenv("SMTP_PASS", "")
    SMTP_FROM = os.getenv("SMTP_FROM", "noreply@ceap.school")
    NOTIFICATIONS_ENABLED = os.getenv("NOTIFICATIONS_ENABLED", "1") == "1"
