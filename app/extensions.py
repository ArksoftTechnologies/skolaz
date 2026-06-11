"""
Skolaz v2.0 — Flask Extensions
All extension instances live here to avoid circular imports.
Import from here everywhere else, not from flask_* directly.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_wtf.csrf import CSRFProtect
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO

# ── Database ─────────────────────────────────────────────────
db = SQLAlchemy()

# ── Migrations ───────────────────────────────────────────────
migrate = Migrate()

# ── Authentication ───────────────────────────────────────────
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "warning"
login_manager.session_protection = "strong"

# ── Password Hashing ─────────────────────────────────────────
bcrypt = Bcrypt()

# ── CSRF Protection ──────────────────────────────────────────
csrf = CSRFProtect()

# ── JWT ──────────────────────────────────────────────────────
jwt = JWTManager()

# ── WebSockets ───────────────────────────────────────────────
socketio = SocketIO(
    cors_allowed_origins="*",
    async_mode="eventlet",
    logger=False,
    engineio_logger=False,
)
