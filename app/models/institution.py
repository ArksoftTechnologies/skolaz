"""
Skolaz v2.0 — Institution Models
School, Program, Intake, TuitionFee, Scholarship
"""
import enum
from datetime import datetime, timezone
from app.extensions import db


class InstitutionStatus(str, enum.Enum):
    DRAFT     = "draft"
    PENDING   = "pending"
    ACTIVE    = "active"
    INACTIVE  = "inactive"
    SUSPENDED = "suspended"


class ProgramLevel(str, enum.Enum):
    CERTIFICATE    = "certificate"
    DIPLOMA        = "diploma"
    ASSOCIATE      = "associate"
    BACHELOR       = "bachelor"
    POSTGRADUATE   = "postgraduate"
    MASTER         = "master"
    DOCTORATE      = "doctorate"
    LANGUAGE       = "language"
    SHORT_COURSE   = "short_course"
    FOUNDATION     = "foundation"
    PRE_SESSIONAL  = "pre_sessional"


# ── School media join table ───────────────────────────────────
school_media = db.Table(
    "school_media",
    db.Column("school_id", db.Integer, db.ForeignKey("schools.id"), primary_key=True),
    db.Column("media_id",  db.Integer, db.ForeignKey("media_assets.id"), primary_key=True),
)


# ── Media Asset ───────────────────────────────────────────────────────────────

class MediaAsset(db.Model):
    __tablename__ = "media_assets"

    id         = db.Column(db.Integer, primary_key=True)
    url        = db.Column(db.String(1000), nullable=False)
    asset_type = db.Column(db.String(20))  # image | video | brochure
    filename   = db.Column(db.String(255))
    size_bytes = db.Column(db.Integer)
    uploaded_by= db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


# ── School ────────────────────────────────────────────────────────────────────

class School(db.Model):
    __tablename__ = "schools"

    id                      = db.Column(db.Integer, primary_key=True)
    name                    = db.Column(db.String(200), nullable=False)
    slug                    = db.Column(db.String(200), unique=True)
    logo_url                = db.Column(db.String(1000))
    cover_image_url         = db.Column(db.String(1000))
    description             = db.Column(db.Text)
    short_description       = db.Column(db.String(500))
    website                 = db.Column(db.String(500))
    email                   = db.Column(db.String(120))
    phone                   = db.Column(db.String(30))

    # Location
    country_id              = db.Column(db.Integer, db.ForeignKey("countries.id"))
    state_id                = db.Column(db.Integer, db.ForeignKey("states.id"))
    city_id                 = db.Column(db.Integer, db.ForeignKey("cities.id"))
    address                 = db.Column(db.String(500))

    # Academic info
    ranking                 = db.Column(db.Integer)
    ranking_source          = db.Column(db.String(100))   # QS, Times, etc.
    acceptance_rate         = db.Column(db.Numeric(5, 2))
    established_year        = db.Column(db.Integer)
    international_students  = db.Column(db.Integer)
    total_students          = db.Column(db.Integer)
    institution_type        = db.Column(db.String(50))    # public | private | college | university

    # Financials
    tuition_min             = db.Column(db.Numeric(12, 2))
    tuition_max             = db.Column(db.Numeric(12, 2))
    currency                = db.Column(db.String(10), default="GBP")

    # Commission defaults
    default_commission_pct  = db.Column(db.Numeric(5, 2))

    # Flags
    status                  = db.Column(db.String(20), default=InstitutionStatus.DRAFT)
    is_featured             = db.Column(db.Boolean, default=False)
    is_partner              = db.Column(db.Boolean, default=False)
    requires_gmat           = db.Column(db.Boolean, default=False)
    requires_gre            = db.Column(db.Boolean, default=False)

    # Meta
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    approved_by= db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    country      = db.relationship("Country", back_populates="schools")
    state        = db.relationship("State")
    city         = db.relationship("City",    back_populates="schools")
    campuses     = db.relationship("Campus",  back_populates="school",
                                   lazy="dynamic", cascade="all, delete-orphan")
    programs     = db.relationship("Program", back_populates="school",
                                   lazy="dynamic", cascade="all, delete-orphan")
    scholarships = db.relationship("Scholarship", back_populates="school",
                                   lazy="dynamic", cascade="all, delete-orphan")
    media        = db.relationship("MediaAsset", secondary=school_media, lazy="dynamic")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "logo_url": self.logo_url,
            "country": self.country.name if self.country else None,
            "city": self.city.name if self.city else None,
            "ranking": self.ranking,
            "status": self.status,
        }

    def __repr__(self):
        return f"<School {self.name}>"


# ── Program ───────────────────────────────────────────────────────────────────

