"""
Skolaz v2.0 — Auth Blueprint
Login, logout, register, MFA setup, password reset
Features: role-based dashboard redirect, confirm password, 5-attempt lockout (10 min)
"""
from datetime import datetime, timezone, timedelta
from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, jsonify, session, current_app)
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db, bcrypt
from app.models.user import User, Role
from app.models.student import Student
from app.models.system import SystemSetting

auth_bp = Blueprint("auth", __name__, template_folder="../templates/auth")

# ── Lockout constants ──────────────────────────────────────────
MAX_ATTEMPTS   = 5
LOCKOUT_MINUTES = 10


def _lockout_key(email: str) -> str:
    return f"login_attempts_{email.lower()}"


def _is_locked_out(email: str) -> tuple[bool, int]:
    """Returns (is_locked, seconds_remaining)."""
    key        = _lockout_key(email)
    attempts   = session.get(key, 0)
    locked_at  = session.get(f"{key}_locked_at")

    if attempts >= MAX_ATTEMPTS and locked_at:
        locked_dt = datetime.fromisoformat(locked_at)
        elapsed   = (datetime.now(timezone.utc) - locked_dt).total_seconds()
        remaining = int(LOCKOUT_MINUTES * 60 - elapsed)
        if remaining > 0:
            return True, remaining
        # Lockout expired — reset
        session.pop(key, None)
        session.pop(f"{key}_locked_at", None)

    return False, 0


def _record_failed_attempt(email: str):
    key      = _lockout_key(email)
    attempts = session.get(key, 0) + 1
    session[key] = attempts
    if attempts >= MAX_ATTEMPTS:
        session[f"{key}_locked_at"] = datetime.now(timezone.utc).isoformat()


def _clear_attempts(email: str):
    key = _lockout_key(email)
    session.pop(key, None)
    session.pop(f"{key}_locked_at", None)


# ── Login ─────────────────────────────────────────────────────────────────────

@auth_bp.get("/login")
def login():
    if current_user.is_authenticated:
        return redirect(_role_dashboard())
    return render_template("auth/login.html")


@auth_bp.post("/login")
def login_post():
    email    = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    remember = bool(request.form.get("remember"))

    # ── Lockout check ─────────────────────────────────────────
    locked, remaining = _is_locked_out(email)
    if locked:
        mins = remaining // 60
        secs = remaining % 60
        msg  = f"Account temporarily locked. Try again in {mins}m {secs}s."
        if request.headers.get("HX-Request"):
            return render_template("auth/_login_error.html", message=msg), 429
        flash(msg, "error")
        return render_template("auth/login.html", email=email, locked=True,
                               remaining=remaining), 429

    user = User.query.filter_by(email=email, is_deleted=False).first()

    if not user or not bcrypt.check_password_hash(user.password_hash, password):
        _record_failed_attempt(email)
        attempts_left = MAX_ATTEMPTS - session.get(_lockout_key(email), 0)
        msg = "Invalid email or password."
        if attempts_left > 0:
            msg += f" {attempts_left} attempt(s) remaining before lockout."
        else:
            msg = f"Too many failed attempts. Account locked for {LOCKOUT_MINUTES} minutes."
        if request.headers.get("HX-Request"):
            return render_template("auth/_login_error.html", message=msg), 401
        flash(msg, "error")
        return render_template("auth/login.html", email=email), 401

    if not user.is_active_account:
        flash("Your account is inactive. Contact support.", "error")
        return render_template("auth/login.html", email=email), 403

    # ── Success ───────────────────────────────────────────────
    _clear_attempts(email)

    if user.mfa_enabled:
        session["mfa_user_id"] = user.id
        session["mfa_remember"] = remember
        return redirect(url_for("auth.mfa_verify"))

    login_user(user, remember=remember)
    user.record_login(request.remote_addr)

    next_page = request.args.get("next") or _role_dashboard()
    return redirect(next_page)


# ── Signup ────────────────────────────────────────────────────────────────────

@auth_bp.get("/signup")
def signup():
    if current_user.is_authenticated:
        return redirect(_role_dashboard())
    if not SystemSetting.get("allow_public_registration", True):
        flash("Public registration is currently disabled.", "warning")
        return redirect(url_for("auth.login"))
    return render_template("auth/signup.html")


@auth_bp.post("/signup")
def signup_post():
    if not SystemSetting.get("allow_public_registration", True):
        flash("Public registration is currently disabled.", "warning")
        return redirect(url_for("auth.login"))

    first_name       = request.form.get("first_name", "").strip()
    last_name        = request.form.get("last_name",  "").strip()
    email            = request.form.get("email",      "").strip().lower()
    password         = request.form.get("password",   "")
    confirm_password = request.form.get("confirm_password", "")
    phone            = request.form.get("phone",      "").strip()

    # ── Validation ───────────────────────────────────────────
    if not first_name or not last_name or not email or not password:
        flash("All required fields must be filled.", "error")
        return render_template("auth/signup.html", email=email,
                               first_name=first_name, last_name=last_name)

    if len(password) < 8:
        flash("Password must be at least 8 characters.", "error")
        return render_template("auth/signup.html", email=email,
                               first_name=first_name, last_name=last_name)

    if password != confirm_password:
        flash("Passwords do not match. Please re-enter.", "error")
        return render_template("auth/signup.html", email=email,
                               first_name=first_name, last_name=last_name)

    if User.query.filter_by(email=email).first():
        flash("A user with that email already exists.", "error")
        return render_template("auth/signup.html", email=email,
                               first_name=first_name, last_name=last_name)

    student_role = Role.query.filter_by(slug="student").first()
    if not student_role:
        flash("Student role not found. Contact administrator.", "error")
        return render_template("auth/signup.html", email=email)

    user = User(
        email=email,
        password_hash=bcrypt.generate_password_hash(password).decode(),
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        role_id=student_role.id,
        status="active"
    )
    db.session.add(user)
    db.session.flush()

    student = Student(
        user_id=user.id,
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone
    )
    db.session.add(student)
    db.session.commit()

    login_user(user)
    user.record_login(request.remote_addr)
    flash("Registration successful! Welcome to Skolaz.", "success")
    return redirect(url_for("student_portal.dashboard"))


