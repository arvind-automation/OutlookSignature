import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


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
    ALLOWED_EMAIL_SUFFIXES = ("@arvind.in", "@arvind.com", "@arvindlimited.com", "@arvindgcc.com")
    TEAM_LABELS = {
        "gcc": "Standard Template",
        "sales": "Hierarchy Template",
    }
    ALLOWED_TEAMS = frozenset(TEAM_LABELS.keys())
    ALLOWED_TEMPLATES = frozenset(
        {
            "standard",
            "logo-sidebar",
        }
    )
    APP_BASE_URL = (os.getenv("APP_BASE_URL") or "http://localhost:5000").rstrip("/")
    # Public HTTPS origin that serves this application's /static assets.
    # Local/data URLs are deliberately excluded from copied signatures.
    PUBLIC_ASSET_BASE_URL = (os.getenv("PUBLIC_ASSET_BASE_URL") or "").rstrip("/")
    AZURE_CLIENT_ID = (os.getenv("AZURE_CLIENT_ID") or "").strip()
    AZURE_CLIENT_SECRET = (os.getenv("AZURE_CLIENT_SECRET") or "").strip()
    AZURE_TENANT_ID = (os.getenv("AZURE_TENANT_ID") or "").strip()
    MICROSOFT_SSO_ENABLED = (
        env_flag("MICROSOFT_SSO_ENABLED")
        and bool(AZURE_CLIENT_ID and AZURE_CLIENT_SECRET and AZURE_TENANT_ID)
    )
    MICROSOFT_SSO_SCOPES = ["User.Read", "User.Read.All"]
    LOCAL_DEV_LOGIN_ENABLED = (
        FLASK_ENV == "development"
        and not MICROSOFT_SSO_ENABLED
        and env_flag("LOCAL_DEV_LOGIN_ENABLED")
    )
    LOCAL_DEV_EMAIL = (os.getenv("LOCAL_DEV_EMAIL") or "local.user@arvind.in").strip().lower()
