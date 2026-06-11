"""
Skolaz v2.0 — Agency & Agency User Models
"""
import enum
from datetime import datetime, timezone
from app.extensions import db


class AgencyStatus(str, enum.Enum):
    PENDING   = "pending"
    APPROVED  = "approved"
    SUSPENDED = "suspended"
    REJECTED  = "rejected"


# ── Agency ────────────────────────────────────────────────────────────────────

class Agency(db.Model):
    __tablename__ = "agencies"

    id                 = db.Column(db.Integer, primary_key=True)
    name               = db.Column(db.String(200), nullable=False)
    slug               = db.Column(db.String(200), unique=True)
    registration_number= db.Column(db.String(100))
    country_id         = db.Column(db.Integer, db.ForeignKey("countries.id"))
    state              = db.Column(db.String(100))
    city               = db.Column(db.String(100))
    address            = db.Column(db.String(500))
    website            = db.Column(db.String(500))
    email              = db.Column(db.String(120))
    phone              = db.Column(db.String(30))
    logo_url           = db.Column(db.String(1000))
    years_in_business  = db.Column(db.Integer)
    description        = db.Column(db.Text)

    # Documents
    cac_cert_url       = db.Column(db.String(1000))
    business_reg_url   = db.Column(db.String(1000))
    tax_doc_url        = db.Column(db.String(1000))
    agreement_url      = db.Column(db.String(1000))
    agreement_signed_at= db.Column(db.DateTime)

    # Commission
    default_commission_pct = db.Column(db.Numeric(5, 2), default=10.0)

    # Status & approval
    status      = db.Column(db.String(20), default=AgencyStatus.PENDING)
    approved_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    approved_at = db.Column(db.DateTime)
    suspended_reason = db.Column(db.Text)

    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                            onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    country     = db.relationship("Country",    back_populates="agencies")
    approver    = db.relationship("User",       foreign_keys=[approved_by])
    agency_users= db.relationship("AgencyUser", back_populates="agency",
                                  lazy="dynamic", cascade="all, delete-orphan")
    students    = db.relationship("Student",    back_populates="agency", lazy="dynamic")
    commissions = db.relationship("Commission", back_populates="agency", lazy="dynamic")

    @property
    def admin_user(self):
        return self.agency_users.filter_by(is_admin=True).first()

    @property
    def student_count(self) -> int:
        return self.students.count()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "country": self.country.name if self.country else None,
            "status": self.status,
            "student_count": self.student_count,
        }

    def __repr__(self):
        return f"<Agency {self.name}>"


# ── Agency User ───────────────────────────────────────────────────────────────

class AgencyUser(db.Model):
    __tablename__ = "agency_users"

    id         = db.Column(db.Integer, primary_key=True)
    agency_id  = db.Column(db.Integer, db.ForeignKey("agencies.id"),  nullable=False)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"),     nullable=False)
    is_admin   = db.Column(db.Boolean, default=False)
    title      = db.Column(db.String(100))

    # Granular permissions (override role defaults)
    can_register_students = db.Column(db.Boolean, default=True)
    can_view_commissions  = db.Column(db.Boolean, default=False)
    can_manage_team       = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    agency = db.relationship("Agency", back_populates="agency_users")
    user   = db.relationship("User")

    __table_args__ = (
        db.UniqueConstraint("agency_id", "user_id", name="uq_agency_user"),
    )

    def __repr__(self):
        return f"<AgencyUser agency={self.agency_id} user={self.user_id}>"
