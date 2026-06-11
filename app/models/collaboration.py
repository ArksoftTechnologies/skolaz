"""
Skolaz v2.0 — Collaboration Models
Tasks, Notes, Meetings — all attached to student records
"""
import enum
from datetime import datetime, timezone
from app.extensions import db


class TaskStatus(str, enum.Enum):
    OPEN        = "open"
    IN_PROGRESS = "in_progress"
    DONE        = "done"
    CANCELLED   = "cancelled"


class TaskPriority(str, enum.Enum):
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"
    URGENT = "urgent"


class MeetingStatus(str, enum.Enum):
    SCHEDULED  = "scheduled"
    CONFIRMED  = "confirmed"
    COMPLETED  = "completed"
    CANCELLED  = "cancelled"
    NO_SHOW    = "no_show"


# ── Task ──────────────────────────────────────────────────────────────────────

class Task(db.Model):
    __tablename__ = "tasks"

    id          = db.Column(db.Integer, primary_key=True)
    student_id  = db.Column(db.Integer, db.ForeignKey("students.id"))
    assigned_to = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_by  = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title       = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    priority    = db.Column(db.String(20), default=TaskPriority.MEDIUM)
    status      = db.Column(db.String(20), default=TaskStatus.OPEN)
    due_date    = db.Column(db.DateTime)
    completed_at= db.Column(db.DateTime)

    # Optional links
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id"))

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    student  = db.relationship("Student", back_populates="tasks",
                               foreign_keys=[student_id])
    assignee = db.relationship("User", foreign_keys=[assigned_to],
                               back_populates="tasks_assigned")
    creator  = db.relationship("User", foreign_keys=[created_by],
                               back_populates="tasks_created")

    @property
    def is_overdue(self) -> bool:
        if not self.due_date or self.status in (TaskStatus.DONE, TaskStatus.CANCELLED):
            return False
        return datetime.now(timezone.utc) > self.due_date.replace(tzinfo=timezone.utc) \
            if self.due_date.tzinfo is None else datetime.now(timezone.utc) > self.due_date

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "priority": self.priority,
            "status": self.status,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "is_overdue": self.is_overdue,
            "assignee": self.assignee.full_name if self.assignee else None,
        }

    def __repr__(self):
        return f"<Task {self.title[:40]} [{self.status}]>"


# ── Note ──────────────────────────────────────────────────────────────────────

class Note(db.Model):
    __tablename__ = "notes"

    id          = db.Column(db.Integer, primary_key=True)
    student_id  = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    author_id   = db.Column(db.Integer, db.ForeignKey("users.id"),    nullable=False)
    content     = db.Column(db.Text, nullable=False)
    is_internal = db.Column(db.Boolean, default=True)  # False = visible to student
    is_pinned   = db.Column(db.Boolean, default=False)

    # Optional link
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id"))

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    student = db.relationship("Student", back_populates="notes_list")
    author  = db.relationship("User",    back_populates="notes")

    def __repr__(self):
        return f"<Note student={self.student_id} internal={self.is_internal}>"


# ── Meeting ───────────────────────────────────────────────────────────────────

class Meeting(db.Model):
    __tablename__ = "meetings"

    id          = db.Column(db.Integer, primary_key=True)
    student_id  = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    advisor_id  = db.Column(db.Integer, db.ForeignKey("users.id"),    nullable=False)
    title       = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    scheduled_at= db.Column(db.DateTime, nullable=False)
    duration_mins= db.Column(db.Integer, default=30)
    meeting_type= db.Column(db.String(30), default="video")  # video | phone | in-person
    meeting_url = db.Column(db.String(500))  # Zoom, Meet, etc.
    location    = db.Column(db.String(300))
    status      = db.Column(db.String(20), default=MeetingStatus.SCHEDULED)
    notes       = db.Column(db.Text)
    recording_url = db.Column(db.String(500))

    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                            onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    student = db.relationship("Student",  back_populates="meetings")
    advisor = db.relationship("User")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "duration_mins": self.duration_mins,
            "meeting_type": self.meeting_type,
            "meeting_url": self.meeting_url,
            "status": self.status,
            "advisor": self.advisor.full_name if self.advisor else None,
        }

    def __repr__(self):
        return f"<Meeting student={self.student_id} at={self.scheduled_at}>"
