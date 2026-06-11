"""
Skolaz v2.0 — Commission Model
Tracks expected, received, and outstanding commissions per agency per application
"""
import enum
from datetime import datetime, timezone
from app.extensions import db


class CommissionStatus(str, enum.Enum):
    PENDING    = "pending"
    INVOICED   = "invoiced"
    PARTIAL    = "partial"
    PAID       = "paid"
    DISPUTED   = "disputed"
    CANCELLED  = "cancelled"


class Commission(db.Model):
    __tablename__ = "commissions"

    id             = db.Column(db.Integer, primary_key=True)
    agency_id      = db.Column(db.Integer, db.ForeignKey("agencies.id"),      nullable=False)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id"),  nullable=False, unique=True)
    school_id      = db.Column(db.Integer, db.ForeignKey("schools.id"))
    program_id     = db.Column(db.Integer, db.ForeignKey("programs.id"))

    # Commission amounts
    commission_pct      = db.Column(db.Numeric(5, 2))           # percentage
    expected_amount     = db.Column(db.Numeric(12, 2))
    invoiced_amount     = db.Column(db.Numeric(12, 2), default=0)
    received_amount     = db.Column(db.Numeric(12, 2), default=0)
    currency            = db.Column(db.String(10), default="GBP")

    # Status
    status              = db.Column(db.String(20), default=CommissionStatus.PENDING)

    # Invoice details
    invoice_number      = db.Column(db.String(50))
    invoice_date        = db.Column(db.Date)
    invoice_url         = db.Column(db.String(1000))
    payment_due_date    = db.Column(db.Date)
    payment_received_date = db.Column(db.Date)
    payment_reference   = db.Column(db.String(100))

    # Notes
    notes               = db.Column(db.Text)
    dispute_reason      = db.Column(db.Text)

    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    agency      = db.relationship("Agency",      back_populates="commissions")
    application = db.relationship("Application", back_populates="commission")
    school      = db.relationship("School")
    program     = db.relationship("Program")
    creator     = db.relationship("User")

    @property
    def outstanding_amount(self):
        if self.expected_amount is None:
            return 0
        return float(self.expected_amount) - float(self.received_amount or 0)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "agency": self.agency.name if self.agency else None,
            "school": self.school.name if self.school else None,
            "expected_amount": float(self.expected_amount) if self.expected_amount else 0,
            "received_amount": float(self.received_amount) if self.received_amount else 0,
            "outstanding_amount": self.outstanding_amount,
            "currency": self.currency,
            "status": self.status,
        }

    def __repr__(self):
        return f"<Commission agency={self.agency_id} app={self.application_id} status={self.status}>"
