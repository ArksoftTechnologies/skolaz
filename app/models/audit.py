"""
Skolaz v2.0 — Audit Log & Activity Models
Every user action is timestamped and recorded with IP + device
"""
from datetime import datetime, timezone
from app.extensions import db


class AuditLog(db.Model):
    """
    Immutable record of every meaningful system action.
    Never updated — only appended.
    """
    __tablename__ = "audit_logs"

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"))
    action      = db.Column(db.String(100), nullable=False)   # e.g. "offer.uploaded"
    module      = db.Column(db.String(50))                    # e.g. "offers"
    record_id   = db.Column(db.Integer)                       # PK of affected record
    record_type = db.Column(db.String(50))                    # e.g. "Offer"
    description = db.Column(db.Text)
    old_value   = db.Column(db.Text)   # JSON string of previous state
    new_value   = db.Column(db.Text)   # JSON string of new state
    ip_address  = db.Column(db.String(45))
    user_agent  = db.Column(db.String(500))
    device      = db.Column(db.String(100))
    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                            nullable=False)

    # Relationship (read-only, no cascade)
    user = db.relationship("User", back_populates="audit_logs")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user": self.user.full_name if self.user else "System",
            "action": self.action,
            "module": self.module,
            "record_id": self.record_id,
            "description": self.description,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<AuditLog {self.action} by user={self.user_id}>"


class Activity(db.Model):
    """
    Timeline feed per student — lighter weight than full audit log.
    Used for the student timeline UI component.
    """
    __tablename__ = "activities"

    id          = db.Column(db.Integer, primary_key=True)
    student_id  = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    actor_id    = db.Column(db.Integer, db.ForeignKey("users.id"))
    verb        = db.Column(db.String(100), nullable=False)  # "uploaded offer", "changed stage"
    detail      = db.Column(db.Text)
    icon        = db.Column(db.String(50))                   # heroicon name
    color       = db.Column(db.String(30))                   # tailwind color e.g. "blue"
    link_url    = db.Column(db.String(500))
    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    actor   = db.relationship("User")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "actor": self.actor.full_name if self.actor else "System",
            "verb": self.verb,
            "detail": self.detail,
            "icon": self.icon,
            "color": self.color,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<Activity student={self.student_id} verb={self.verb}>"
