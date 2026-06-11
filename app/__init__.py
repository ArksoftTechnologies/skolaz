"""
Skolaz v2.0 — Flask Application Factory
"""
import os
import logging
from flask import Flask
from config import get_config
from app.extensions import db, migrate, login_manager, bcrypt, csrf, jwt, socketio


def create_app(env: str = None) -> Flask:
    """
    Application factory.
    Creates and configures the Flask app for the given environment.
    """
    # Use absolute paths so Vercel's /var/task layout resolves correctly.
    # Vercel bundles everything from the project root, so templates live at
    # /var/task/templates/ (top-level copy) rather than /var/task/app/templates/
    _package_dir = os.path.dirname(os.path.abspath(__file__))
    _project_root = os.path.dirname(_package_dir)

    # Prefer top-level templates/ (works on Vercel); fall back to app/templates/
    _top_level_templates = os.path.join(_project_root, "templates")
    _app_templates       = os.path.join(_package_dir,  "templates")
    _template_folder     = _top_level_templates if os.path.isdir(_top_level_templates) else _app_templates

    app = Flask(
        __name__,
        template_folder=_template_folder,
        static_folder=os.path.join(_package_dir, "static"),
    )

    # ── Load Configuration ────────────────────────────────────
    cfg = get_config(env)
    app.config.from_object(cfg)

    # ── Ensure Upload Folder Exists ───────────────────────────
    # On Vercel the task root is read-only; use /tmp instead
    upload_folder = app.config.get("UPLOAD_FOLDER", "uploads")
    if os.environ.get("VERCEL") or not os.access(os.path.dirname(os.path.abspath(upload_folder)) or ".", os.W_OK):
        upload_folder = "/tmp/uploads"
        app.config["UPLOAD_FOLDER"] = upload_folder
    try:
        os.makedirs(upload_folder, exist_ok=True)
    except OSError:
        # Truly read-only environment (Vercel lambda) — skip silently
        app.config["UPLOAD_FOLDER"] = "/tmp/uploads"

    # ── Initialise Extensions ────────────────────────────────
    _init_extensions(app)

    # ── Auto-run migrations (needed on Vercel / fresh deployments) ──
    _run_migrations(app)

    # ── Register Blueprints ───────────────────────────────────
    _register_blueprints(app)

    # ── Register Error Handlers ───────────────────────────────
    _register_error_handlers(app)

    # ── Register Template Globals / Filters ───────────────────
    _register_template_helpers(app)

    # ── Configure Logging ─────────────────────────────────────
    _configure_logging(app)

    # ── Register Socket.IO Events ─────────────────────────────
    _register_socketio_events(app)

    return app


# ── Private helpers ───────────────────────────────────────────────────────────

def _run_migrations(app: Flask) -> None:
    """Run any pending Alembic migrations automatically on startup.
    Safe to call multiple times — only applies pending changes."""
    try:
        from flask_migrate import upgrade as flask_migrate_upgrade
        with app.app_context():
            flask_migrate_upgrade()
            _seed_initial_data()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Migration/seed warning: {e}")


def _seed_initial_data() -> None:
    """Create roles and super admin on first boot if they don't exist."""
    from app.models.user import Role, User
    from app.extensions import bcrypt as _bcrypt

    roles_data = [
        {"name": "Super Admin",   "slug": "super_admin",   "description": "Full system access"},
        {"name": "Staff",         "slug": "staff",          "description": "Internal application processing staff"},
        {"name": "Advisor",       "slug": "advisor",        "description": "Student counselor and advisor"},
        {"name": "Data Entry",    "slug": "data_entry",     "description": "Catalog and data management"},
        {"name": "Agency Owner",  "slug": "agency",         "description": "Owner of a partner agency"},
        {"name": "Agency Member", "slug": "agency_member",  "description": "Agent working for a partner agency"},
        {"name": "Student",       "slug": "student",        "description": "Standard student applicant"},
    ]
    for rd in roles_data:
        if not Role.query.filter_by(slug=rd["slug"]).first():
            db.session.add(Role(**rd))
    db.session.commit()

    admin_email = "admin@skolaz.com"
    if not User.query.filter_by(email=admin_email).first():
        admin_role = Role.query.filter_by(slug="super_admin").first()
        if admin_role:
            admin = User(
                first_name="Super", last_name="Admin",
                email=admin_email, role_id=admin_role.id, status="active"
            )
            admin.set_password("Admin123!")
            db.session.add(admin)
            db.session.commit()


def _init_extensions(app: Flask) -> None:
    """Initialise all Flask extensions with the app instance."""
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)
    jwt.init_app(app)
    socketio.init_app(
        app,
        async_mode=app.config.get("SOCKETIO_ASYNC_MODE", "threading"),
        cors_allowed_origins="*",
    )

    # Tell Flask-Login how to load a user from the session
    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id: str):
        return User.query.get(int(user_id))


