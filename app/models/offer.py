"""
Skolaz v2.0 — Offer & Offer Condition Models
Multi-type offers with full approval chain
"""
import enum
from datetime import datetime, timezone
from app.extensions import db


class OfferType(str, enum.Enum):
    CONDITIONAL   = "conditional"
    UNCONDITIONAL = "unconditional"
    SCHOLARSHIP   = "scholarship"
    DEPOSIT_REQUEST = "deposit_request"
    FINAL_ACCEPTANCE = "final_acceptance"


class OfferStatus(str, enum.Enum):
    UPLOADED          = "uploaded"    # Advisor uploaded
    STAFF_REVIEW      = "staff_review"
    MANAGER_APPROVED  = "manager_approved"
    STUDENT_NOTIFIED  = "student_notified"
    STUDENT_ACCEPTED  = "student_accepted"
    STUDENT_REJECTED  = "student_rejected"
    EXPIRED           = "expired"
    WITHDRAWN         = "withdrawn"


# ── Offer ─────────────────────────────────────────────────────────────────────

class Offer(db.Model):
    __tablename__ = "offers"

    id             = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id"), nullable=False)
    offer_type     = db.Column(db.String(30), nullable=False, default=OfferType.CONDITIONAL)
    status         = db.Column(db.String(30), nullable=False, default=OfferStatus.UPLOADED)

    # Offer details
    reference_number   = db.Column(db.String(100))
    offered_program    = db.Column(db.String(200))  # May differ from applied program
    offered_start_date = db.Column(db.Date)
    offer_expiry_date  = db.Column(db.Date)
    tuition_amount     = db.Column(db.Numeric(12, 2))
    deposit_amount     = db.Column(db.Numeric(12, 2))
    currency           = db.Column(db.String(10), default="GBP")
    scholarship_amount = db.Column(db.Numeric(12, 2))

    # Files
    offer_letter_url   = db.Column(db.String(1000))
    additional_docs_url= db.Column(db.String(1000))

    # Notes
    internal_notes = db.Column(db.Text)
    student_message= db.Column(db.Text)

    # Approval chain timestamps
    uploaded_at       = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    staff_reviewed_at = db.Column(db.DateTime)
    approved_at       = db.Column(db.DateTime)
    student_notified_at = db.Column(db.DateTime)
    student_responded_at = db.Column(db.DateTime)

    # Actors
    uploaded_by  = db.Column(db.Integer, db.ForeignKey("users.id"))
    reviewed_by  = db.Column(db.Integer, db.ForeignKey("users.id"))
    approved_by  = db.Column(db.Integer, db.ForeignKey("users.id"))

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    application = db.relationship("Application", back_populates="offers")
    uploader    = db.relationship("User", foreign_keys=[uploaded_by])
    reviewer    = db.relationship("User", foreign_keys=[reviewed_by])
    approver    = db.relationship("User", foreign_keys=[approved_by])
    conditions  = db.relationship("OfferCondition", back_populates="offer",
                                  lazy="dynamic", cascade="all, delete-orphan")

    @property
    def all_conditions_met(self) -> bool:
        return all(c.is_met for c in self.conditions)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "application_id": self.application_id,
            "offer_type": self.offer_type,
            "status": self.status,
            "offer_letter_url": self.offer_letter_url,
            "offer_expiry_date": self.offer_expiry_date.isoformat() if self.offer_expiry_date else None,
        }

    def __repr__(self):
        return f"<Offer {self.id} type={self.offer_type} status={self.status}>"


# ── Offer Condition ───────────────────────────────────────────────────────────

class OfferCondition(db.Model):
    __tablename__ = "offer_conditions"

    id             = db.Column(db.Integer, primary_key=True)
    offer_id       = db.Column(db.Integer, db.ForeignKey("offers.id"), nullable=False)
    condition_text = db.Column(db.Text, nullable=False)
    is_met         = db.Column(db.Boolean, default=False)
    met_at         = db.Column(db.DateTime)
    met_by         = db.Column(db.Integer, db.ForeignKey("users.id"))
    notes          = db.Column(db.Text)
    created_at     = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    offer   = db.relationship("Offer", back_populates="conditions")
    met_user= db.relationship("User")

    def __repr__(self):
        return f"<OfferCondition offer={self.offer_id} met={self.is_met}>"
