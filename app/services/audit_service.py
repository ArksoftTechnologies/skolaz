"""
Skolaz v2.0 — Audit Service
Write audit logs and activity feeds without cluttering route handlers
"""
from datetime import datetime, timezone
from app.extensions import db


def log_action(
    action: str,
    module: str = None,
    user_id: int = None,
    record_id: int = None,
    record_type: str = None,
    description: str = None,
    old_value: str = None,
    new_value: str = None,
    ip: str = None,
    user_agent: str = None,
) -> None:
    """Write a row to audit_logs. Silently swallows exceptions."""
    try:
        from app.models.audit import AuditLog
        entry = AuditLog(
            user_id=user_id,
            action=action,
            module=module,
            record_id=record_id,
            record_type=record_type,
            description=description,
            old_value=old_value,
            new_value=new_value,
            ip_address=ip,
            user_agent=user_agent,
            created_at=datetime.now(timezone.utc),
        )
        db.session.add(entry)
        db.session.commit()
    except Exception:
        db.session.rollback()


def log_activity(
    student_id: int,
    verb: str,
    detail: str = None,
    actor_id: int = None,
    icon: str = "information-circle",
    color: str = "blue",
    link_url: str = None,
) -> None:
    """Write a row to the student activity timeline feed."""
    try:
        from app.models.audit import Activity
        entry = Activity(
            student_id=student_id,
            actor_id=actor_id,
            verb=verb,
            detail=detail,
            icon=icon,
            color=color,
            link_url=link_url,
            created_at=datetime.now(timezone.utc),
        )
        db.session.add(entry)
        db.session.commit()
    except Exception:
        db.session.rollback()
