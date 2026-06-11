"""
Skolaz v2.0 — Super Admin Blueprint
Executive dashboard, user management, system config, audit log
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.extensions import db, bcrypt
from app.models.user import User, Role
from app.models.student import Student
from app.models.application import Application
from app.models.agency import Agency
from app.models.institution import School, Program
from app.models.commission import Commission
from app.models.audit import AuditLog
from app.models.system import SystemSetting
from app.utils.decorators import super_admin_required
from app.utils.helpers import get_page_args, Paginator

super_admin_bp = Blueprint("super_admin", __name__)


@super_admin_bp.before_request
def require_super_admin():
    from flask_login import current_user
    from flask import redirect, url_for, abort, request as req
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login", next=req.url))
    if not current_user.is_active_account:
        abort(403)
    if not current_user.is_super_admin:
        abort(403)


# ── Dashboard ─────────────────────────────────────────────────────────────────

@super_admin_bp.get("/")
def dashboard():
    stats = {
        "total_students":   Student.query.count(),
        "total_applications": Application.query.count(),
        "total_schools":    School.query.filter_by(status="active").count(),
        "total_agencies":   Agency.query.filter_by(status="approved").count(),
        "total_users":      User.query.filter_by(is_deleted=False).count(),
        "active_programs":  Program.query.filter_by(status="active").count(),
        "visa_approved":    Application.query.filter_by(current_stage="visa_approved").count(),
        "enrolled":         Application.query.filter_by(current_stage="enrolled").count(),
    }

    recent_students = Student.query.order_by(Student.created_at.desc()).limit(5).all()
    recent_apps     = Application.query.order_by(Application.created_at.desc()).limit(5).all()
    recent_audits   = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(10).all()

    return render_template(
        "super_admin/dashboard.html",
        stats=stats,
        recent_students=recent_students,
        recent_apps=recent_apps,
        recent_audits=recent_audits,
    )


# ── User Management ───────────────────────────────────────────────────────────

@super_admin_bp.get("/users")
def users():
    page, per_page = get_page_args()
    q      = request.args.get("q", "")
    role   = request.args.get("role", "")
    status = request.args.get("status", "")

    query = User.query.filter_by(is_deleted=False)
    if q:
        query = query.filter(
            db.or_(User.email.ilike(f"%{q}%"),
                   User.first_name.ilike(f"%{q}%"),
                   User.last_name.ilike(f"%{q}%"))
        )
    if role:
        query = query.join(User.role).filter(Role.slug == role)
    if status:
        query = query.filter(User.status == status)

    paginator = Paginator(query.order_by(User.created_at.desc()), page, per_page)
    roles = Role.query.all()

    if request.headers.get("HX-Request"):
        return render_template("super_admin/_users_table.html",
                               paginator=paginator, q=q, role=role)

    return render_template("super_admin/users.html",
                           paginator=paginator, roles=roles, q=q, role=role, status=status)


@super_admin_bp.get("/users/create")
def create_user():
    roles = Role.query.all()
    return render_template("super_admin/user_form.html", roles=roles, user=None)


@super_admin_bp.post("/users/create")
def create_user_post():
    data = request.form
    role = Role.query.get(data.get("role_id"))
    if not role:
        flash("Invalid role selected.", "error")
        return redirect(url_for("super_admin.create_user"))

    if User.query.filter_by(email=data["email"].lower()).first():
        flash("A user with that email already exists.", "error")
        return redirect(url_for("super_admin.create_user"))

    user = User(
        email=data["email"].strip().lower(),
        password_hash=bcrypt.generate_password_hash(data["password"]).decode(),
        first_name=data["first_name"].strip(),
        last_name=data["last_name"].strip(),
        phone=data.get("phone", "").strip(),
        role_id=role.id,
        status="active",
    )
    db.session.add(user)
    db.session.commit()
    flash(f"User {user.full_name} created successfully.", "success")
    return redirect(url_for("super_admin.users"))


@super_admin_bp.get("/users/<int:user_id>")
def user_detail(user_id):
    user = User.query.get_or_404(user_id)
    roles = Role.query.all()
    return render_template("super_admin/user_detail.html", user=user, roles=roles)


@super_admin_bp.post("/users/<int:user_id>/toggle-status")
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)
    user.status = "inactive" if user.status == "active" else "active"
    db.session.commit()
    flash(f"User {user.full_name} is now {user.status}.", "success")
    return redirect(url_for("super_admin.user_detail", user_id=user_id))


@super_admin_bp.post("/users/<int:user_id>/change-role")
def change_user_role(user_id):
    """Change a user's role. Super admin role cannot be assigned here."""
    user    = User.query.get_or_404(user_id)
    role_id = request.form.get("role_id", type=int)

    if not role_id:
        flash("Please select a valid role.", "error")
        return redirect(url_for("super_admin.user_detail", user_id=user_id))

    new_role = Role.query.get(role_id)
    if not new_role:
        flash("Role not found.", "error")
        return redirect(url_for("super_admin.user_detail", user_id=user_id))

    # Guard: cannot assign super_admin through this form
    if new_role.slug == "super_admin":
        flash("Super Admin role cannot be assigned through this interface.", "error")
        return redirect(url_for("super_admin.user_detail", user_id=user_id))

    # Guard: cannot change your own role
    if user.id == current_user.id:
        flash("You cannot change your own role.", "error")
        return redirect(url_for("super_admin.user_detail", user_id=user_id))

    old_role_name = user.role.name
    user.role_id  = new_role.id
    db.session.commit()

    # Audit log
    from app.services.audit_service import log_action
    log_action("user.role_changed", "users", current_user.id,
               user.id, "User",
               f"Role changed from {old_role_name} to {new_role.name}",
               ip=request.remote_addr)

    flash(f"{user.full_name}'s role changed from {old_role_name} to {new_role.name}.", "success")
    return redirect(url_for("super_admin.user_detail", user_id=user_id))


