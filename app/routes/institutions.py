"""Re-export individual blueprints from feature_routes for clean imports."""
from app.routes.feature_routes import (
    institutions_bp,
    applications_bp,
    offers_bp,
    documents_bp,
    students_bp,
    commissions_bp,
    reports_bp,
)
