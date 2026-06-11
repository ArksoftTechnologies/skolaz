"""
Skolaz v2.0 — Communication Models
Chat, Notification, EmailLog
"""
import enum
from datetime import datetime, timezone
from app.extensions import db


class NotificationType(str, enum.Enum):
    INFO     = "info"
    SUCCESS  = "success"
    WARNING  = "warning"
    ERROR    = "error"
    OFFER    = "offer"
    DOCUMENT = "document"
    STAGE    = "stage"
    MESSAGE  = "message"
    TASK     = "task"


class EmailStatus(str, enum.Enum):
    QUEUED  = "queued"
    SENT    = "sent"
    FAILED  = "failed"
    BOUNCED = "bounced"


# ── Chat ──────────────────────────────────────────────────────────────────────

class Chat(db.Model):
    __tablename__ = "chats"

    id         = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    sender_id  = db.Column(db.Integer, db.ForeignKey("users.id"),    nullable=False)
    message    = db.Column(db.Text, nullable=False)
    attachment_url  = db.Column(db.String(1000))
    attachment_name = db.Column(db.String(255))
    is_read    = db.Column(db.Boolean, default=False)
    read_at    = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    student = db.relationship("Student", back_populates="chats")
    sender  = db.relationship("User")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "sender_name": self.sender.full_name if self.sender else None,
            "sender_avatar": self.sender.avatar_url if self.sender else None,
            "message": self.message,
            "attachment_url": self.attachment_url,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<Chat student={self.student_id} sender={self.sender_id}>"


# ── Notification ──────────────────────────────────────────────────────────────

class Notification(db.Model):
    __tablename__ = "notifications"

    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title        = db.Column(db.String(200), nullable=False)
    body         = db.Column(db.Text)
    notif_type   = db.Column(db.String(20), default=NotificationType.INFO)
    action_url   = db.Column(db.String(500))
    is_read      = db.Column(db.Boolean, default=False)
    read_at      = db.Column(db.DateTime)

    # Optional links
    student_id     = db.Column(db.Integer, db.ForeignKey("students.id"))
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id"))

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = db.relationship("User", back_populates="notifications")

    def mark_read(self):
        self.is_read = True
        self.read_at = datetime.now(timezone.utc)
        db.session.commit()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "body": self.body,
            "type": self.notif_type,
            "action_url": self.action_url,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<Notification user={self.user_id} title={self.title[:30]}>"


# ── Email Log ─────────────────────────────────────────────────────────────────

class EmailLog(db.Model):
    __tablename__ = "email_logs"

    id           = db.Column(db.Integer, primary_key=True)
    to_email     = db.Column(db.String(120), nullable=False)
    to_name      = db.Column(db.String(150))
    from_email   = db.Column(db.String(120))
    subject      = db.Column(db.String(300), nullable=False)
    template     = db.Column(db.String(100))
    body_preview = db.Column(db.Text)
    status       = db.Column(db.String(20), default=EmailStatus.QUEUED)
    provider     = db.Column(db.String(30))     # smtp | sendgrid | mailgun
    provider_id  = db.Column(db.String(200))    # provider message ID
    error_msg    = db.Column(db.Text)
    sent_at      = db.Column(db.DateTime)
    opened_at    = db.Column(db.DateTime)

    student_id   = db.Column(db.Integer, db.ForeignKey("students.id"))
    sent_by      = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at   = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<EmailLog to={self.to_email} subject={self.subject[:40]}>"
