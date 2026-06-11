"""Skolaz v2.0 — Agency Blueprint"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import current_user
from app.extensions import db
from app.utils.decorators import agency_required
from app.utils.helpers import get_page_args, Paginator
from app.models.agency import Agency, AgencyUser
from app.models.student import Student
from app.models.application import Application
from app.models.commission import Commission

agency_bp = Blueprint("agency", __name__)

@agency_bp.before_request
def require_agency():
    # /register and /register POST are public
    if request.endpoint in ("agency.register", "agency.register_post"):
        return None
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login", next=request.url))
    if not current_user.is_active_account:
        abort(403)
    if not current_user.role or current_user.role.slug not in ("agency", "agency_member", "super_admin"):
        abort(403)

def _my_agency():
    au = AgencyUser.query.filter_by(user_id=current_user.id).first()
    return au.agency if au else None

@agency_bp.get("/")
def dashboard():
    agency = _my_agency()
    if not agency:
        flash("No agency linked to your account.", "error")
        return redirect(url_for("public.home"))

    student_count = agency.students.count()
    app_count = Application.query.join(Student).filter(Student.agency_id == agency.id).count()
    offer_count = Application.query.join(Student).filter(
        Student.agency_id == agency.id,
        Application.current_stage == "offer_issued"
    ).count()
    commission_total = db.session.query(
        db.func.sum(Commission.received_amount)
    ).filter_by(agency_id=agency.id).scalar() or 0
    pending_commission = db.session.query(
        db.func.sum(Commission.expected_amount - Commission.received_amount)
    ).filter_by(agency_id=agency.id).scalar() or 0

    stats = {
        "students_registered": student_count,
        "applications_submitted": app_count,
        "offers_received": offer_count,
        "revenue_generated": float(commission_total),
        "pending_commissions": float(pending_commission),
    }
    recent_students = agency.students.order_by(Student.created_at.desc()).limit(5).all()
    return render_template("agency/dashboard.html", agency=agency,
                           stats=stats, recent_students=recent_students)

@agency_bp.get("/students")
def students():
    agency = _my_agency()
    if not agency:
        return redirect(url_for("public.home"))
    page, per_page = get_page_args()
    q = request.args.get("q", "")
    query = agency.students
    if q:
        query = query.filter(
            Student.first_name.ilike(f"%{q}%") | Student.last_name.ilike(f"%{q}%")
        )
    paginator = Paginator(query.order_by(Student.created_at.desc()), page, per_page)
    return render_template("agency/students.html", paginator=paginator, q=q, agency=agency)

@agency_bp.get("/commissions")
def commissions():
    agency = _my_agency()
    if not agency:
        return redirect(url_for("public.home"))
    items = Commission.query.filter_by(agency_id=agency.id).order_by(
        Commission.created_at.desc()
    ).all()
    return render_template("agency/commissions.html", commissions=items, agency=agency)

@agency_bp.get("/register")
def register():
    """Public agency registration form."""
    return render_template("agency/register.html")

@agency_bp.post("/register")
def register_post():
    flash("Registration submitted. Our team will review and contact you shortly.", "success")
    return redirect(url_for("public.home"))