class Program(db.Model):
    __tablename__ = "programs"

    id                  = db.Column(db.Integer, primary_key=True)
    school_id           = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    name                = db.Column(db.String(200), nullable=False)
    code                = db.Column(db.String(50))
    level               = db.Column(db.String(30), nullable=False)
    field_of_study      = db.Column(db.String(100))
    description         = db.Column(db.Text)
    duration_months     = db.Column(db.Integer)
    study_mode          = db.Column(db.String(30))  # full-time | part-time | online | blended

    # Requirements
    ielts_requirement   = db.Column(db.Numeric(3, 1))
    toefl_requirement   = db.Column(db.Integer)
    pte_requirement     = db.Column(db.Numeric(3, 1))
    gpa_requirement     = db.Column(db.Numeric(4, 2))
    gmat_requirement    = db.Column(db.Integer)
    gre_requirement     = db.Column(db.Integer)
    min_work_experience = db.Column(db.Integer)       # years

    # Financials
    tuition_fee         = db.Column(db.Numeric(12, 2))
    currency            = db.Column(db.String(10), default="GBP")
    application_fee     = db.Column(db.Numeric(10, 2))

    # Processing
    processing_weeks    = db.Column(db.Integer)
    brochure_url        = db.Column(db.String(1000))

    # Status
    status              = db.Column(db.String(20), default=InstitutionStatus.DRAFT)
    is_featured         = db.Column(db.Boolean, default=False)

    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    approved_by= db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    school       = db.relationship("School",  back_populates="programs")
    intakes      = db.relationship("Intake",  back_populates="program",
                                   lazy="dynamic", cascade="all, delete-orphan")
    tuition_fees = db.relationship("TuitionFee", back_populates="program",
                                   lazy="dynamic", cascade="all, delete-orphan")
    applications = db.relationship("Application", back_populates="program", lazy="dynamic")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "school": self.school.name if self.school else None,
            "level": self.level,
            "duration_months": self.duration_months,
            "tuition_fee": float(self.tuition_fee) if self.tuition_fee else None,
            "currency": self.currency,
            "ielts_requirement": float(self.ielts_requirement) if self.ielts_requirement else None,
        }

    def __repr__(self):
        return f"<Program {self.name}>"


# ── Intake ────────────────────────────────────────────────────────────────────

class Intake(db.Model):
    __tablename__ = "intakes"

    id               = db.Column(db.Integer, primary_key=True)
    program_id       = db.Column(db.Integer, db.ForeignKey("programs.id"), nullable=False)
    month            = db.Column(db.Integer, nullable=False)  # 1–12
    year             = db.Column(db.Integer, nullable=False)
    deadline         = db.Column(db.Date)
    spots_available  = db.Column(db.Integer)
    is_open          = db.Column(db.Boolean, default=True)
    notes            = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    program      = db.relationship("Program",     back_populates="intakes")
    applications = db.relationship("Application", back_populates="intake", lazy="dynamic")

    def __repr__(self):
        return f"<Intake {self.month}/{self.year} prog={self.program_id}>"


# ── Tuition Fee (historical / per year) ──────────────────────────────────────

class TuitionFee(db.Model):
    __tablename__ = "tuition_fees"

    id          = db.Column(db.Integer, primary_key=True)
    program_id  = db.Column(db.Integer, db.ForeignKey("programs.id"), nullable=False)
    academic_year = db.Column(db.String(10))   # e.g. "2024/25"
    amount      = db.Column(db.Numeric(12, 2), nullable=False)
    currency    = db.Column(db.String(10), default="GBP")
    fee_type    = db.Column(db.String(30))     # tuition | accommodation | registration
    notes       = db.Column(db.String(255))
    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_by  = db.Column(db.Integer, db.ForeignKey("users.id"))

    program = db.relationship("Program", back_populates="tuition_fees")


# ── Scholarship ───────────────────────────────────────────────────────────────

class Scholarship(db.Model):
    __tablename__ = "scholarships"

    id              = db.Column(db.Integer, primary_key=True)
    school_id       = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    program_id      = db.Column(db.Integer, db.ForeignKey("programs.id"))
    name            = db.Column(db.String(200), nullable=False)
    description     = db.Column(db.Text)
    amount          = db.Column(db.Numeric(12, 2))
    currency        = db.Column(db.String(10), default="GBP")
    scholarship_type= db.Column(db.String(50))  # full | partial | merit | need
    eligibility     = db.Column(db.Text)
    deadline        = db.Column(db.Date)
    how_to_apply    = db.Column(db.Text)
    is_active       = db.Column(db.Boolean, default=True)
    link            = db.Column(db.String(500))

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))

    school  = db.relationship("School",  back_populates="scholarships")
    program = db.relationship("Program")

    def __repr__(self):
        return f"<Scholarship {self.name}>"
