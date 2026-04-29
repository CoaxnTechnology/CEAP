import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY")
    PORT = int(os.getenv("PORT", 5000))


class AuthConfig:
    USERS = {
        "admin@documind.ai": "demo1234",
        "user@example.com": "password123",
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
    MODEL = "gemini-2.5-flash"


class RAGConfig:
    CHUNK_SIZE = 800
    CHUNK_OVERLAP = 150
    TOP_K = 6
    RRF_K = 60