# ── Logout ────────────────────────────────────────────────────────────────────

@auth_bp.get("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


# ── MFA Verify ────────────────────────────────────────────────────────────────

@auth_bp.get("/mfa")
def mfa_verify():
    if "mfa_user_id" not in session:
        return redirect(url_for("auth.login"))
    return render_template("auth/mfa_verify.html")


@auth_bp.post("/mfa")
def mfa_verify_post():
    user_id = session.get("mfa_user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    user = User.query.get(user_id)
    code = request.form.get("code", "").strip()

    import pyotp
    totp = pyotp.TOTP(user.mfa_secret)
    if not totp.verify(code):
        flash("Invalid MFA code. Try again.", "error")
        return render_template("auth/mfa_verify.html"), 401

    login_user(user, remember=session.get("mfa_remember", False))
    user.record_login(request.remote_addr)
    session.pop("mfa_user_id", None)
    session.pop("mfa_remember", None)
    return redirect(_role_dashboard())


# ── MFA Setup ─────────────────────────────────────────────────────────────────

@auth_bp.get("/mfa/setup")
@login_required
def mfa_setup():
    import pyotp, qrcode, io, base64
    if not current_user.mfa_secret:
        current_user.mfa_secret = pyotp.random_base32()
        db.session.commit()

    totp    = pyotp.TOTP(current_user.mfa_secret)
    otp_uri = totp.provisioning_uri(
        name=current_user.email,
        issuer_name=current_app.config.get("MFA_ISSUER_NAME", "Skolaz")
    )
    img = qrcode.make(otp_uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode()
    return render_template("auth/mfa_setup.html",
                           qr_b64=qr_b64, secret=current_user.mfa_secret)


@auth_bp.post("/mfa/setup")
@login_required
def mfa_setup_post():
    import pyotp
    code = request.form.get("code", "").strip()
    totp = pyotp.TOTP(current_user.mfa_secret)
    if not totp.verify(code):
        flash("Invalid code. MFA not enabled.", "error")
        return redirect(url_for("auth.mfa_setup"))
    current_user.mfa_enabled = True
    db.session.commit()
    flash("Two-factor authentication enabled successfully.", "success")
    return redirect(_role_dashboard())


# ── Password Reset ────────────────────────────────────────────────────────────

@auth_bp.get("/forgot-password")
def forgot_password():
    return render_template("auth/forgot_password.html")


@auth_bp.post("/forgot-password")
def forgot_password_post():
    email = request.form.get("email", "").strip().lower()
    user  = User.query.filter_by(email=email, is_deleted=False).first()
    if user:
        from app.services.email_service import send_password_reset
        send_password_reset(user)
    flash("If that email exists, a reset link has been sent.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.get("/reset-password/<token>")
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first_or_404()
    if user.reset_token_expiry and user.reset_token_expiry < datetime.now(timezone.utc):
        flash("Reset link has expired. Please request a new one.", "error")
        return redirect(url_for("auth.forgot_password"))
    return render_template("auth/reset_password.html", token=token)


@auth_bp.post("/reset-password/<token>")
def reset_password_post(token):
    user             = User.query.filter_by(reset_token=token).first_or_404()
    password         = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    if len(password) < 8:
        flash("Password must be at least 8 characters.", "error")
        return render_template("auth/reset_password.html", token=token)

    if password != confirm_password:
        flash("Passwords do not match.", "error")
        return render_template("auth/reset_password.html", token=token)

    user.password_hash    = bcrypt.generate_password_hash(password).decode()
    user.reset_token      = None
    user.reset_token_expiry = None
    db.session.commit()
    flash("Password reset successfully. Please log in.", "success")
    return redirect(url_for("auth.login"))


# ── Profile ───────────────────────────────────────────────────────────────────

@auth_bp.get("/profile")
@login_required
def profile():
    return render_template("auth/profile.html")


@auth_bp.post("/profile")
@login_required
def profile_post():
    current_user.first_name = request.form.get("first_name", current_user.first_name)
    current_user.last_name  = request.form.get("last_name",  current_user.last_name)
    current_user.phone      = request.form.get("phone",      current_user.phone)

    # Password change (optional)
    new_password     = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")
    if new_password:
        if len(new_password) < 8:
            flash("New password must be at least 8 characters.", "error")
            return redirect(url_for("auth.profile"))
        if new_password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for("auth.profile"))
        current_user.password_hash = bcrypt.generate_password_hash(new_password).decode()

    db.session.commit()
    flash("Profile updated successfully.", "success")
    return redirect(url_for("auth.profile"))


# ── Role Dashboard Helper ─────────────────────────────────────────────────────

def _role_dashboard() -> str:
    """Return the correct dashboard URL for the current user's role."""
    if not current_user.is_authenticated:
        return url_for("public.home")
    role_slug = current_user.role.slug
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
    return mapping.get(role_slug, url_for("public.home"))
