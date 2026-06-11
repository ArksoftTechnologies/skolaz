"""
Skolaz v2.0 — Data Entry Blueprint
Full catalog management: Countries, States, Cities, Campuses, Schools, Programs, Intakes
Accessible to: super_admin, staff, advisor, data_entry
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify
from flask_login import current_user
from app.extensions import db
from app.utils.helpers import slugify
from app.models.geography import Country, State, City, Campus
from app.models.institution import School, Program, Intake, TuitionFee, Scholarship

data_entry_bp = Blueprint("data_entry", __name__)

ALLOWED_ROLES = ("super_admin", "staff", "advisor", "data_entry")


@data_entry_bp.before_request
def require_data_entry():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login", next=request.url))
    if not current_user.is_active_account:
        abort(403)
    if not current_user.role or current_user.role.slug not in ALLOWED_ROLES:
        abort(403)


# ── Dashboard ─────────────────────────────────────────────────────────────────

@data_entry_bp.get("/")
def dashboard():
    stats = {
        "countries":    Country.query.count(),
        "states":       State.query.count(),
        "cities":       City.query.count(),
        "schools":      School.query.count(),
        "programs":     Program.query.count(),
        "pending":      School.query.filter_by(status="pending").count(),
        "intakes":      Intake.query.count(),
        "scholarships": Scholarship.query.count(),
    }
    recent_schools = School.query.order_by(School.created_at.desc()).limit(8).all()
    return render_template("data_entry/dashboard.html", stats=stats,
                           recent_schools=recent_schools)


# ══════════════════════════════════════════════════════════════
# GEOGRAPHY
# ══════════════════════════════════════════════════════════════

# ── Countries ─────────────────────────────────────────────────

@data_entry_bp.get("/countries")
def countries():
    q = request.args.get("q", "")
    query = Country.query
    if q:
        query = query.filter(Country.name.ilike(f"%{q}%"))
    items = query.order_by(Country.name).all()
    return render_template("data_entry/countries.html", countries=items, q=q)


@data_entry_bp.post("/countries")
def create_country():
    name     = request.form.get("name", "").strip()
    iso_code = request.form.get("iso_code", "").strip().upper()
    if not name or not iso_code:
        flash("Country name and ISO code are required.", "error")
        return redirect(url_for("data_entry.countries"))
    if Country.query.filter_by(iso_code=iso_code).first():
        flash(f"A country with ISO code '{iso_code}' already exists.", "error")
        return redirect(url_for("data_entry.countries"))
    c = Country(
        name=name,
        iso_code=iso_code,
        iso2_code=request.form.get("iso2_code", "").strip().upper() or None,
        flag_emoji=request.form.get("flag_emoji", "").strip() or None,
        currency=request.form.get("currency", "").strip() or None,
        currency_symbol=request.form.get("currency_symbol", "").strip() or None,
        phone_code=request.form.get("phone_code", "").strip() or None,
        timezone=request.form.get("timezone", "").strip() or None,
        is_featured=bool(request.form.get("is_featured")),
        description=request.form.get("description", "").strip() or None,
        student_visa_info=request.form.get("student_visa_info", "").strip() or None,
        created_by=current_user.id,
    )
    db.session.add(c)
    db.session.commit()
    flash(f"Country '{c.name}' added successfully.", "success")
    return redirect(url_for("data_entry.countries"))


@data_entry_bp.post("/countries/<int:country_id>/edit")
def edit_country(country_id):
    country = Country.query.get_or_404(country_id)
    country.name           = request.form.get("name", country.name).strip()
    country.flag_emoji     = request.form.get("flag_emoji", "").strip() or country.flag_emoji
    country.currency       = request.form.get("currency", "").strip() or country.currency
    country.currency_symbol= request.form.get("currency_symbol", "").strip() or country.currency_symbol
    country.phone_code     = request.form.get("phone_code", "").strip() or country.phone_code
    country.timezone       = request.form.get("timezone", "").strip() or country.timezone
    country.is_featured    = bool(request.form.get("is_featured"))
    country.status         = request.form.get("status", country.status)
    country.description    = request.form.get("description", "").strip() or None
    country.student_visa_info = request.form.get("student_visa_info", "").strip() or None
    db.session.commit()
    flash(f"Country '{country.name}' updated.", "success")
    return redirect(url_for("data_entry.country_detail", country_id=country_id))


@data_entry_bp.get("/countries/<int:country_id>")
def country_detail(country_id):
    country = Country.query.get_or_404(country_id)
    states  = country.states.order_by(State.name).all()
    cities  = country.cities.order_by(City.name).limit(20).all()
    return render_template("data_entry/country_detail.html",
                           country=country, states=states, cities=cities)


# ── States ────────────────────────────────────────────────────

@data_entry_bp.get("/states")
def states():
    country_id = request.args.get("country_id", type=int)
    q = request.args.get("q", "")
    query = State.query
    if country_id:
        query = query.filter_by(country_id=country_id)
    if q:
        query = query.filter(State.name.ilike(f"%{q}%"))
    items = query.order_by(State.name).all()
    countries = Country.query.filter_by(status="active").order_by(Country.name).all()
    return render_template("data_entry/states.html",
                           states=items, countries=countries,
                           country_id=country_id, q=q)


@data_entry_bp.post("/states")
def create_state():
    country_id = request.form.get("country_id", type=int)
    name = request.form.get("name", "").strip()
    if not country_id or not name:
        flash("Country and state name are required.", "error")
        return redirect(url_for("data_entry.states"))
    s = State(
        country_id=country_id,
        name=name,
        code=request.form.get("code", "").strip().upper() or None,
        created_by=current_user.id,
    )
    db.session.add(s)
    db.session.commit()
    flash(f"State '{s.name}' added.", "success")
    return redirect(url_for("data_entry.states", country_id=country_id))


@data_entry_bp.post("/states/<int:state_id>/edit")
def edit_state(state_id):
    state = State.query.get_or_404(state_id)
    state.name   = request.form.get("name", state.name).strip()
    state.code   = request.form.get("code", "").strip().upper() or state.code
    state.status = request.form.get("status", state.status)
    db.session.commit()
    flash(f"State '{state.name}' updated.", "success")
    return redirect(url_for("data_entry.states", country_id=state.country_id))


@data_entry_bp.post("/states/<int:state_id>/delete")
def delete_state(state_id):
    state = State.query.get_or_404(state_id)
    country_id = state.country_id
    name = state.name
    db.session.delete(state)
    db.session.commit()
    flash(f"State '{name}' deleted.", "warning")
    return redirect(url_for("data_entry.states", country_id=country_id))


# ── Cities ────────────────────────────────────────────────────

@data_entry_bp.get("/cities")
def cities():
    country_id = request.args.get("country_id", type=int)
    state_id   = request.args.get("state_id", type=int)
    q = request.args.get("q", "")
    query = City.query
    if country_id:
        query = query.filter_by(country_id=country_id)
    if state_id:
        query = query.filter_by(state_id=state_id)
    if q:
        query = query.filter(City.name.ilike(f"%{q}%"))
    items     = query.order_by(City.name).all()
    countries = Country.query.filter_by(status="active").order_by(Country.name).all()
    states    = State.query.order_by(State.name).all()
    if country_id:
        states = State.query.filter_by(country_id=country_id).order_by(State.name).all()
    return render_template("data_entry/cities.html",
                           cities=items, countries=countries, states=states,
                           country_id=country_id, state_id=state_id, q=q)


@data_entry_bp.post("/cities")
def create_city():
    country_id = request.form.get("country_id", type=int)
    name = request.form.get("name", "").strip()
    if not country_id or not name:
        flash("Country and city name are required.", "error")
        return redirect(url_for("data_entry.cities"))
    c = City(
        country_id=country_id,
        state_id=request.form.get("state_id", type=int) or None,
        name=name,
        created_by=current_user.id,
    )
    db.session.add(c)
    db.session.commit()
    flash(f"City '{c.name}' added.", "success")
    return redirect(url_for("data_entry.cities", country_id=country_id))


@data_entry_bp.post("/cities/<int:city_id>/edit")
def edit_city(city_id):
    city = City.query.get_or_404(city_id)
    city.name   = request.form.get("name", city.name).strip()
    city.status = request.form.get("status", city.status)
    db.session.commit()
    flash(f"City '{city.name}' updated.", "success")
    return redirect(url_for("data_entry.cities", country_id=city.country_id))


@data_entry_bp.post("/cities/<int:city_id>/delete")
def delete_city(city_id):
    city = City.query.get_or_404(city_id)
    country_id = city.country_id
    name = city.name
    db.session.delete(city)
    db.session.commit()
    flash(f"City '{name}' deleted.", "warning")
    return redirect(url_for("data_entry.cities", country_id=country_id))


# ── HTMX: states by country ───────────────────────────────────

@data_entry_bp.get("/ajax/states")
def ajax_states():
    country_id = request.args.get("country_id", type=int)
    states = State.query.filter_by(country_id=country_id).order_by(State.name).all() if country_id else []
    html = '<option value="">Select state (optional)</option>'
    for s in states:
        html += f'<option value="{s.id}">{s.name}</option>'
    return html, 200


@data_entry_bp.get("/ajax/cities")
def ajax_cities():
    country_id = request.args.get("country_id", type=int)
    state_id   = request.args.get("state_id", type=int)
    query = City.query
    if state_id:
        query = query.filter_by(state_id=state_id)
    elif country_id:
        query = query.filter_by(country_id=country_id)
    cities = query.order_by(City.name).all()
    html = '<option value="">Select city (optional)</option>'
    for c in cities:
        html += f'<option value="{c.id}">{c.name}</option>'
    return html, 200


# ══════════════════════════════════════════════════════════════
# INSTITUTIONS
# ══════════════════════════════════════════════════════════════

# ── Schools ───────────────────────────────────────────────────

@data_entry_bp.get("/schools")
def schools():
    q       = request.args.get("q", "")
    country = request.args.get("country_id", "")
    status  = request.args.get("status", "")
    query   = School.query
    if q:
        query = query.filter(School.name.ilike(f"%{q}%"))
    if country:
        query = query.filter_by(country_id=country)
    if status:
        query = query.filter_by(status=status)
    items     = query.order_by(School.name).all()
    countries = Country.query.filter_by(status="active").order_by(Country.name).all()
    return render_template("data_entry/schools.html",
                           schools=items, countries=countries,
                           q=q, country=country, status=status)


@data_entry_bp.get("/schools/create")
def create_school():
    countries = Country.query.filter_by(status="active").order_by(Country.name).all()
    return render_template("data_entry/school_form.html",
                           school=None, countries=countries, edit=False)


@data_entry_bp.post("/schools/create")
def create_school_post():
    name = request.form.get("name", "").strip()
    if not name:
        flash("School name is required.", "error")
        return redirect(url_for("data_entry.create_school"))

    # Auto-generate unique slug
    base_slug = slugify(name)
    slug = base_slug
    counter = 1
    while School.query.filter_by(slug=slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    s = School(
        name=name,
        slug=slug,
        country_id=request.form.get("country_id", type=int) or None,
        state_id=request.form.get("state_id", type=int) or None,
        city_id=request.form.get("city_id", type=int) or None,
        address=request.form.get("address", "").strip() or None,
        website=request.form.get("website", "").strip() or None,
        email=request.form.get("email", "").strip() or None,
        phone=request.form.get("phone", "").strip() or None,
        short_description=request.form.get("short_description", "").strip() or None,
        description=request.form.get("description", "").strip() or None,
        institution_type=request.form.get("institution_type", "university"),
        ranking=request.form.get("ranking", type=int) or None,
        ranking_source=request.form.get("ranking_source", "").strip() or None,
        established_year=request.form.get("established_year", type=int) or None,
        international_students=request.form.get("international_students", type=int) or None,
        total_students=request.form.get("total_students", type=int) or None,
        acceptance_rate=request.form.get("acceptance_rate", type=float) or None,
        tuition_min=request.form.get("tuition_min", type=float) or None,
        tuition_max=request.form.get("tuition_max", type=float) or None,
        currency=request.form.get("currency", "GBP"),
        default_commission_pct=request.form.get("default_commission_pct", type=float) or None,
        is_featured=bool(request.form.get("is_featured")),
        is_partner=bool(request.form.get("is_partner")),
        requires_gmat=bool(request.form.get("requires_gmat")),
        requires_gre=bool(request.form.get("requires_gre")),
        status=request.form.get("status", "pending"),
        created_by=current_user.id,
    )
    db.session.add(s)
    db.session.commit()
    flash(f"School '{s.name}' created.", "success")
    return redirect(url_for("data_entry.school_detail", school_id=s.id))


@data_entry_bp.get("/schools/<int:school_id>")
def school_detail(school_id):
    school   = School.query.get_or_404(school_id)
    programs = school.programs.order_by(Program.name).all()
    campuses = school.campuses.all()
    countries = Country.query.filter_by(status="active").order_by(Country.name).all()
    cities    = City.query.filter_by(country_id=school.country_id).order_by(City.name).all() if school.country_id else []
    return render_template("data_entry/school_detail.html",
                           school=school, programs=programs,
                           campuses=campuses, countries=countries, cities=cities)


@data_entry_bp.post("/schools/<int:school_id>/edit")
def edit_school(school_id):
    school = School.query.get_or_404(school_id)
    school.name               = request.form.get("name", school.name).strip()
    school.country_id         = request.form.get("country_id", type=int) or school.country_id
    school.state_id           = request.form.get("state_id", type=int) or None
    school.city_id            = request.form.get("city_id", type=int) or None
    school.address            = request.form.get("address", "").strip() or None
    school.website            = request.form.get("website", "").strip() or None
    school.email              = request.form.get("email", "").strip() or None
    school.phone              = request.form.get("phone", "").strip() or None
    school.short_description  = request.form.get("short_description", "").strip() or None
    school.description        = request.form.get("description", "").strip() or None
    school.institution_type   = request.form.get("institution_type", school.institution_type)
    school.ranking            = request.form.get("ranking", type=int) or None
    school.ranking_source     = request.form.get("ranking_source", "").strip() or None
    school.established_year   = request.form.get("established_year", type=int) or None
    school.international_students = request.form.get("international_students", type=int) or None
    school.total_students     = request.form.get("total_students", type=int) or None
    school.acceptance_rate    = request.form.get("acceptance_rate", type=float) or None
    school.tuition_min        = request.form.get("tuition_min", type=float) or None
    school.tuition_max        = request.form.get("tuition_max", type=float) or None
    school.currency           = request.form.get("currency", school.currency)
    school.default_commission_pct = request.form.get("default_commission_pct", type=float) or None
    school.logo_url           = request.form.get("logo_url", "").strip() or school.logo_url
    school.cover_image_url    = request.form.get("cover_image_url", "").strip() or school.cover_image_url
    school.is_featured        = bool(request.form.get("is_featured"))
    school.is_partner         = bool(request.form.get("is_partner"))
    school.requires_gmat      = bool(request.form.get("requires_gmat"))
    school.requires_gre       = bool(request.form.get("requires_gre"))
    school.status             = request.form.get("status", school.status)
    db.session.commit()
    flash(f"School '{school.name}' updated.", "success")
    return redirect(url_for("data_entry.school_detail", school_id=school_id))


# ── Campuses ──────────────────────────────────────────────────

@data_entry_bp.post("/schools/<int:school_id>/campuses")
def create_campus(school_id):
    school = School.query.get_or_404(school_id)
    name = request.form.get("name", "").strip()
    if not name:
        flash("Campus name is required.", "error")
        return redirect(url_for("data_entry.school_detail", school_id=school_id))
    campus = Campus(
        school_id=school_id,
        city_id=request.form.get("city_id", type=int) or None,
        name=name,
        address=request.form.get("address", "").strip() or None,
        postal_code=request.form.get("postal_code", "").strip() or None,
        phone=request.form.get("phone", "").strip() or None,
        email=request.form.get("email", "").strip() or None,
        is_main=bool(request.form.get("is_main")),
    )
    db.session.add(campus)
    db.session.commit()
    flash(f"Campus '{campus.name}' added to {school.name}.", "success")
    return redirect(url_for("data_entry.school_detail", school_id=school_id))


@data_entry_bp.post("/campuses/<int:campus_id>/edit")
def edit_campus(campus_id):
    campus = Campus.query.get_or_404(campus_id)
    campus.name        = request.form.get("name", campus.name).strip()
    campus.address     = request.form.get("address", "").strip() or None
    campus.postal_code = request.form.get("postal_code", "").strip() or None
    campus.phone       = request.form.get("phone", "").strip() or None
    campus.email       = request.form.get("email", "").strip() or None
    campus.is_main     = bool(request.form.get("is_main"))
    db.session.commit()
    flash(f"Campus '{campus.name}' updated.", "success")
    return redirect(url_for("data_entry.school_detail", school_id=campus.school_id))


@data_entry_bp.post("/campuses/<int:campus_id>/delete")
def delete_campus(campus_id):
    campus = Campus.query.get_or_404(campus_id)
    school_id = campus.school_id
    name = campus.name
    db.session.delete(campus)
    db.session.commit()
    flash(f"Campus '{name}' removed.", "warning")
    return redirect(url_for("data_entry.school_detail", school_id=school_id))


# ══════════════════════════════════════════════════════════════
# PROGRAMS
# ══════════════════════════════════════════════════════════════

@data_entry_bp.get("/programs")
def programs():
    q         = request.args.get("q", "")
    school_id = request.args.get("school_id", "")
    level     = request.args.get("level", "")
    query     = Program.query
    if q:
        query = query.filter(Program.name.ilike(f"%{q}%"))
    if school_id:
        query = query.filter_by(school_id=school_id)
    if level:
        query = query.filter_by(level=level)
    items   = query.order_by(Program.name).all()
    schools = School.query.order_by(School.name).all()
    return render_template("data_entry/programs.html",
                           programs=items, schools=schools,
                           q=q, school_id=school_id, level=level)


@data_entry_bp.get("/programs/create")
def create_program():
    schools = School.query.filter_by(status="active").order_by(School.name).all()
    # Pre-select if school_id passed
    preselect_school = request.args.get("school_id", type=int)
    return render_template("data_entry/program_form.html",
                           program=None, schools=schools,
                           preselect_school=preselect_school, edit=False)


@data_entry_bp.post("/programs/create")
def create_program_post():
    school_id = request.form.get("school_id", type=int)
    name = request.form.get("name", "").strip()
    level = request.form.get("level", "").strip()
    if not school_id or not name or not level:
        flash("School, program name, and level are required.", "error")
        return redirect(url_for("data_entry.create_program"))

    p = Program(
        school_id=school_id,
        name=name,
        level=level,
        code=request.form.get("code", "").strip() or None,
        field_of_study=request.form.get("field_of_study", "").strip() or None,
        description=request.form.get("description", "").strip() or None,
        duration_months=request.form.get("duration_months", type=int) or None,
        study_mode=request.form.get("study_mode", "full-time"),
        ielts_requirement=request.form.get("ielts_requirement", type=float) or None,
        toefl_requirement=request.form.get("toefl_requirement", type=int) or None,
        pte_requirement=request.form.get("pte_requirement", type=float) or None,
        gpa_requirement=request.form.get("gpa_requirement", type=float) or None,
        gmat_requirement=request.form.get("gmat_requirement", type=int) or None,
        gre_requirement=request.form.get("gre_requirement", type=int) or None,
        min_work_experience=request.form.get("min_work_experience", type=int) or None,
        tuition_fee=request.form.get("tuition_fee", type=float) or None,
        currency=request.form.get("currency", "GBP"),
        application_fee=request.form.get("application_fee", type=float) or None,
        processing_weeks=request.form.get("processing_weeks", type=int) or None,
        brochure_url=request.form.get("brochure_url", "").strip() or None,
        is_featured=bool(request.form.get("is_featured")),
        status=request.form.get("status", "draft"),
        created_by=current_user.id,
    )
    db.session.add(p)
    db.session.commit()
    flash(f"Program '{p.name}' created.", "success")
    return redirect(url_for("data_entry.program_detail", program_id=p.id))


@data_entry_bp.get("/programs/<int:program_id>")
def program_detail(program_id):
    program = Program.query.get_or_404(program_id)
    intakes = program.intakes.order_by(Intake.year.desc(), Intake.month.desc()).all()
    return render_template("data_entry/program_detail.html",
                           program=program, intakes=intakes)


@data_entry_bp.post("/programs/<int:program_id>/edit")
def edit_program(program_id):
    program = Program.query.get_or_404(program_id)
    program.name               = request.form.get("name", program.name).strip()
    program.level              = request.form.get("level", program.level)
    program.code               = request.form.get("code", "").strip() or None
    program.field_of_study     = request.form.get("field_of_study", "").strip() or None
    program.description        = request.form.get("description", "").strip() or None
    program.duration_months    = request.form.get("duration_months", type=int) or None
    program.study_mode         = request.form.get("study_mode", program.study_mode)
    program.ielts_requirement  = request.form.get("ielts_requirement", type=float) or None
    program.toefl_requirement  = request.form.get("toefl_requirement", type=int) or None
    program.pte_requirement    = request.form.get("pte_requirement", type=float) or None
    program.gpa_requirement    = request.form.get("gpa_requirement", type=float) or None
    program.gmat_requirement   = request.form.get("gmat_requirement", type=int) or None
    program.gre_requirement    = request.form.get("gre_requirement", type=int) or None
    program.min_work_experience= request.form.get("min_work_experience", type=int) or None
    program.tuition_fee        = request.form.get("tuition_fee", type=float) or None
    program.currency           = request.form.get("currency", program.currency)
    program.application_fee    = request.form.get("application_fee", type=float) or None
    program.processing_weeks   = request.form.get("processing_weeks", type=int) or None
    program.brochure_url       = request.form.get("brochure_url", "").strip() or None
    program.is_featured        = bool(request.form.get("is_featured"))
    program.status             = request.form.get("status", program.status)
    if current_user.is_super_admin or current_user.is_staff:
        program.approved_by = current_user.id
    db.session.commit()
    flash(f"Program '{program.name}' updated.", "success")
    return redirect(url_for("data_entry.program_detail", program_id=program_id))


# ── Intakes ───────────────────────────────────────────────────

@data_entry_bp.post("/programs/<int:program_id>/intakes")
def create_intake(program_id):
    from datetime import date
    program = Program.query.get_or_404(program_id)
    month = request.form.get("month", type=int)
    year  = request.form.get("year", type=int)
    if not month or not year:
        flash("Month and year are required for an intake.", "error")
        return redirect(url_for("data_entry.program_detail", program_id=program_id))

    deadline_str = request.form.get("deadline", "").strip()
    deadline = None
    if deadline_str:
        try:
            from datetime import datetime
            deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    intake = Intake(
        program_id=program_id,
        month=month,
        year=year,
        deadline=deadline,
        spots_available=request.form.get("spots_available", type=int) or None,
        is_open=bool(request.form.get("is_open", True)),
        notes=request.form.get("notes", "").strip() or None,
    )
    db.session.add(intake)
    db.session.commit()
    flash(f"Intake {month}/{year} added to '{program.name}'.", "success")
    return redirect(url_for("data_entry.program_detail", program_id=program_id))


@data_entry_bp.post("/intakes/<int:intake_id>/edit")
def edit_intake(intake_id):
    intake = Intake.query.get_or_404(intake_id)
    intake.is_open          = bool(request.form.get("is_open"))
    intake.spots_available  = request.form.get("spots_available", type=int) or None
    deadline_str = request.form.get("deadline", "").strip()
    if deadline_str:
        try:
            from datetime import datetime
            intake.deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
        except ValueError:
            pass
    intake.notes = request.form.get("notes", "").strip() or None
    db.session.commit()
    flash("Intake updated.", "success")
    return redirect(url_for("data_entry.program_detail", program_id=intake.program_id))


@data_entry_bp.post("/intakes/<int:intake_id>/delete")
def delete_intake(intake_id):
    intake = Intake.query.get_or_404(intake_id)
    program_id = intake.program_id
    db.session.delete(intake)
    db.session.commit()
    flash("Intake removed.", "warning")
    return redirect(url_for("data_entry.program_detail", program_id=program_id))


# ══════════════════════════════════════════════════════════════
# CSV BULK IMPORT / EXPORT TEMPLATES
# ══════════════════════════════════════════════════════════════

import csv
import io
from flask import Response


def _csv_response(filename: str, headers: list, rows: list = None) -> Response:
    """Build a CSV download response."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    if rows:
        writer.writerows(rows)
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