# ── Agency Approvals ──────────────────────────────────────────────────────────

@super_admin_bp.get("/agencies")
def agencies():
    page, per_page = get_page_args()
    status = request.args.get("status", "")
    query  = Agency.query
    if status:
        query = query.filter_by(status=status)
    paginator = Paginator(query.order_by(Agency.created_at.desc()), page, per_page)
    return render_template("super_admin/agencies.html", paginator=paginator, status=status)


@super_admin_bp.post("/agencies/<int:agency_id>/approve")
def approve_agency(agency_id):
    agency = Agency.query.get_or_404(agency_id)
    agency.status = "approved"
    agency.approved_by = current_user.id
    from datetime import datetime, timezone
    agency.approved_at = datetime.now(timezone.utc)
    db.session.commit()
    flash(f"Agency '{agency.name}' approved.", "success")
    return redirect(url_for("super_admin.agencies"))


@super_admin_bp.post("/agencies/<int:agency_id>/suspend")
def suspend_agency(agency_id):
    agency = Agency.query.get_or_404(agency_id)
    agency.status = "suspended"
    db.session.commit()
    flash(f"Agency '{agency.name}' suspended.", "warning")
    return redirect(url_for("super_admin.agencies"))


# ── Audit Log ─────────────────────────────────────────────────────────────────

@super_admin_bp.get("/audit-log")
def audit_log():
    page, per_page = get_page_args()
    query = AuditLog.query.order_by(AuditLog.created_at.desc())
    paginator = Paginator(query, page, per_page)
    return render_template("super_admin/audit_log.html", paginator=paginator)


# ── System Settings ───────────────────────────────────────────────────────────

@super_admin_bp.get("/settings")
def settings():
    settings_dict = {
        "maintenance_mode": SystemSetting.get("maintenance_mode", False),
        "allow_public_registration": SystemSetting.get("allow_public_registration", True),
        "aws_bucket": SystemSetting.get("aws_bucket", "skolaz-prod-assets"),
        "sendgrid_key": SystemSetting.get("sendgrid_key", "************************")
    }
    return render_template("super_admin/settings.html", settings=settings_dict)


@super_admin_bp.post("/settings")
def settings_post():
    SystemSetting.set("maintenance_mode", request.form.get("maintenance_mode") == "on", type="boolean")
    SystemSetting.set("allow_public_registration", request.form.get("allow_public_registration") == "on", type="boolean")
    SystemSetting.set("aws_bucket", request.form.get("aws_bucket", ""), type="string")
    SystemSetting.set("sendgrid_key", request.form.get("sendgrid_key", ""), type="string")
    
    flash("Settings saved successfully.", "success")
    return redirect(url_for("super_admin.settings"))
