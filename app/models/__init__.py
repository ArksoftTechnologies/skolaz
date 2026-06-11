"""
Skolaz v2.0 — Models Package
Import all models here so Alembic/Flask-Migrate can discover them.
"""
from app.models.user import User, Role, Permission          # noqa: F401
from app.models.geography import Country, State, City, Campus  # noqa: F401
from app.models.institution import School, Program, Intake, TuitionFee, Scholarship  # noqa: F401
from app.models.student import Student, StudentDocument      # noqa: F401
from app.models.agency import Agency, AgencyUser             # noqa: F401
from app.models.application import Application, ApplicationStage  # noqa: F401
from app.models.offer import Offer, OfferCondition           # noqa: F401
from app.models.system import SystemSetting          # noqa: F401
from app.models.commission import Commission                  # noqa: F401
from app.models.communication import Chat, Notification, EmailLog  # noqa: F401
from app.models.collaboration import Task, Note, Meeting     # noqa: F401
from app.models.audit import AuditLog, Activity              # noqa: F401
