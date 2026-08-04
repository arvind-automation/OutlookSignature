import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://root:rootpass@localhost:3306/digitalsignature_arvind",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
    }
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    INIT_DB_STRICT_ASSETS = os.getenv("INIT_DB_STRICT_ASSETS", "0") == "1"
    INIT_DB_ALLOW_RESET = os.getenv("INIT_DB_ALLOW_RESET", "0") == "1"
    DEMO_PASSWORD = "123456789"
    ALLOWED_EMAIL_SUFFIXES = ("@arvind.in", "@arvind.com", "@arvindlimited.com")
    TEAM_LABELS = {
        "gcc": "Standard Template",
        "sales": "Hierarchy Template",
    }
    ALLOWED_TEAMS = frozenset(TEAM_LABELS.keys())
    ALLOWED_TEMPLATES = frozenset({"standard", "compact", "minimal"})
    APP_BASE_URL = (os.getenv("APP_BASE_URL") or "http://localhost:5000").rstrip("/")
    AZURE_CLIENT_ID = (os.getenv("AZURE_CLIENT_ID") or "").strip()
    AZURE_CLIENT_SECRET = (os.getenv("AZURE_CLIENT_SECRET") or "").strip()
    AZURE_TENANT_ID = (os.getenv("AZURE_TENANT_ID") or "").strip()
    MICROSOFT_SSO_ENABLED = (
        os.getenv("MICROSOFT_SSO_ENABLED", "0") == "1"
        and bool(AZURE_CLIENT_ID and AZURE_CLIENT_SECRET and AZURE_TENANT_ID)
    )
    MICROSOFT_SSO_SCOPES = ["User.Read"]

