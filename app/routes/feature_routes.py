"""Skolaz v2.0 — Feature Blueprints (fully implemented)"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.utils.decorators import internal_only
from app.utils.helpers import get_page_args, Paginator, generate_reference, slugify
from app.models.institution import School, Program, Intake
from app.models.geography import Country
from app.extensions import db

# ── Institutions ──────────────────────────────────────────────
institutions_bp = Blueprint("institutions", __name__)

@institutions_bp.get("/schools")
@login_required
@internal_only
def schools():
    page, per_page = get_page_args()
    q       = request.args.get("q", "")
    country = request.args.get("country", "")
    status  = request.args.get("status", "")
    query   = School.query
    if q:
        query = query.filter(School.name.ilike(f"%{q}%"))
    if country:
        query = query.filter(School.country_id == country)
    if status:
        query = query.filter_by(status=status)
    paginator = Paginator(query.order_by(School.name), page, per_page)
    countries = Country.query.filter_by(status="active").order_by(Country.name).all()
    return render_template("institutions/schools.html",
                           paginator=paginator, q=q, countries=countries,
                           country=country, status=status)


@institutions_bp.get("/schools/<int:school_id>")
@login_required
@internal_only
def school_detail(school_id):
    school   = School.query.get_or_404(school_id)
    programs = school.programs.order_by(Program.name).all()
    return render_template("institutions/school_detail.html",
                           school=school, programs=programs)


@institutions_bp.post("/schools/<int:school_id>/status")
@login_required
@internal_only
def toggle_school_status(school_id):
    school = School.query.get_or_404(school_id)
    new_status = request.form.get("status", "active")
    school.status      = new_status
    school.approved_by = current_user.id
    db.session.commit()
    flash(f"School '{school.name}' status updated to {new_status}.", "success")
    return redirect(url_for("institutions.school_detail", school_id=school_id))


@institutions_bp.get("/programs")
@login_required
@internal_only
def programs():
    page, per_page = get_page_args()
    q      = request.args.get("q", "")
    level  = request.args.get("level", "")
    school = request.args.get("school_id", "")
    query  = Program.query
    if q:
        query = query.filter(Program.name.ilike(f"%{q}%"))
    if level:
        query = query.filter_by(level=level)
    if school:
        query = query.filter_by(school_id=school)
    paginator = Paginator(query.order_by(Program.name), page, per_page)
    schools   = School.query.filter_by(status="active").order_by(School.name).all()
    return render_template("institutions/programs.html",
                           paginator=paginator, q=q, level=level,
                           schools=schools, school=school)


@institutions_bp.get("/programs/<int:program_id>")
@login_required
@internal_only
def program_detail(program_id):
    program = Program.query.get_or_404(program_id)
    intakes = program.intakes.order_by(Intake.year.desc(), Intake.month.desc()).all()
    return render_template("institutions/program_detail.html",
                           program=program, intakes=intakes)


# ── Applications ──────────────────────────────────────────────
from app.models.application import Application, ApplicationStage, STAGE_ORDER, STAGE_LABELS
from app.models.student import Student
from app.services.audit_service import log_action, log_activity

applications_bp = Blueprint("applications", __name__)


@applications_bp.get("/")
@login_required
@internal_only
def index():
    page, per_page = get_page_args()
    stage    = request.args.get("stage", "")
    priority = request.args.get("priority", "")
    q        = request.args.get("q", "")
    query    = Application.query

    if stage:
        query = query.filter_by(current_stage=stage)
    if priority:
        query = query.filter_by(priority=priority)
    if q:
        query = query.join(Application.student).filter(
            db.or_(
                Student.first_name.ilike(f"%{q}%"),
                Student.last_name.ilike(f"%{q}%"),
                Application.reference.ilike(f"%{q}%"),
            )
        )

    # Scope to advisor's own students if advisor role
    if current_user.is_advisor:
        query = query.join(Application.student).filter(
            Student.primary_advisor_id == current_user.id
        )

    paginator = Paginator(query.order_by(Application.updated_at.desc()), page, per_page)
    return render_template("applications/index.html",
                           paginator=paginator, stage=stage,
                           priority=priority, q=q,
                           STAGE_LABELS=STAGE_LABELS, STAGE_ORDER=STAGE_ORDER)


@applications_bp.get("/create")
@login_required
@internal_only
def create():
    students = Student.query.filter_by(is_active=True).order_by(Student.first_name).all()
    schools  = School.query.filter_by(status="active").order_by(School.name).all()
    return render_template("applications/create.html",
                           students=students, schools=schools,
                           STAGE_LABELS=STAGE_LABELS)


@applications_bp.post("/create")
@login_required
@internal_only
def create_post():
    student_id = request.form.get("student_id", type=int)
    program_id = request.form.get("program_id", type=int)
    intake_id  = request.form.get("intake_id",  type=int)
    priority   = request.form.get("priority", "normal")
    notes      = request.form.get("internal_notes", "")

    student = Student.query.get_or_404(student_id)
    program = Program.query.get_or_404(program_id)

    app = Application(
        reference=generate_reference("SKZ"),
        student_id=student_id,
        program_id=program_id,
        intake_id=intake_id or None,
        priority=priority,
        internal_notes=notes,
        created_by=current_user.id,
        assigned_to=student.primary_advisor_id or current_user.id,
    )
    db.session.add(app)
    db.session.flush()

    # Create initial stage entry
    stage_entry = ApplicationStage(
        application_id=app.id,
        stage="interested",
        notes="Application created",
        changed_by=current_user.id,
    )
    db.session.add(stage_entry)
    db.session.commit()

    log_action("application.created", "applications", current_user.id,
               app.id, "Application", f"Created application {app.reference}")
    log_activity(student_id, "Application created",
                 f"Application {app.reference} created for {program.name}",
                 current_user.id, "document", "blue")

    flash(f"Application {app.reference} created successfully.", "success")
    return redirect(url_for("applications.detail", app_id=app.id))


@applications_bp.get("/<int:app_id>")
@login_required
@internal_only
def detail(app_id):
    application = Application.query.get_or_404(app_id)
    stage_history = application.stages.order_by(ApplicationStage.created_at).all()
    offers = application.offers.order_by("created_at").all()
    return render_template("applications/detail.html",
                           application=application,
                           stage_history=stage_history,
                           offers=offers,
                           STAGE_LABELS=STAGE_LABELS,
                           STAGE_ORDER=STAGE_ORDER)


@applications_bp.post("/<int:app_id>/advance")
@login_required
@internal_only
def advance_stage(app_id):
    application = Application.query.get_or_404(app_id)
    new_stage = request.form.get("stage")
    notes     = request.form.get("notes", "")

    if new_stage not in STAGE_LABELS:
        flash("Invalid stage.", "error")
        return redirect(url_for("applications.detail", app_id=app_id))

    old_stage = application.current_stage
    application.advance_stage(new_stage, current_user.id, notes)

    log_action("application.stage_changed", "applications", current_user.id,
               application.id, "Application",
               f"Stage changed from {old_stage} to {new_stage}")
    log_activity(application.student_id, "Stage updated",
                 f"Moved to {STAGE_LABELS[new_stage]}",
                 current_user.id, "arrow-right", "blue",
                 url_for("applications.detail", app_id=app_id))

    # Broadcast real-time update
    try:
        from app.sockets import broadcast_stage_change
        broadcast_stage_change(application.id, new_stage, current_user.full_name)
    except Exception:
        pass

    flash(f"Application moved to: {STAGE_LABELS[new_stage]}", "success")
    return redirect(url_for("applications.detail", app_id=app_id))


@applications_bp.post("/<int:app_id>/note")
@login_required
@internal_only
def add_note(app_id):
    from app.models.collaboration import Note
    application = Application.query.get_or_404(app_id)
    content = request.form.get("content", "").strip()
    if not content:
        flash("Note cannot be empty.", "error")
        return redirect(url_for("applications.detail", app_id=app_id))

    note = Note(
        student_id=application.student_id,
        author_id=current_user.id,
        content=content,
        application_id=app_id,
        is_internal=True,
    )
    db.session.add(note)
    db.session.commit()
    flash("Note added.", "success")
    return redirect(url_for("applications.detail", app_id=app_id))


# ── Offers ────────────────────────────────────────────────────
from app.models.offer import Offer, OfferCondition, OfferStatus, OfferType
from datetime import datetime, timezone

offers_bp = Blueprint("offers", __name__)


@offers_bp.get("/")
@login_required
@internal_only
def index():
    page, per_page = get_page_args()
    status = request.args.get("status", "")
    query  = Offer.query
    if status:
        query = query.filter_by(status=status)
    paginator = Paginator(query.order_by(Offer.created_at.desc()), page, per_page)
    return render_template("offers/index.html",
                           paginator=paginator, status=status,
                           OfferStatus=OfferStatus)


@offers_bp.get("/<int:offer_id>")
@login_required
@internal_only
def detail(offer_id):
    offer = Offer.query.get_or_404(offer_id)
    conditions = offer.conditions.all()
    return render_template("offers/detail.html",
                           offer=offer, conditions=conditions,
                           OfferStatus=OfferStatus, OfferType=OfferType)


@offers_bp.post("/<int:offer_id>/approve")
@login_required
def approve_offer(offer_id):
    offer = Offer.query.get_or_404(offer_id)
    offer.status      = OfferStatus.MANAGER_APPROVED
    offer.approved_by = current_user.id
    offer.approved_at = datetime.now(timezone.utc)
    db.session.commit()

    log_action("offer.approved", "offers", current_user.id, offer.id, "Offer",
               f"Offer {offer.id} approved")
    flash("Offer approved.", "success")
    return redirect(url_for("offers.detail", offer_id=offer_id))


@offers_bp.post("/<int:offer_id>/notify-student")
@login_required
def notify_student(offer_id):
    offer = Offer.query.get_or_404(offer_id)
    offer.status             = OfferStatus.STUDENT_NOTIFIED
    offer.student_notified_at = datetime.now(timezone.utc)
    db.session.commit()

    # Push real-time notification
    try:
        from app.sockets import push_notification
        student_user = offer.application.student.user
        if student_user:
            push_notification(student_user.id, "New Offer Available",
                              "You have a new offer to review.", "offer")
    except Exception:
        pass

    flash("Student notified of the offer.", "success")
    return redirect(url_for("offers.detail", offer_id=offer_id))


# ── Documents ─────────────────────────────────────────────────
from app.models.student import StudentDocument, DocumentStatus
from app.services.storage_service import upload_file, delete_file

documents_bp = Blueprint("documents", __name__)


@documents_bp.get("/")
@login_required
@internal_only
def index():
    page, per_page = get_page_args()
    status   = request.args.get("status", "")
    category = request.args.get("category", "")
    q        = request.args.get("q", "")
    query    = StudentDocument.query
    if status:
        query = query.filter_by(status=status)
    if category:
        query = query.filter_by(category=category)
    if q:
        query = query.join(StudentDocument.student).filter(
            db.or_(
                Student.first_name.ilike(f"%{q}%"),
                Student.last_name.ilike(f"%{q}%"),
                StudentDocument.doc_type.ilike(f"%{q}%"),
            )
        )
    paginator = Paginator(query.order_by(StudentDocument.created_at.desc()), page, per_page)
    return render_template("documents/index.html",
                           paginator=paginator, status=status,
                           category=category, q=q,
                           DocumentStatus=DocumentStatus)


@documents_bp.post("/<int:doc_id>/review")
@login_required
@internal_only
def review_document(doc_id):
    doc    = StudentDocument.query.get_or_404(doc_id)
    action = request.form.get("action")  # approve | reject

    if action == "approve":
        doc.status      = DocumentStatus.APPROVED
        doc.reviewed_by = current_user.id
        doc.reviewed_at = datetime.now(timezone.utc)
        db.session.commit()
        log_activity(doc.student_id, "Document approved",
                     f"{doc.doc_type} approved by {current_user.full_name}",
                     current_user.id, "check-circle", "green")
        flash("Document approved.", "success")
    elif action == "reject":
        doc.status           = DocumentStatus.REJECTED
        doc.reviewed_by      = current_user.id
        doc.reviewed_at      = datetime.now(timezone.utc)
        doc.rejection_reason = request.form.get("reason", "")
        db.session.commit()
        log_activity(doc.student_id, "Document rejected",
                     f"{doc.doc_type} rejected: {doc.rejection_reason}",
                     current_user.id, "x-circle", "red")
        flash("Document rejected.", "warning")
    else:
        flash("Unknown action.", "error")

    return redirect(request.referrer or url_for("documents.index"))


# ── Students ──────────────────────────────────────────────────
students_bp = Blueprint("students", __name__)


@students_bp.get("/")
@login_required
@internal_only
def index():
    page, per_page = get_page_args()
    q       = request.args.get("q", "")
    source  = request.args.get("source", "")
    advisor = request.args.get("advisor_id", "")
    query   = Student.query.filter_by(is_archived=False)

    if q:
        query = query.filter(
            db.or_(
                Student.first_name.ilike(f"%{q}%"),
                Student.last_name.ilike(f"%{q}%"),
                Student.email.ilike(f"%{q}%"),
            )
        )
    if source:
        query = query.filter_by(source=source)
    if advisor:
        query = query.filter_by(primary_advisor_id=advisor)

    # Advisors only see their own students
    if current_user.is_advisor:
        query = query.filter_by(primary_advisor_id=current_user.id)

    paginator = Paginator(query.order_by(Student.created_at.desc()), page, per_page)

    from app.models.user import User, RoleSlug
    advisors = User.query.join(User.role).filter(
        db.or_(
            User.role.has(slug=RoleSlug.ADVISOR),
            User.role.has(slug=RoleSlug.STAFF),
        ),
        User.is_deleted == False
    ).order_by(User.first_name).all()

    return render_template("students/index.html",
                           paginator=paginator, q=q, source=source,
                           advisor=advisor, advisors=advisors)


@students_bp.get("/create")
@login_required
@internal_only
def create():
    from app.models.user import User, RoleSlug
    from app.models.agency import Agency
    countries = Country.query.filter_by(status="active").order_by(Country.name).all()
    advisors  = User.query.join(User.role).filter(
        db.or_(
            User.role.has(slug=RoleSlug.ADVISOR),
            User.role.has(slug=RoleSlug.STAFF),
        ),
        User.is_deleted == False
    ).order_by(User.first_name).all()
    agencies = Agency.query.filter_by(status="approved").order_by(Agency.name).all()
    return render_template("students/create.html",
                           countries=countries, advisors=advisors, agencies=agencies)


@students_bp.post("/create")
@login_required
@internal_only
def create_post():
    from app.models.agency import Agency
    first_name = request.form.get("first_name", "").strip()
    last_name  = request.form.get("last_name",  "").strip()
    email      = request.form.get("email",      "").strip().lower()
    phone      = request.form.get("phone",      "").strip()

    if not first_name or not last_name or not email:
        flash("First name, last name, and email are required.", "error")
        return redirect(url_for("students.create"))

    if Student.query.filter_by(email=email).first():
        flash("A student with that email already exists.", "error")
        return redirect(url_for("students.create"))

    student = Student(
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
        whatsapp=request.form.get("whatsapp", "").strip(),
        nationality_country_id=request.form.get("nationality_country_id", type=int) or None,
        country_of_residence_id=request.form.get("country_of_residence_id", type=int) or None,
        highest_qualification=request.form.get("highest_qualification", "").strip(),
        english_test=request.form.get("english_test", ""),
        english_score=request.form.get("english_score", type=float) or None,
        primary_advisor_id=request.form.get("primary_advisor_id", type=int) or None,
        agency_id=request.form.get("agency_id", type=int) or None,
        source=request.form.get("source", "direct"),
        notes=request.form.get("notes", "").strip(),
        created_by=current_user.id,
    )
    db.session.add(student)
    db.session.commit()

    log_action("student.created", "students", current_user.id,
               student.id, "Student", f"Created student {student.full_name}")
    flash(f"Student {student.full_name} added successfully.", "success")
    return redirect(url_for("students.detail", student_id=student.id))


@students_bp.get("/<int:student_id>")
@login_required
@internal_only
def detail(student_id):
    from app.models.collaboration import Task, Note, Meeting
    from app.models.audit import Activity
    student      = Student.query.get_or_404(student_id)
    applications = student.applications.order_by(Application.created_at.desc()).all()
    documents    = student.documents.filter_by(is_latest=True).order_by("created_at").all()
    tasks        = student.tasks.filter(
        Task.status.in_(["open", "in_progress"])
    ).order_by(Task.due_date).limit(5).all()
    notes    = student.notes_list.order_by(Note.is_pinned.desc(), Note.created_at.desc()).limit(10).all()
    meetings = student.meetings.order_by(Meeting.scheduled_at.desc()).limit(5).all()
    activities = Activity.query.filter_by(student_id=student_id).order_by(
        Activity.created_at.desc()
    ).limit(20).all()
    return render_template("students/detail.html",
                           student=student,
                           applications=applications,
                           documents=documents,
                           tasks=tasks,
                           notes=notes,
                           meetings=meetings,
                           activities=activities,
                           STAGE_LABELS=STAGE_LABELS)


@students_bp.post("/<int:student_id>/edit")
@login_required
@internal_only
def edit(student_id):
    student = Student.query.get_or_404(student_id)
    student.first_name   = request.form.get("first_name", student.first_name).strip()
    student.last_name    = request.form.get("last_name",  student.last_name).strip()
    student.phone        = request.form.get("phone",      student.phone)
    student.whatsapp     = request.form.get("whatsapp",   student.whatsapp)
    student.address      = request.form.get("address",    student.address)
    student.city         = request.form.get("city",       student.city)
    student.notes        = request.form.get("notes",      student.notes)
    student.primary_advisor_id = request.form.get("primary_advisor_id", type=int) or student.primary_advisor_id
    db.session.commit()
    flash("Student profile updated.", "success")
    return redirect(url_for("students.detail", student_id=student_id))


@students_bp.post("/<int:student_id>/archive")
@login_required
@internal_only
def archive(student_id):
    student = Student.query.get_or_404(student_id)
    student.is_archived = True
    student.archived_at = datetime.now(timezone.utc)
    student.is_active   = False
    db.session.commit()
    flash(f"Student {student.full_name} archived.", "warning")
    return redirect(url_for("students.index"))


# ── Commissions ───────────────────────────────────────────────
from app.models.commission import Commission, CommissionStatus

commissions_bp = Blueprint("commissions", __name__)


@commissions_bp.get("/")
@login_required
@internal_only
def index():
    page, per_page = get_page_args()
    status   = request.args.get("status", "")
    agency   = request.args.get("agency_id", "")
    query    = Commission.query

    if status:
        query = query.filter_by(status=status)
    if agency:
        query = query.filter_by(agency_id=agency)

    paginator = Paginator(query.order_by(Commission.created_at.desc()), page, per_page)

    # Aggregates
    totals = db.session.query(
        db.func.sum(Commission.expected_amount).label("expected"),
        db.func.sum(Commission.received_amount).label("received"),
    ).one()

    from app.models.agency import Agency
    agencies = Agency.query.filter_by(status="approved").order_by(Agency.name).all()

    return render_template("commissions/index.html",
                           paginator=paginator, status=status,
                           agency=agency, agencies=agencies,
                           totals=totals,
                           CommissionStatus=CommissionStatus)


@commissions_bp.post("/<int:commission_id>/record-payment")
@login_required
@internal_only
def record_payment(commission_id):
    from datetime import date
    commission = Commission.query.get_or_404(commission_id)
    amount = request.form.get("amount", type=float)
    reference = request.form.get("reference", "").strip()

    if not amount or amount <= 0:
        flash("Please enter a valid payment amount.", "error")
        return redirect(url_for("commissions.index"))

    commission.received_amount  = float(commission.received_amount or 0) + amount
    commission.payment_reference = reference
    commission.payment_received_date = date.today()

    if commission.received_amount >= float(commission.expected_amount or 0):
        commission.status = CommissionStatus.PAID
    else:
        commission.status = CommissionStatus.PARTIAL

    db.session.commit()
    log_action("commission.payment_recorded", "commissions", current_user.id,
               commission.id, "Commission",
               f"Payment of {amount} recorded for commission {commission.id}")
    flash(f"Payment of {amount} recorded.", "success")
    return redirect(url_for("commissions.index"))


# ── Reports ───────────────────────────────────────────────────
reports_bp = Blueprint("reports", __name__)


@reports_bp.get("/")
@login_required
@internal_only
def index():
    from app.models.agency import Agency
    # Top-level stats for report overview
    stats = {
        "total_students":     Student.query.count(),
        "total_applications": Application.query.count(),
        "enrolled":           Application.query.filter_by(current_stage="enrolled").count(),
        "visa_approved":      Application.query.filter_by(current_stage="visa_approved").count(),
        "pending_commissions": db.session.query(
            db.func.coalesce(
                db.func.sum(Commission.expected_amount - Commission.received_amount), 0
            )
        ).filter(Commission.status.in_([CommissionStatus.PENDING, CommissionStatus.INVOICED])).scalar(),
    }
    return render_template("reports/index.html", stats=stats)


@reports_bp.get("/funnel")
@login_required
@internal_only
def student_funnel():
    funnel = {}
    for stage in STAGE_ORDER:
        funnel[stage] = Application.query.filter_by(current_stage=stage).count()
    return render_template("reports/student_funnel.html",
                           funnel=funnel, STAGE_LABELS=STAGE_LABELS)


@reports_bp.get("/commissions")
@login_required
@internal_only
def commissions_report():
    from app.models.agency import Agency
    agencies = Agency.query.filter_by(status="approved").all()
    data = []
    for ag in agencies:
        expected = db.session.query(
            db.func.coalesce(db.func.sum(Commission.expected_amount), 0)
        ).filter_by(agency_id=ag.id).scalar()
        received = db.session.query(
            db.func.coalesce(db.func.sum(Commission.received_amount), 0)
        ).filter_by(agency_id=ag.id).scalar()
        data.append({
            "agency": ag,
            "expected": float(expected),
            "received": float(received),
            "outstanding": float(expected) - float(received),
        })
    return render_template("reports/commissions.html", data=data)


@reports_bp.get("/api/funnel-data")
@login_required
@internal_only
def funnel_data_api():
    """JSON endpoint for chart rendering."""
    funnel = {stage: Application.query.filter_by(current_stage=stage).count()
              for stage in STAGE_ORDER}
    return jsonify(success=True, data=funnel)