# ── Template downloads ─────────────────────────────────────────

@data_entry_bp.get("/csv/template/<entity>")
def csv_template(entity):
    """Download a blank CSV template for bulk import."""
    templates = {
        "countries": (
            "skolaz_countries_template.csv",
            ["name", "iso_code", "iso2_code", "flag_emoji", "currency",
             "currency_symbol", "phone_code", "timezone", "is_featured",
             "student_visa_info", "description"],
            [["United Kingdom", "GBR", "GB", "🇬🇧", "GBP", "£", "+44",
              "Europe/London", "true", "Tier 4 student visa required.", "Top study destination."]]
        ),
        "states": (
            "skolaz_states_template.csv",
            ["country_iso_code", "name", "code"],
            [["GBR", "England", "ENG"], ["GBR", "Scotland", "SCT"]]
        ),
        "cities": (
            "skolaz_cities_template.csv",
            ["country_iso_code", "state_name", "name"],
            [["GBR", "England", "London"], ["GBR", "England", "Manchester"]]
        ),
        "campuses": (
            "skolaz_campuses_template.csv",
            ["school_name", "campus_name", "city_name", "country_iso_code",
             "address", "postal_code", "phone", "email", "is_main"],
            [["University of London", "Main Campus", "London", "GBR",
              "Senate House, Malet St", "WC1E 7HU", "+44 20 7862 8000",
              "info@london.ac.uk", "true"]]
        ),
        "schools": (
            "skolaz_schools_template.csv",
            ["name", "country_iso_code", "city_name", "website", "email", "phone",
             "institution_type", "ranking", "established_year", "currency",
             "tuition_min", "tuition_max", "default_commission_pct", "is_partner",
             "is_featured", "status", "short_description"],
            [["University of Toronto", "CAN", "Toronto", "https://utoronto.ca",
              "admissions@utoronto.ca", "+1 416 978 2011", "university", "18",
              "1827", "CAD", "6100", "14000", "10", "true", "false", "active",
              "Canada's top-ranked university."]]
        ),
        "programs": (
            "skolaz_programs_template.csv",
            ["school_name", "name", "level", "field_of_study", "study_mode",
             "duration_months", "currency", "tuition_fee", "application_fee",
             "ielts_requirement", "toefl_requirement", "gpa_requirement",
             "processing_weeks", "status"],
            [["University of Toronto", "BSc Computer Science", "bachelor",
              "Computer Science", "full-time", "48", "CAD", "12000", "150",
              "6.5", "90", "3.0", "8", "active"]]
        ),
    }
    if entity not in templates:
        flash("Unknown template type.", "error")
        return redirect(url_for("data_entry.dashboard"))

    filename, headers, sample_rows = templates[entity]
    return _csv_response(filename, headers, sample_rows)


