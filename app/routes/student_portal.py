"""Skolaz v2.0 — Student Portal Blueprint"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import current_user
from app.extensions import db
from app.utils.decorators import student_required
from app.models.student import Student
from app.models.application import Application
from app.models.communication import Chat, Notification

student_portal_bp = Blueprint("student_portal", __name__)

@student_portal_bp.before_request
def require_student():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login", next=request.url))
    if not current_user.is_active_account:
        abort(403)
    if not current_user.role or current_user.role.slug not in ("student", "super_admin"):
        abort(403)

def _my_profile():
    return Student.query.filter_by(user_id=current_user.id).first()

@student_portal_bp.get("/")
def dashboard():
    student = _my_profile()
    if not student:
        flash("Student profile not found. Contact your advisor.", "warning")
        return render_template("student/no_profile.html")

    applications  = student.applications.order_by(Application.created_at.desc()).all()
    active_app    = student.active_application
    documents     = student.documents.filter_by(is_latest=True).order_by("created_at").all()
    advisor       = student.primary_advisor
    unread_notifs = Notification.query.filter_by(
        user_id=current_user.id, is_read=False
    ).count()

    # Document checklist stats
    doc_pending  = student.documents.filter_by(status="pending").count()
    doc_approved = student.documents.filter_by(status="approved").count()
    doc_rejected = student.documents.filter_by(status="rejected").count()

    # Upcoming meetings
    from app.models.collaboration import Meeting
    from datetime import datetime, timezone
    upcoming_meetings = student.meetings.filter(
        Meeting.scheduled_at >= datetime.now(timezone.utc)
    ).order_by(Meeting.scheduled_at).limit(3).all()

    return render_template("student/dashboard.html",
                           student=student,
                           applications=applications,
                           active_app=active_app,
                           documents=documents,
                           advisor=advisor,
                           unread_notifs=unread_notifs,
                           doc_pending=doc_pending,
                           doc_approved=doc_approved,
                           doc_rejected=doc_rejected,
                           upcoming_meetings=upcoming_meetings)

@student_portal_bp.get("/applications")
def applications():
    student = _my_profile()
    if not student:
        return redirect(url_for("student_portal.dashboard"))
    apps = student.applications.order_by(Application.created_at.desc()).all()
    return render_template("student/applications.html", student=student, applications=apps)

@student_portal_bp.get("/documents")
def documents():
    student = _my_profile()
    if not student:
        return redirect(url_for("student_portal.dashboard"))
    docs = student.documents.order_by("created_at").all()
    return render_template("student/documents.html", student=student, documents=docs)

@student_portal_bp.get("/messages")
def messages():
    student = _my_profile()
    if not student:
        return redirect(url_for("student_portal.dashboard"))
    chats = Chat.query.filter_by(student_id=student.id).order_by(Chat.created_at).all()
    return render_template("student/messages.html", student=student, chats=chats)

@student_portal_bp.get("/notifications")
def notifications():
    notifs = Notification.query.filter_by(user_id=current_user.id).order_by(
        Notification.created_at.desc()
    ).limit(50).all()
    for n in notifs:
        if not n.is_read:
            n.mark_read()
    return render_template("student/notifications.html", notifications=notifs)

@student_portal_bp.get("/appointments")
def appointments():
    student = _my_profile()
    if not student:
        return redirect(url_for("student_portal.dashboard"))
    meetings = student.meetings.order_by("scheduled_at").all()
    return render_template("student/appointments.html", student=student, meetings=meetings)
