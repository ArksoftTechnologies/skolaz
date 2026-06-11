"""
Skolaz v2.0 — Role-Based Access Decorators
"""
import functools
from flask import abort, request, jsonify
from flask_login import current_user


def _is_api_request() -> bool:
    return request.path.startswith("/api/") or \
           request.accept_mimetypes.best == "application/json"


def _deny(message: str = "Access denied", code: int = 403):
    if _is_api_request():
        return jsonify(success=False, message=message, data=None, errors=[]), code
    abort(code)


# ── Core decorator factory ────────────────────────────────────────────────────

def roles_required(*role_slugs):
    """Restrict a view to users with one of the given role slugs."""
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return _deny("Authentication required", 401)
            if not current_user.is_active_account:
                return _deny("Account is inactive or suspended", 403)
            if current_user.role.slug not in role_slugs:
                return _deny(
                    f"This page requires one of these roles: {', '.join(role_slugs)}", 403
                )
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def permission_required(module: str, action: str = "read"):
    """Restrict a view based on the user's role permission for a module."""
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return _deny("Authentication required", 401)
            if not current_user.has_permission(module, action):
                return _deny(
                    f"You do not have {action} permission on '{module}'", 403
                )
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ── Convenience shorthands ────────────────────────────────────────────────────

def super_admin_required(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return _deny("Authentication required", 401)
        if not current_user.is_super_admin:
            return _deny("Super Admin access required", 403)
        return fn(*args, **kwargs)
    return wrapper


def staff_or_above(fn):
    """Allows super_admin, staff."""
    return roles_required("super_admin", "staff")(fn)


def advisor_or_above(fn):
    """Allows super_admin, staff, advisor."""
    return roles_required("super_admin", "staff", "advisor")(fn)


def internal_only(fn):
    """Allows super_admin, staff, advisor, data_entry (no agency/student)."""
    return roles_required("super_admin", "staff", "advisor", "data_entry")(fn)


def agency_required(fn):
    return roles_required("agency", "agency_member")(fn)


def student_required(fn):
    return roles_required("student")(fn)


# ── Audit decorator ───────────────────────────────────────────────────────────

def audit_action(action: str, module: str):
    """
    Log an AuditLog entry after a successful view call.
    Usage: @audit_action("offer.uploaded", "offers")
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            result = fn(*args, **kwargs)
            try:
                from app.services.audit_service import log_action
                log_action(
                    action=action,
                    module=module,
                    user_id=current_user.id if current_user.is_authenticated else None,
                    ip=request.remote_addr,
                    user_agent=request.user_agent.string,
                )
            except Exception:
                pass  # Never let audit failures break the response
            return result
        return wrapper
    return decorator
