"""
Skolaz v2.0 — Application & Application Stage Models
14-stage pipeline: Interested → Enrolled
"""
import enum
from datetime import datetime, timezone
from app.extensions import db


class ApplicationStageEnum(str, enum.Enum):
    INTERESTED            = "interested"
    QUALIFIED             = "qualified"
    DOCUMENTS_PENDING     = "documents_pending"
    DOCUMENTS_RECEIVED    = "documents_received"
    APPLICATION_DRAFT     = "application_draft"
    APPLICATION_SUBMITTED = "application_submitted"
    SCHOOL_REVIEW         = "school_review"
    OFFER_ISSUED          = "offer_issued"
    OFFER_ACCEPTED        = "offer_accepted"
    DEPOSIT_PAID          = "deposit_paid"
    CAS_LOA_ISSUED        = "cas_loa_issued"
    VISA_SUBMITTED        = "visa_submitted"
    VISA_APPROVED         = "visa_approved"
    ENROLLED              = "enrolled"
    WITHDRAWN             = "withdrawn"
    REJECTED              = "rejected"


# Ordered list of active stages (excludes terminal states)
STAGE_ORDER = [
    ApplicationStageEnum.INTERESTED,
    ApplicationStageEnum.QUALIFIED,
    ApplicationStageEnum.DOCUMENTS_PENDING,
    ApplicationStageEnum.DOCUMENTS_RECEIVED,
    ApplicationStageEnum.APPLICATION_DRAFT,
    ApplicationStageEnum.APPLICATION_SUBMITTED,
    ApplicationStageEnum.SCHOOL_REVIEW,
    ApplicationStageEnum.OFFER_ISSUED,
    ApplicationStageEnum.OFFER_ACCEPTED,
    ApplicationStageEnum.DEPOSIT_PAID,
    ApplicationStageEnum.CAS_LOA_ISSUED,
    ApplicationStageEnum.VISA_SUBMITTED,
    ApplicationStageEnum.VISA_APPROVED,
    ApplicationStageEnum.ENROLLED,
]

STAGE_LABELS = {
    "interested":            "Interested",
    "qualified":             "Qualified",
    "documents_pending":     "Documents Pending",
    "documents_received":    "Documents Received",
    "application_draft":     "Application Draft",
    "application_submitted": "Application Submitted",
    "school_review":         "School Review",
    "offer_issued":          "Offer Issued",
    "offer_accepted":        "Offer Accepted",
    "deposit_paid":          "Deposit Paid",
    "cas_loa_issued":        "CAS / LOA Issued",
    "visa_submitted":        "Visa Submitted",
    "visa_approved":         "Visa Approved",
    "enrolled":              "Enrolled",
    "withdrawn":             "Withdrawn",
    "rejected":              "Rejected",
}


# ── Application ───────────────────────────────────────────────────────────────

class Application(db.Model):
    __tablename__ = "applications"

    id          = db.Column(db.Integer, primary_key=True)
    reference   = db.Column(db.String(20), unique=True)  # SKZ-2024-00001
    student_id  = db.Column(db.Integer, db.ForeignKey("students.id"),  nullable=False)
    program_id  = db.Column(db.Integer, db.ForeignKey("programs.id"),  nullable=False)
    intake_id   = db.Column(db.Integer, db.ForeignKey("intakes.id"))

    # Pipeline
    current_stage = db.Column(db.String(40), default=ApplicationStageEnum.INTERESTED,
                              nullable=False)
    is_active     = db.Column(db.Boolean, default=True)

    # Tracking
    submitted_at    = db.Column(db.DateTime)
    offer_issued_at = db.Column(db.DateTime)
    enrolled_at     = db.Column(db.DateTime)
    visa_submitted_at = db.Column(db.DateTime)
    visa_approved_at  = db.Column(db.DateTime)

    # Internal
    priority      = db.Column(db.String(20), default="normal")  # low | normal | high | urgent
    internal_notes= db.Column(db.Text)

    # Meta
    created_by  = db.Column(db.Integer, db.ForeignKey("users.id"))
    assigned_to = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                            onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    student     = db.relationship("Student",  back_populates="applications")
    program     = db.relationship("Program",  back_populates="applications")
    intake      = db.relationship("Intake",   back_populates="applications")
    creator     = db.relationship("User",     foreign_keys=[created_by])
    assignee    = db.relationship("User",     foreign_keys=[assigned_to])
    stages      = db.relationship("ApplicationStage", back_populates="application",
                                  lazy="dynamic", cascade="all, delete-orphan",
                                  order_by="ApplicationStage.created_at")
    offers      = db.relationship("Offer", back_populates="application",
                                  lazy="dynamic", cascade="all, delete-orphan")
    commission  = db.relationship("Commission", back_populates="application",
                                  uselist=False)

    @property
    def stage_index(self) -> int:
        try:
            return STAGE_ORDER.index(self.current_stage)
        except ValueError:
            return -1

    @property
    def stage_label(self) -> str:
        return STAGE_LABELS.get(self.current_stage, self.current_stage)

    @property
    def progress_pct(self) -> int:
        idx = self.stage_index
        if idx < 0:
            return 0
        return int((idx / (len(STAGE_ORDER) - 1)) * 100)

    def advance_stage(self, new_stage: str, changed_by_id: int, notes: str = None):
        """Advance to a new pipeline stage and record it."""
        self.current_stage = new_stage
        stage_entry = ApplicationStage(
            application_id=self.id,
            stage=new_stage,
            notes=notes,
            changed_by=changed_by_id,
        )
        db.session.add(stage_entry)
        # Update timestamp shortcuts
        _now = datetime.now(timezone.utc)
        if new_stage == ApplicationStageEnum.APPLICATION_SUBMITTED:
            self.submitted_at = _now
        elif new_stage == ApplicationStageEnum.OFFER_ISSUED:
            self.offer_issued_at = _now
        elif new_stage == ApplicationStageEnum.VISA_SUBMITTED:
            self.visa_submitted_at = _now
        elif new_stage == ApplicationStageEnum.VISA_APPROVED:
            self.visa_approved_at = _now
        elif new_stage == ApplicationStageEnum.ENROLLED:
            self.enrolled_at = _now
        db.session.commit()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "reference": self.reference,
            "student": self.student.full_name if self.student else None,
            "program": self.program.name if self.program else None,
            "school": self.program.school.name if self.program and self.program.school else None,
            "stage": self.current_stage,
            "stage_label": self.stage_label,
            "progress_pct": self.progress_pct,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<Application {self.reference} [{self.current_stage}]>"


# ── Application Stage (audit trail) ──────────────────────────────────────────

class ApplicationStage(db.Model):
    __tablename__ = "application_stages"

    id             = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id"), nullable=False)
    stage          = db.Column(db.String(40), nullable=False)
    notes          = db.Column(db.Text)
    changed_by     = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at     = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    application = db.relationship("Application", back_populates="stages")
    changer     = db.relationship("User")

    @property
    def stage_label(self) -> str:
        return STAGE_LABELS.get(self.stage, self.stage)

    def __repr__(self):
        return f"<ApplicationStage app={self.application_id} stage={self.stage}>"
