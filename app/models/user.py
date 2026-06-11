"""
Skolaz v2.0 — User, Role & Permission Models
Supports: Super Admin, Staff, Advisor, Data Entry, Agency, Student
"""
import enum
from datetime import datetime, timezone
from flask_login import UserMixin
from app.extensions import db


# ── Enums ─────────────────────────────────────────────────────────────────────

class RoleSlug(str, enum.Enum):
    SUPER_ADMIN  = "super_admin"
    STAFF        = "staff"
    ADVISOR      = "advisor"
    DATA_ENTRY   = "data_entry"
    AGENCY       = "agency"
    AGENCY_MEMBER= "agency_member"
    STUDENT      = "student"


class UserStatus(str, enum.Enum):
    ACTIVE    = "active"
    INACTIVE  = "inactive"
    SUSPENDED = "suspended"
    PENDING   = "pending"


# ── Role ──────────────────────────────────────────────────────────────────────

class Role(db.Model):
    __tablename__ = "roles"

    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(64), nullable=False)
    slug        = db.Column(db.String(32), unique=True, nullable=False)
    description = db.Column(db.String(255))
    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    users       = db.relationship("User", back_populates="role", lazy="dynamic")
    permissions = db.relationship("Permission", back_populates="role",
                                  cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Role {self.slug}>"

    @classmethod
    def get_by_slug(cls, slug: str) -> "Role | None":
        return cls.query.filter_by(slug=slug).first()


# ── Permission ────────────────────────────────────────────────────────────────

class Permission(db.Model):
    __tablename__ = "permissions"

    id         = db.Column(db.Integer, primary_key=True)
    role_id    = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    module     = db.Column(db.String(64), nullable=False)  # e.g. "students", "offers"
    can_read   = db.Column(db.Boolean, default=True)
    can_write  = db.Column(db.Boolean, default=False)
    can_delete = db.Column(db.Boolean, default=False)

    role = db.relationship("Role", back_populates="permissions")

    __table_args__ = (
        db.UniqueConstraint("role_id", "module", name="uq_role_module"),
    )

    def __repr__(self):
        return f"<Permission role={self.role_id} module={self.module}>"


# ── User ──────────────────────────────────────────────────────────────────────

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id            = db.Column(db.Integer, primary_key=True)
    email         = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name    = db.Column(db.String(64), nullable=False)
    last_name     = db.Column(db.String(64), nullable=False)
    phone         = db.Column(db.String(20))
    avatar_url    = db.Column(db.String(500))
    role_id       = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    status        = db.Column(db.String(20), default=UserStatus.ACTIVE, nullable=False)

    # MFA
    mfa_enabled   = db.Column(db.Boolean, default=False)
    mfa_secret    = db.Column(db.String(64))

    # Timestamps
    created_at    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                              onupdate=lambda: datetime.now(timezone.utc))
    last_login    = db.Column(db.DateTime)
    last_ip       = db.Column(db.String(45))

    # Email verification
    email_verified     = db.Column(db.Boolean, default=False)
    email_verify_token = db.Column(db.String(128))

    # Password reset
    reset_token        = db.Column(db.String(128))
    reset_token_expiry = db.Column(db.DateTime)

    # Soft delete
    is_deleted    = db.Column(db.Boolean, default=False)
    deleted_at    = db.Column(db.DateTime)

    # Relationships
    role              = db.relationship("Role", back_populates="users")
    notifications     = db.relationship("Notification", back_populates="user",
                                        lazy="dynamic", cascade="all, delete-orphan")
    tasks_assigned    = db.relationship("Task", foreign_keys="Task.assigned_to",
                                        back_populates="assignee", lazy="dynamic")
    tasks_created     = db.relationship("Task", foreign_keys="Task.created_by",
                                        back_populates="creator", lazy="dynamic")
    notes             = db.relationship("Note", back_populates="author", lazy="dynamic")
    audit_logs        = db.relationship("AuditLog", back_populates="user", lazy="dynamic")

    # ── Computed Properties ───────────────────────────────────

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def initials(self) -> str:
        return f"{self.first_name[0]}{self.last_name[0]}".upper()

    def set_password(self, password: str):
        from app.extensions import bcrypt
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password: str) -> bool:
        from app.extensions import bcrypt
        return bcrypt.check_password_hash(self.password_hash, password)

    @property
    def is_super_admin(self) -> bool:
        return self.role.slug == RoleSlug.SUPER_ADMIN

    @property
    def is_staff(self) -> bool:
        return self.role.slug == RoleSlug.STAFF

    @property
    def is_advisor(self) -> bool:
        return self.role.slug == RoleSlug.ADVISOR

    @property
    def is_data_entry(self) -> bool:
        return self.role.slug == RoleSlug.DATA_ENTRY

    @property
    def is_agency(self) -> bool:
        return self.role.slug in (RoleSlug.AGENCY, RoleSlug.AGENCY_MEMBER)

    @property
    def is_student_user(self) -> bool:
        return self.role.slug == RoleSlug.STUDENT

    @property
    def is_active_account(self) -> bool:
        return self.status == UserStatus.ACTIVE and not self.is_deleted

    def has_permission(self, module: str, action: str = "read") -> bool:
        """Check if user's role has a specific permission."""
        if self.is_super_admin:
            return True
        perm = Permission.query.filter_by(
            role_id=self.role_id, module=module
        ).first()
        if not perm:
            return False
        return getattr(perm, f"can_{action}", False)

    def record_login(self, ip: str = None):
        self.last_login = datetime.now(timezone.utc)
        self.last_ip = ip
        db.session.commit()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role.slug if self.role else None,
            "status": self.status,
            "avatar_url": self.avatar_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<User {self.email}>"
