"""Skolaz v2.0 — Advisor Blueprint"""
from flask import Blueprint, render_template, request, redirect, url_for, abort
from flask_login import current_user
from app.utils.decorators import advisor_or_above
from app.utils.helpers import get_page_args, Paginator
from app.models.student import Student
from app.models.application import Application
from app.models.collaboration import Task

advisor_bp = Blueprint("advisor", __name__)

@advisor_bp.before_request
def require_advisor():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login", next=request.url))
    if not current_user.is_active_account:
        abort(403)
    if not current_user.role or current_user.role.slug not in ("super_admin", "staff", "advisor"):
        abort(403)

@advisor_bp.get("/")
def dashboard():
    my_students = Student.query.filter_by(primary_advisor_id=current_user.id).all()
    my_tasks = Task.query.filter_by(assigned_to=current_user.id, status="open").order_by(Task.due_date).limit(5).all()
    pending_offers = Application.query.filter_by(
        current_stage="offer_issued", assigned_to=current_user.id
    ).count()
    stats = {
        "active_students": len(my_students),
        "pending_tasks":   Task.query.filter_by(assigned_to=current_user.id, status="open").count(),
        "pending_offers":  pending_offers,
        "missing_docs":    Application.query.filter_by(
            current_stage="documents_pending", assigned_to=current_user.id
        ).count(),
    }
    recent_students = Student.query.filter_by(
        primary_advisor_id=current_user.id
    ).order_by(Student.created_at.desc()).limit(6).all()
    return render_template("advisor/dashboard.html", stats=stats,
                           recent_students=recent_students, my_tasks=my_tasks)

@advisor_bp.get("/students")
def students():
    page, per_page = get_page_args()
    q = request.args.get("q", "")
    query = Student.query.filter_by(primary_advisor_id=current_user.id)
    if q:
        query = query.filter(
            Student.first_name.ilike(f"%{q}%") | Student.last_name.ilike(f"%{q}%")
        )
    paginator = Paginator(query.order_by(Student.created_at.desc()), page, per_page)
    return render_template("advisor/students.html", paginator=paginator, q=q)

@advisor_bp.get("/tasks")
def tasks():
    page, per_page = get_page_args()
    status = request.args.get("status", "open")
    query = Task.query.filter_by(assigned_to=current_user.id)
    if status:
        query = query.filter_by(status=status)
    paginator = Paginator(query.order_by(Task.due_date), page, per_page)
    return render_template("advisor/tasks.html", paginator=paginator, status=status)
