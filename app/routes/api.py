"""
Skolaz v2.0 — API Blueprint
Health check + shared HTMX partials API
All responses: { success, data, message, errors }
"""
from flask import Blueprint, jsonify, current_app, request

api_bp = Blueprint("api", __name__)


@api_bp.get("/health")
def health_check():
    """GET /api/health — liveness probe."""
    return jsonify(
        success=True,
        data={"version": current_app.config.get("APP_VERSION", "2.0.0"),
              "status": "healthy"},
        message="Skolaz API is running",
        errors=[],
    ), 200


@api_bp.get("/version")
def version():
    return jsonify(
        success=True,
        data={"version": current_app.config.get("APP_VERSION", "2.0.0")},
        message="OK",
        errors=[],
    ), 200


@api_bp.get("/programs-by-school")
def programs_by_school():
    """HTMX endpoint — returns <option> list of programs for a given school_id."""
    from flask import render_template_string
    from app.models.institution import Program
    school_id = request.args.get("school_id_picker", type=int)
    programs = []
    if school_id:
        programs = Program.query.filter_by(school_id=school_id, status="active").order_by(Program.name).all()
    html = '<option value="">Select program...</option>'
    for p in programs:
        html += f'<option value="{p.id}">{p.name}</option>'
    return html, 200


@api_bp.get("/intakes-by-program")
def intakes_by_program():
    """HTMX endpoint — returns <option> list of intakes for a given program_id."""
    from app.models.institution import Intake
    program_id = request.args.get("program_id", type=int)
    intakes = []
    if program_id:
        intakes = Intake.query.filter_by(program_id=program_id, is_open=True).order_by(
            Intake.year.desc(), Intake.month.desc()
        ).all()
    months = ['','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    html = '<option value="">No specific intake</option>'
    for i in intakes:
        html += f'<option value="{i.id}">{months[i.month]} {i.year}</option>'
    return html, 200


@api_bp.get("/notifications/unread-count")
def unread_notifications():
    from flask_login import current_user
    from app.models.communication import Notification
    if not current_user.is_authenticated:
        return jsonify(count=0)
    count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify(success=True, count=count)
