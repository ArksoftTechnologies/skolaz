"""
Skolaz v2.0 — Geographic Data Models
Hierarchy: Country → State/Province → City → Campus
"""
import enum
from datetime import datetime, timezone
from app.extensions import db


class GeoStatus(str, enum.Enum):
    ACTIVE   = "active"
    INACTIVE = "inactive"


# ── Country ───────────────────────────────────────────────────────────────────

class Country(db.Model):
    __tablename__ = "countries"

    id                      = db.Column(db.Integer, primary_key=True)
    name                    = db.Column(db.String(100), nullable=False, unique=True)
    iso_code                = db.Column(db.String(3), nullable=False, unique=True)
    iso2_code               = db.Column(db.String(2))
    flag_emoji              = db.Column(db.String(10))
    logo_url                = db.Column(db.String(500))
    currency                = db.Column(db.String(10))
    currency_symbol         = db.Column(db.String(5))
    timezone                = db.Column(db.String(64))
    phone_code              = db.Column(db.String(10))
    status                  = db.Column(db.String(20), default=GeoStatus.ACTIVE)
    is_featured             = db.Column(db.Boolean, default=False)
    student_visa_info       = db.Column(db.Text)
    description             = db.Column(db.Text)
    cover_image_url         = db.Column(db.String(500))

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))

    # Relationships
    states   = db.relationship("State",   back_populates="country",
                               lazy="dynamic", cascade="all, delete-orphan")
    cities   = db.relationship("City",    back_populates="country", lazy="dynamic")
    schools  = db.relationship("School",  back_populates="country", lazy="dynamic")
    students = db.relationship("Student", back_populates="nationality_country",
                               lazy="dynamic", foreign_keys="Student.nationality_country_id")
    agencies = db.relationship("Agency",  back_populates="country", lazy="dynamic")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "iso_code": self.iso_code,
            "flag_emoji": self.flag_emoji,
            "currency": self.currency,
            "status": self.status,
        }

    def __repr__(self):
        return f"<Country {self.iso_code}:{self.name}>"


# ── State / Province ──────────────────────────────────────────────────────────

class State(db.Model):
    __tablename__ = "states"

    id         = db.Column(db.Integer, primary_key=True)
    country_id = db.Column(db.Integer, db.ForeignKey("countries.id"), nullable=False)
    name       = db.Column(db.String(100), nullable=False)
    code       = db.Column(db.String(10))
    status     = db.Column(db.String(20), default=GeoStatus.ACTIVE)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))

    # Relationships
    country  = db.relationship("Country", back_populates="states")
    cities   = db.relationship("City", back_populates="state",
                               lazy="dynamic", cascade="all, delete-orphan")

    __table_args__ = (
        db.UniqueConstraint("country_id", "name", name="uq_state_country_name"),
    )

    def __repr__(self):
        return f"<State {self.name}, {self.country_id}>"


# ── City ──────────────────────────────────────────────────────────────────────

class City(db.Model):
    __tablename__ = "cities"

    id         = db.Column(db.Integer, primary_key=True)
    state_id   = db.Column(db.Integer, db.ForeignKey("states.id"))
    country_id = db.Column(db.Integer, db.ForeignKey("countries.id"), nullable=False)
    name       = db.Column(db.String(100), nullable=False)
    status     = db.Column(db.String(20), default=GeoStatus.ACTIVE)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))

    # Relationships
    state    = db.relationship("State",   back_populates="cities")
    country  = db.relationship("Country", back_populates="cities")
    campuses = db.relationship("Campus",  back_populates="city", lazy="dynamic")
    schools  = db.relationship("School",  back_populates="city", lazy="dynamic")

    def __repr__(self):
        return f"<City {self.name}>"


# ── Campus ────────────────────────────────────────────────────────────────────

class Campus(db.Model):
    __tablename__ = "campuses"

    id          = db.Column(db.Integer, primary_key=True)
    school_id   = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    city_id     = db.Column(db.Integer, db.ForeignKey("cities.id"))
    name        = db.Column(db.String(150), nullable=False)
    address     = db.Column(db.String(500))
    postal_code = db.Column(db.String(20))
    latitude    = db.Column(db.Numeric(9, 6))
    longitude   = db.Column(db.Numeric(9, 6))
    is_main     = db.Column(db.Boolean, default=False)
    phone       = db.Column(db.String(30))
    email       = db.Column(db.String(120))

    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    school = db.relationship("School", back_populates="campuses")
    city   = db.relationship("City",   back_populates="campuses")

    def __repr__(self):
        return f"<Campus {self.name}>"