# ── Bulk upload endpoint ───────────────────────────────────────

@data_entry_bp.get("/csv/import")
def csv_import_page():
    """Bulk import page."""
    return render_template("data_entry/csv_import.html")


@data_entry_bp.post("/csv/import/<entity>")
def csv_import(entity):
    """Process a CSV upload for the given entity type."""
    file = request.files.get("csv_file")
    if not file or not file.filename.endswith(".csv"):
        flash("Please upload a valid .csv file.", "error")
        return redirect(url_for("data_entry.csv_import_page"))

    stream   = io.StringIO(file.stream.read().decode("utf-8-sig"), newline=None)
    reader   = csv.DictReader(stream)
    rows     = list(reader)
    created  = 0
    skipped  = 0
    errors   = []

    if entity == "countries":
        for i, row in enumerate(rows, 2):
            try:
                iso = row.get("iso_code", "").strip().upper()
                name = row.get("name", "").strip()
                if not iso or not name:
                    skipped += 1; continue
                if Country.query.filter_by(iso_code=iso).first():
                    skipped += 1; continue
                c = Country(
                    name=name, iso_code=iso,
                    iso2_code=row.get("iso2_code", "").strip().upper() or None,
                    flag_emoji=row.get("flag_emoji", "").strip() or None,
                    currency=row.get("currency", "").strip() or None,
                    currency_symbol=row.get("currency_symbol", "").strip() or None,
                    phone_code=row.get("phone_code", "").strip() or None,
                    timezone=row.get("timezone", "").strip() or None,
                    is_featured=row.get("is_featured", "false").strip().lower() in ("true","1","yes"),
                    student_visa_info=row.get("student_visa_info", "").strip() or None,
                    description=row.get("description", "").strip() or None,
                    created_by=current_user.id,
                )
                db.session.add(c); created += 1
            except Exception as e:
                errors.append(f"Row {i}: {e}")
        db.session.commit()

    elif entity == "states":
        for i, row in enumerate(rows, 2):
            try:
                iso  = row.get("country_iso_code", "").strip().upper()
                name = row.get("name", "").strip()
                if not iso or not name: skipped += 1; continue
                country = Country.query.filter_by(iso_code=iso).first()
                if not country:
                    errors.append(f"Row {i}: Country '{iso}' not found."); continue
                if State.query.filter_by(country_id=country.id, name=name).first():
                    skipped += 1; continue
                db.session.add(State(
                    country_id=country.id, name=name,
                    code=row.get("code", "").strip().upper() or None,
                    created_by=current_user.id,
                )); created += 1
            except Exception as e:
                errors.append(f"Row {i}: {e}")
        db.session.commit()

    elif entity == "cities":
        for i, row in enumerate(rows, 2):
            try:
                iso        = row.get("country_iso_code", "").strip().upper()
                state_name = row.get("state_name", "").strip()
                city_name  = row.get("name", "").strip()
                if not iso or not city_name: skipped += 1; continue
                country = Country.query.filter_by(iso_code=iso).first()
                if not country:
                    errors.append(f"Row {i}: Country '{iso}' not found."); continue
                state = State.query.filter_by(country_id=country.id, name=state_name).first() if state_name else None
                if City.query.filter_by(country_id=country.id, name=city_name).first():
                    skipped += 1; continue
                db.session.add(City(
                    country_id=country.id,
                    state_id=state.id if state else None,
                    name=city_name,
                    created_by=current_user.id,
                )); created += 1
            except Exception as e:
                errors.append(f"Row {i}: {e}")
        db.session.commit()

    elif entity == "schools":
        from app.models.geography import Campus
        for i, row in enumerate(rows, 2):
            try:
                name = row.get("name", "").strip()
                iso  = row.get("country_iso_code", "").strip().upper()
                if not name or not iso: skipped += 1; continue
                if School.query.filter_by(name=name).first():
                    skipped += 1; continue
                country   = Country.query.filter_by(iso_code=iso).first()
                city_name = row.get("city_name", "").strip()
                city      = City.query.filter_by(name=city_name, country_id=country.id).first() if country and city_name else None
                base_slug = slugify(name); slug = base_slug; ctr = 1
                while School.query.filter_by(slug=slug).first():
                    slug = f"{base_slug}-{ctr}"; ctr += 1
                db.session.add(School(
                    name=name, slug=slug,
                    country_id=country.id if country else None,
                    city_id=city.id if city else None,
                    website=row.get("website", "").strip() or None,
                    email=row.get("email", "").strip() or None,
                    phone=row.get("phone", "").strip() or None,
                    institution_type=row.get("institution_type", "university").strip(),
                    ranking=int(row["ranking"]) if row.get("ranking", "").strip() else None,
                    established_year=int(row["established_year"]) if row.get("established_year", "").strip() else None,
                    currency=row.get("currency", "GBP").strip(),
                    tuition_min=float(row["tuition_min"]) if row.get("tuition_min", "").strip() else None,
                    tuition_max=float(row["tuition_max"]) if row.get("tuition_max", "").strip() else None,
                    default_commission_pct=float(row["default_commission_pct"]) if row.get("default_commission_pct", "").strip() else None,
                    is_partner=row.get("is_partner", "false").strip().lower() in ("true","1","yes"),
                    is_featured=row.get("is_featured", "false").strip().lower() in ("true","1","yes"),
                    status=row.get("status", "pending").strip(),
                    short_description=row.get("short_description", "").strip() or None,
                    created_by=current_user.id,
                )); created += 1
            except Exception as e:
                errors.append(f"Row {i}: {e}")
        db.session.commit()

    elif entity == "programs":
        for i, row in enumerate(rows, 2):
            try:
                school_name = row.get("school_name", "").strip()
                name        = row.get("name", "").strip()
                level       = row.get("level", "").strip()
                if not school_name or not name or not level: skipped += 1; continue
                school = School.query.filter(School.name.ilike(school_name)).first()
                if not school:
                    errors.append(f"Row {i}: School '{school_name}' not found."); continue
                base_slug = slugify(name)
                db.session.add(Program(
                    school_id=school.id,
                    name=name, level=level,
                    field_of_study=row.get("field_of_study", "").strip() or None,
                    study_mode=row.get("study_mode", "full-time").strip(),
                    duration_months=int(row["duration_months"]) if row.get("duration_months", "").strip() else None,
                    currency=row.get("currency", "GBP").strip(),
                    tuition_fee=float(row["tuition_fee"]) if row.get("tuition_fee", "").strip() else None,
                    application_fee=float(row["application_fee"]) if row.get("application_fee", "").strip() else None,
                    ielts_requirement=float(row["ielts_requirement"]) if row.get("ielts_requirement", "").strip() else None,
                    toefl_requirement=int(row["toefl_requirement"]) if row.get("toefl_requirement", "").strip() else None,
                    gpa_requirement=float(row["gpa_requirement"]) if row.get("gpa_requirement", "").strip() else None,
                    processing_weeks=int(row["processing_weeks"]) if row.get("processing_weeks", "").strip() else None,
                    status=row.get("status", "draft").strip(),
                    created_by=current_user.id,
                )); created += 1
            except Exception as e:
                errors.append(f"Row {i}: {e}")
        db.session.commit()

    elif entity == "campuses":
        from app.models.geography import Campus
        for i, row in enumerate(rows, 2):
            try:
                school_name = row.get("school_name", "").strip()
                campus_name = row.get("campus_name", "").strip()
                if not school_name or not campus_name: skipped += 1; continue
                school = School.query.filter(School.name.ilike(school_name)).first()
                if not school:
                    errors.append(f"Row {i}: School '{school_name}' not found."); continue
                city_name = row.get("city_name", "").strip()
                iso       = row.get("country_iso_code", "").strip().upper()
                city      = None
                if city_name and iso:
                    country = Country.query.filter_by(iso_code=iso).first()
                    if country:
                        city = City.query.filter_by(name=city_name, country_id=country.id).first()
                db.session.add(Campus(
                    school_id=school.id,
                    name=campus_name,
                    city_id=city.id if city else None,
                    address=row.get("address", "").strip() or None,
                    postal_code=row.get("postal_code", "").strip() or None,
                    phone=row.get("phone", "").strip() or None,
                    email=row.get("email", "").strip() or None,
                    is_main=row.get("is_main", "false").strip().lower() in ("true","1","yes"),
                )); created += 1
            except Exception as e:
                errors.append(f"Row {i}: {e}")
        db.session.commit()

    else:
        flash(f"Unknown entity type: {entity}", "error")
        return redirect(url_for("data_entry.csv_import_page"))

    msg = f"Import complete: {created} created, {skipped} skipped (already exist)."
    if errors:
        msg += f" {len(errors)} error(s): " + "; ".join(errors[:5])
        flash(msg, "warning")
    else:
        flash(msg, "success")

    return redirect(url_for("data_entry.csv_import_page"))
