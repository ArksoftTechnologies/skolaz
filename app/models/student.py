"""
Skolaz v2.0 — Student & Document Models
The heart of the CRM system
"""
import enum
from datetime import datetime, timezone
from app.extensions import db


class StudentSource(str, enum.Enum):
    DIRECT       = "direct"
    AGENCY       = "agency"
    REFERRAL     = "referral"
    WEBSITE      = "website"
    SOCIAL_MEDIA = "social_media"
    EVENT        = "event"
    WALK_IN      = "walk_in"


class DocumentCategory(str, enum.Enum):
    ACADEMIC  = "academic"
    IDENTITY  = "identity"
    FINANCIAL = "financial"
    VISA      = "visa"
    OTHER     = "other"


class DocumentStatus(str, enum.Enum):
    PENDING  = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED  = "expired"


# ── Preferred countries join table ────────────────────────────
student_preferred_countries = db.Table(
    "student_preferred_countries",
    db.Column("student_id",  db.Integer, db.ForeignKey("students.id"), primary_key=True),
    db.Column("country_id",  db.Integer, db.ForeignKey("countries.id"), primary_key=True),
)

# ── Preferred programs join table ─────────────────────────────
student_preferred_programs = db.Table(
    "student_preferred_programs",
    db.Column("student_id",  db.Integer, db.ForeignKey("students.id"), primary_key=True),
    db.Column("program_id",  db.Integer, db.ForeignKey("programs.id"), primary_key=True),
)


# ── Student ───────────────────────────────────────────────────────────────────

class Student(db.Model):
    __tablename__ = "students"

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True)

    # Personal
    first_name  = db.Column(db.String(64),  nullable=False)
    last_name   = db.Column(db.String(64),  nullable=False)
    middle_name = db.Column(db.String(64))
    dob         = db.Column(db.Date)
    gender      = db.Column(db.String(20))
    marital_status = db.Column(db.String(20))
    avatar_url  = db.Column(db.String(1000))

    # Nationality
    nationality_country_id = db.Column(db.Integer, db.ForeignKey("countries.id"))
    country_of_birth_id    = db.Column(db.Integer, db.ForeignKey("countries.id"))
    country_of_residence_id= db.Column(db.Integer, db.ForeignKey("countries.id"))

    # Passport
    passport_number = db.Column(db.String(30))
    passport_expiry = db.Column(db.Date)
    passport_status = db.Column(db.String(20))  # valid | expired | pending

    # Contact
    email       = db.Column(db.String(120), nullable=False, index=True)
    phone       = db.Column(db.String(30))
    whatsapp    = db.Column(db.String(30))
    address     = db.Column(db.String(500))
    city        = db.Column(db.String(100))
    postal_code = db.Column(db.String(20))

    # Academic background
    highest_qualification = db.Column(db.String(100))
    institution_attended  = db.Column(db.String(200))
    graduation_year       = db.Column(db.Integer)
    gpa                   = db.Column(db.Numeric(4, 2))
    gpa_scale             = db.Column(db.Numeric(4, 2))  # e.g. 4.0 or 5.0
    english_test          = db.Column(db.String(20))      # IELTS | TOEFL | PTE | None
    english_score         = db.Column(db.Numeric(4, 1))

    # Financial
    budget_min = db.Column(db.Numeric(12, 2))
    budget_max = db.Column(db.Numeric(12, 2))
    budget_currency = db.Column(db.String(10), default="USD")
    self_funded = db.Column(db.Boolean, default=True)

    # CRM
    source       = db.Column(db.String(30), default=StudentSource.DIRECT)
    referral_code= db.Column(db.String(50))
    notes        = db.Column(db.Text)
    tags         = db.Column(db.String(500))  # comma-separated

    # Assignment
    primary_advisor_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    backup_advisor_id  = db.Column(db.Integer, db.ForeignKey("users.id"))
    agency_id          = db.Column(db.Integer, db.ForeignKey("agencies.id"))
    created_by         = db.Column(db.Integer, db.ForeignKey("users.id"))

    # Status
    is_active   = db.Column(db.Boolean, default=True)
    is_archived = db.Column(db.Boolean, default=False)
    archived_at = db.Column(db.DateTime)

    # Timestamps
    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                            onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user              = db.relationship("User", foreign_keys=[user_id])
    primary_advisor   = db.relationship("User", foreign_keys=[primary_advisor_id])
    backup_advisor    = db.relationship("User", foreign_keys=[backup_advisor_id])
    creator           = db.relationship("User", foreign_keys=[created_by])
    agency            = db.relationship("Agency", back_populates="students")
    nationality_country = db.relationship("Country", back_populates="students",
                                          foreign_keys=[nationality_country_id])
    country_of_birth  = db.relationship("Country", foreign_keys=[country_of_birth_id])
    country_of_residence = db.relationship("Country", foreign_keys=[country_of_residence_id])

    preferred_countries = db.relationship("Country", secondary=student_preferred_countries,
                                          lazy="dynamic")
    preferred_programs  = db.relationship("Program", secondary=student_preferred_programs,
                                          lazy="dynamic")

    applications = db.relationship("Application", back_populates="student", lazy="dynamic")
    documents    = db.relationship("StudentDocument", back_populates="student",
                                   lazy="dynamic", cascade="all, delete-orphan")
    chats        = db.relationship("Chat", back_populates="student", lazy="dynamic")
    tasks        = db.relationship("Task", back_populates="student", lazy="dynamic",
                                   foreign_keys="Task.student_id")
    notes_list   = db.relationship("Note", back_populates="student", lazy="dynamic")
    meetings     = db.relationship("Meeting", back_populates="student", lazy="dynamic")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def initials(self) -> str:
        return f"{self.first_name[0]}{self.last_name[0]}".upper()

    @property
    def active_application(self):
        return self.applications.filter_by(is_active=True).order_by(
            db.desc("created_at")
        ).first()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "nationality": self.nationality_country.name if self.nationality_country else None,
            "source": self.source,
            "advisor": self.primary_advisor.full_name if self.primary_advisor else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<Student {self.full_name}>"


# ── Student Document ──────────────────────────────────────────────────────────

class StudentDocument(db.Model):
    __tablename__ = "student_documents"

    id          = db.Column(db.Integer, primary_key=True)
    student_id  = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    category    = db.Column(db.String(30), nullable=False)   # DocumentCategory
    doc_type    = db.Column(db.String(100), nullable=False)  # e.g. "IELTS Certificate"
    file_url    = db.Column(db.String(1000), nullable=False)
    filename    = db.Column(db.String(255))
    file_size   = db.Column(db.Integer)
    mime_type   = db.Column(db.String(100))
    version     = db.Column(db.Integer, default=1)
    is_latest   = db.Column(db.Boolean, default=True)

    # Validity
    issue_date  = db.Column(db.Date)
    expiry_date = db.Column(db.Date)

    # Review
    status          = db.Column(db.String(20), default=DocumentStatus.PENDING)
    reviewed_by     = db.Column(db.Integer, db.ForeignKey("users.id"))
    reviewed_at     = db.Column(db.DateTime)
    rejection_reason= db.Column(db.Text)
    notes           = db.Column(db.Text)

    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                            onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    student    = db.relationship("Student", back_populates="documents")
    reviewer   = db.relationship("User", foreign_keys=[reviewed_by])
    uploader   = db.relationship("User", foreign_keys=[uploaded_by])

    def __repr__(self):
        return f"<StudentDocument {self.doc_type} v{self.version}>"
