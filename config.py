"""
Skolaz v2.0 — Configuration
Three environment configs: Development, Testing, Production
All secrets loaded from environment variables via python-dotenv
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv()


class BaseConfig:
    """Shared configuration across all environments."""

    # ── App Identity ─────────────────────────────────────────
    APP_NAME = os.environ.get("APP_NAME", "Skolaz")
    APP_VERSION = os.environ.get("APP_VERSION", "2.0.0")
    APP_URL = os.environ.get("APP_URL", "http://localhost:5000")

    # ── Security ─────────────────────────────────────────────
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
    WTF_CSRF_ENABLED = True
    WTF_CSRF_SECRET_KEY = os.environ.get("WTF_CSRF_SECRET_KEY", SECRET_KEY)
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
    PERMANENT_SESSION_LIFETIME = timedelta(
        seconds=int(os.environ.get("PERMANENT_SESSION_LIFETIME", 86400))
    )

    # ── Database ─────────────────────────────────────────────
    # Vercel: read-only fs, use /tmp for SQLite fallback (ephemeral)
    _default_db = (
        "sqlite:////tmp/skolaz_dev.db"
        if os.environ.get("VERCEL")
        else "sqlite:///skolaz_dev.db"
    )
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", _default_db)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }

    # ── JWT ──────────────────────────────────────────────────
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        seconds=int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRES", 900))
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        seconds=int(os.environ.get("JWT_REFRESH_TOKEN_EXPIRES", 2592000))
    )
    JWT_TOKEN_LOCATION = ["headers", "cookies"]
    JWT_COOKIE_SECURE = SESSION_COOKIE_SECURE
    JWT_COOKIE_CSRF_PROTECT = True

    # ── File Uploads ─────────────────────────────────────────
    STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "local")
    UPLOAD_FOLDER = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        os.environ.get("UPLOAD_FOLDER", "uploads"),
    )
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 26214400))
    ALLOWED_EXTENSIONS = {
        "image": {"png", "jpg", "jpeg", "gif", "webp", "svg"},
        "document": {"pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx"},
        "archive": {"zip", "rar"},
    }

    # ── AWS S3 ───────────────────────────────────────────────
    AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
    AWS_S3_BUCKET = os.environ.get("AWS_S3_BUCKET")
    AWS_S3_REGION = os.environ.get("AWS_S3_REGION", "us-east-1")

    # ── Cloudflare R2 ────────────────────────────────────────
    R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID")
    R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY")
    R2_BUCKET = os.environ.get("R2_BUCKET")
    R2_ENDPOINT_URL = os.environ.get("R2_ENDPOINT_URL")

    # ── Email ────────────────────────────────────────────────
    MAIL_PROVIDER = os.environ.get("MAIL_PROVIDER", "smtp")
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "1") == "1"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "noreply@skolaz.com")
    SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
    MAILGUN_API_KEY = os.environ.get("MAILGUN_API_KEY")
    MAILGUN_DOMAIN = os.environ.get("MAILGUN_DOMAIN")

    # ── Twilio (SMS / WhatsApp) ───────────────────────────────
    TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
    TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")
    TWILIO_WHATSAPP_NUMBER = os.environ.get("TWILIO_WHATSAPP_NUMBER")

    # ── MFA ──────────────────────────────────────────────────
    MFA_ISSUER_NAME = os.environ.get("MFA_ISSUER_NAME", "Skolaz")

    # ── Socket.IO ────────────────────────────────────────────
    SOCKETIO_ASYNC_MODE = os.getenv("SOCKETIO_ASYNC_MODE", "threading")

    # ── AI (Phase 3) ─────────────────────────────────────────
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    GOOGLE_GEMINI_API_KEY = os.environ.get("GOOGLE_GEMINI_API_KEY")

    # ── Logging ──────────────────────────────────────────────
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    SENTRY_DSN = os.environ.get("SENTRY_DSN")


class DevelopmentConfig(BaseConfig):
    """Development environment — verbose, SQLite, debug on."""

    DEBUG = True
    TESTING = False
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///skolaz_dev.db"
    )
    SQLALCHEMY_ECHO = False  # Set True to log SQL queries
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_SECURE = False
    JWT_COOKIE_SECURE = False
    LOG_LEVEL = "DEBUG"


class TestingConfig(BaseConfig):
    """Testing environment — in-memory DB, CSRF off."""

    DEBUG = False
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    JWT_COOKIE_SECURE = False
    SESSION_COOKIE_SECURE = False
    SERVER_NAME = "localhost"
    # Speed up bcrypt for tests
    BCRYPT_LOG_ROUNDS = 4


class ProductionConfig(BaseConfig):
    """Production environment — strict security, PostgreSQL required."""

    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    JWT_COOKIE_SECURE = True
    WTF_CSRF_ENABLED = True

    @classmethod
    def validate(cls):
        """Raise if critical production vars are missing."""
        required = ["SECRET_KEY", "DATABASE_URL", "JWT_SECRET_KEY"]
        missing = [k for k in required if not os.environ.get(k)]
        if missing:
            raise ValueError(
                f"Missing required production environment variables: {missing}"
            )


# ── Config registry ──────────────────────────────────────────
config_map = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}


def get_config(env: str = None) -> BaseConfig:
    """Return config class for the given environment name."""
    env = env or os.environ.get("FLASK_ENV", "development")
    return config_map.get(env, DevelopmentConfig)
