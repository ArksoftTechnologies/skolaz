"""Skolaz v2.0 — Staff Blueprint"""
from flask import Blueprint, render_template, request, redirect, url_for, abort
from flask_login import current_user
from app.utils.decorators import staff_or_above
from app.utils.helpers import get_page_args, Paginator
from app.models.student import Student
from app.models.application import Application

staff_bp = Blueprint("staff", __name__)

@staff_bp.before_request
def require_staff():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login", next=request.url))
    if not current_user.is_active_account:
        abort(403)
    if not current_user.role or current_user.role.slug not in ("super_admin", "staff"):
        abort(403)

@staff_bp.get("/")
def dashboard():
    stats = {
        "total_students":   Student.query.count(),
        "total_applications": Application.query.count(),
        "pending_offers":   Application.query.filter_by(current_stage="offer_issued").count(),
        "visa_submitted":   Application.query.filter_by(current_stage="visa_submitted").count(),
    }
    recent = Application.query.order_by(Application.updated_at.desc()).limit(8).all()
    return render_template("staff/dashboard.html", stats=stats, recent=recent)

@staff_bp.get("/students")
def students():
    page, per_page = get_page_args()
    q = request.args.get("q", "")
    query = Student.query
    if q:
        query = query.filter(
            Student.first_name.ilike(f"%{q}%") | Student.last_name.ilike(f"%{q}%") |
            Student.email.ilike(f"%{q}%")
        )
    paginator = Paginator(query.order_by(Student.created_at.desc()), page, per_page)
    return render_template("staff/students.html", paginator=paginator, q=q)

@staff_bp.get("/applications")
def applications():
    page, per_page = get_page_args()
    stage = request.args.get("stage", "")
    query = Application.query
    if stage:
        query = query.filter_by(current_stage=stage)
    paginator = Paginator(query.order_by(Application.updated_at.desc()), page, per_page)
    return render_template("staff/applications.html", paginator=paginator, stage=stage)