def _register_blueprints(app: Flask) -> None:
    """Register all application blueprints."""

    # ── Public & Core ─────────────────────────────────────────
    from app.routes.public import public_bp
    from app.routes.auth import auth_bp
    from app.routes.api import api_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(api_bp, url_prefix="/api")

    # ── Internal Portals ──────────────────────────────────────
    from app.routes.super_admin import super_admin_bp
    from app.routes.staff import staff_bp
    from app.routes.advisor import advisor_bp
    from app.routes.data_entry import data_entry_bp

    app.register_blueprint(super_admin_bp, url_prefix="/admin")
    app.register_blueprint(staff_bp, url_prefix="/staff")
    app.register_blueprint(advisor_bp, url_prefix="/advisor")
    app.register_blueprint(data_entry_bp, url_prefix="/data-entry")

    # ── External Portals ──────────────────────────────────────
    from app.routes.agency import agency_bp
    from app.routes.student_portal import student_portal_bp

    app.register_blueprint(agency_bp, url_prefix="/agency")
    app.register_blueprint(student_portal_bp, url_prefix="/portal")

    # ── Feature Modules ───────────────────────────────────────
    from app.routes.institutions import institutions_bp
    from app.routes.applications import applications_bp
    from app.routes.offers import offers_bp
    from app.routes.documents import documents_bp
    from app.routes.students import students_bp
    from app.routes.commissions import commissions_bp
    from app.routes.reports import reports_bp

    app.register_blueprint(institutions_bp, url_prefix="/institutions")
    app.register_blueprint(applications_bp, url_prefix="/applications")
    app.register_blueprint(offers_bp, url_prefix="/offers")
    app.register_blueprint(documents_bp, url_prefix="/documents")
    app.register_blueprint(students_bp, url_prefix="/students")
    app.register_blueprint(commissions_bp, url_prefix="/commissions")
    app.register_blueprint(reports_bp, url_prefix="/reports")


def _register_error_handlers(app: Flask) -> None:
    """Register custom HTTP error page handlers."""
    from flask import render_template, jsonify, request

    def _wants_json():
        return request.path.startswith("/api/") or \
               request.accept_mimetypes.best == "application/json"

    @app.errorhandler(400)
    def bad_request(e):
        if _wants_json():
            return jsonify(success=False, message="Bad request", errors=[str(e)]), 400
        return render_template("errors/400.html", error=e), 400

    @app.errorhandler(403)
    def forbidden(e):
        if _wants_json():
            return jsonify(success=False, message="Forbidden", errors=[str(e)]), 403
        return render_template("errors/403.html", error=e), 403

    @app.errorhandler(404)
    def not_found(e):
        if _wants_json():
            return jsonify(success=False, message="Not found", errors=[str(e)]), 404
        return render_template("errors/404.html", error=e), 404

    @app.errorhandler(429)
    def rate_limited(e):
        if _wants_json():
            return jsonify(success=False, message="Rate limit exceeded", errors=[str(e)]), 429
        return render_template("errors/429.html", error=e), 429

    @app.errorhandler(500)
    def server_error(e):
        if _wants_json():
            return jsonify(success=False, message="Internal server error", errors=[str(e)]), 500
        return render_template("errors/500.html", error=e), 500


def _register_template_helpers(app: Flask) -> None:
    """Register Jinja2 globals and filters."""
    from datetime import datetime, timezone

    @app.template_global()
    def current_year():
        return datetime.now(timezone.utc).year

    @app.template_global()
    def now():
        return datetime.now(timezone.utc)

    @app.template_global()
    def role_dashboard_url():
        """Returns the correct home dashboard URL for the current logged-in user."""
        from flask_login import current_user
        from flask import url_for
        if not current_user.is_authenticated:
            return url_for("public.home")
        mapping = {
            "super_admin":   url_for("super_admin.dashboard"),
            "staff":         url_for("staff.dashboard"),
            "advisor":       url_for("advisor.dashboard"),
            "data_entry":    url_for("data_entry.dashboard"),
            "agency":        url_for("agency.dashboard"),
            "agency_member": url_for("agency.dashboard"),
            "agency_owner":  url_for("agency.dashboard"),
            "agency_agent":  url_for("agency.dashboard"),
            "student":       url_for("student_portal.dashboard"),
        }
        return mapping.get(current_user.role.slug, url_for("public.home"))

    @app.template_global()
    def app_version():
        return app.config.get("APP_VERSION", "2.0.0")

    @app.template_filter("timeago")
    def timeago_filter(dt):
        if not dt:
            return ""
        from datetime import timezone
        now = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        diff = now - dt
        seconds = int(diff.total_seconds())
        if seconds < 60:
            return "just now"
        elif seconds < 3600:
            return f"{seconds // 60}m ago"
        elif seconds < 86400:
            return f"{seconds // 3600}h ago"
        elif seconds < 604800:
            return f"{seconds // 86400}d ago"
        else:
            return dt.strftime("%b %d, %Y")

    @app.template_filter("currency")
    def currency_filter(value, symbol="$"):
        try:
            return f"{symbol}{float(value):,.2f}"
        except (ValueError, TypeError):
            return value

    @app.template_filter("initials")
    def initials_filter(name: str) -> str:
        parts = (name or "").split()
        return "".join(p[0].upper() for p in parts[:2]) if parts else "??"

    @app.template_global()
    def sidebar_link(title, url, icon_svg, active=False):
        from markupsafe import Markup
        active_class = "nav-item active" if active else "nav-item"
        svg_wrapped = f'<svg class="nav-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">{icon_svg}</svg>'
        html = f'<a href="{url}" class="{active_class}">{svg_wrapped}<span>{title}</span></a>'
        return Markup(html)


def _configure_logging(app: Flask) -> None:
    """Set up structured logging."""
    log_level = getattr(logging, app.config.get("LOG_LEVEL", "INFO").upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    app.logger.setLevel(log_level)


def _register_socketio_events(app: Flask) -> None:
    """Import Socket.IO event handlers (registers them on import)."""
    with app.app_context():
        import app.sockets  # noqa: F401
