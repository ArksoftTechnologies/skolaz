"""
Skolaz v2.0 — Public Blueprint
Landing website + school search + consultation booking
"""
from flask import Blueprint, render_template, request, jsonify
from app.models.institution import School, Program, Scholarship
from app.models.geography import Country, State, City
from app.extensions import db

public_bp = Blueprint("public", __name__)


@public_bp.get("/")
def home():
    """Public landing page with program search."""
    featured_schools   = School.query.filter_by(is_featured=True, status="active").limit(6).all()
    featured_countries = Country.query.filter_by(is_featured=True, status="active").limit(8).all()
    countries          = Country.query.filter_by(status="active").order_by(Country.name).all()

    # Stats for social proof
    stats = {
        "schools":   School.query.filter_by(status="active").count(),
        "programs":  Program.query.filter_by(status="active").count(),
        "countries": Country.query.filter_by(status="active").count(),
    }

    return render_template(
        "public/home.html",
        featured_schools=featured_schools,
        featured_countries=featured_countries,
        countries=countries,
        stats=stats,
    )


@public_bp.get("/destinations")
def destinations():
    countries = Country.query.filter_by(status="active").order_by(Country.name).all()
    return render_template("public/destinations.html", countries=countries)


@public_bp.get("/destinations/<iso_code>")
def destination_detail(iso_code):
    country = Country.query.filter_by(iso_code=iso_code.upper(), status="active").first_or_404()
    schools = School.query.filter_by(country_id=country.id, status="active").all()
    return render_template("public/destination_detail.html", country=country, schools=schools)


@public_bp.get("/schools")
def schools():
    page       = max(1, request.args.get("page", 1, type=int))
    country_id = request.args.get("country_id", type=int)
    state_id   = request.args.get("state_id", type=int)
    city_id    = request.args.get("city_id", type=int)
    q          = request.args.get("q", "")

    query = School.query.filter_by(status="active")
    if country_id:
        query = query.filter_by(country_id=country_id)
    if state_id:
        query = query.filter_by(state_id=state_id)
    if city_id:
        query = query.filter_by(city_id=city_id)
    if q:
        query = query.filter(School.name.ilike(f"%{q}%"))

    pagination = query.order_by(School.is_featured.desc(), School.ranking).paginate(
        page=page, per_page=12, error_out=False
    )
    countries = Country.query.filter_by(status="active").order_by(Country.name).all()

    if request.headers.get("HX-Request"):
        return render_template("public/_schools_grid.html", pagination=pagination, q=q)

    return render_template("public/schools.html",
                           pagination=pagination, q=q,
                           countries=countries,
                           country_id=country_id, state_id=state_id, city_id=city_id)


@public_bp.get("/schools/<int:school_id>")
def school_detail(school_id):
    school   = School.query.filter_by(id=school_id, status="active").first_or_404()
    programs = school.programs.filter_by(status="active").all()
    return render_template("public/school_detail.html", school=school, programs=programs)


@public_bp.get("/programs")
def programs():
    q          = request.args.get("q", "")
    level      = request.args.get("level", "")
    country_id = request.args.get("country_id", type=int)
    state_id   = request.args.get("state_id", type=int)
    city_id    = request.args.get("city_id", type=int)
    school_id  = request.args.get("school_id", type=int)
    min_fee    = request.args.get("min_fee", type=float)
    max_fee    = request.args.get("max_fee", type=float)
    page       = max(1, request.args.get("page", 1, type=int))

    query = Program.query.filter_by(status="active").join(Program.school).filter(
        School.status == "active"
    )

    if q:
        query = query.filter(
            db.or_(Program.name.ilike(f"%{q}%"), Program.field_of_study.ilike(f"%{q}%"))
        )
    if level:
        query = query.filter(Program.level == level)
    if country_id:
        query = query.filter(School.country_id == country_id)
    if state_id:
        query = query.filter(School.state_id == state_id)
    if city_id:
        query = query.filter(School.city_id == city_id)
    if school_id:
        query = query.filter(Program.school_id == school_id)
    if min_fee:
        query = query.filter(Program.tuition_fee >= min_fee)
    if max_fee:
        query = query.filter(Program.tuition_fee <= max_fee)

    pagination = query.order_by(Program.is_featured.desc()).paginate(
        page=page, per_page=15, error_out=False
    )

    countries = Country.query.filter_by(status="active").order_by(Country.name).all()
    schools   = School.query.filter_by(status="active").order_by(School.name).all()

    if request.headers.get("HX-Request"):
        return render_template("public/_programs_list.html", pagination=pagination)

    return render_template("public/programs.html",
                           pagination=pagination, q=q, level=level,
                           country_id=country_id, state_id=state_id,
                           city_id=city_id, school_id=school_id,
                           min_fee=min_fee, max_fee=max_fee,
                           countries=countries, schools=schools)


@public_bp.get("/scholarships")
def scholarships():
    items = Scholarship.query.filter_by(is_active=True).order_by(Scholarship.deadline).all()
    return render_template("public/scholarships.html", scholarships=items)


@public_bp.get("/consultation")
def consultation():
    return render_template("public/consultation.html")


@public_bp.get("/blog")
def blog():
    return render_template("public/blog.html")


@public_bp.get("/about")
def about():
    return render_template("public/about.html")


@public_bp.get("/contact")
def contact():
    return render_template("public/contact.html")


@public_bp.get("/privacy")
def privacy():
    return render_template("public/privacy.html")


@public_bp.get("/terms")
def terms():
    return render_template("public/terms.html")


# ── HTMX Search Autocomplete ─────────────────────────────────────────────────

@public_bp.get("/search")
def search():
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return "", 200

    schools_  = School.query.filter(
        School.name.ilike(f"%{q}%"), School.status == "active"
    ).limit(5).all()
    programs_ = Program.query.filter(
        Program.name.ilike(f"%{q}%"), Program.status == "active"
    ).limit(5).all()

    return render_template(
        "public/_search_results.html",
        schools=schools_, programs=programs_, q=q,
    )


# ── Cascade API for public filters ───────────────────────────────────────────

@public_bp.get("/api/states")
def api_states():
    country_id = request.args.get("country_id", type=int)
    states = State.query.filter_by(country_id=country_id).order_by(State.name).all() if country_id else []
    html = '<option value="">All States / Provinces</option>'
    for s in states:
        html += f'<option value="{s.id}">{s.name}</option>'
    return html, 200


@public_bp.get("/api/cities")
def api_cities():
    country_id = request.args.get("country_id", type=int)
    state_id   = request.args.get("state_id", type=int)
    query = City.query
    if state_id:
        query = query.filter_by(state_id=state_id)
    elif country_id:
        query = query.filter_by(country_id=country_id)
    cities = query.order_by(City.name).all()
    html = '<option value="">All Cities</option>'
    for c in cities:
        html += f'<option value="{c.id}">{c.name}</option>'
    return html, 200


@public_bp.get("/api/schools-in")
def api_schools_in():
    country_id = request.args.get("country_id", type=int)
    state_id   = request.args.get("state_id", type=int)
    city_id    = request.args.get("city_id", type=int)
    query = School.query.filter_by(status="active")
    if city_id:
        query = query.filter_by(city_id=city_id)
    elif state_id:
        query = query.filter_by(state_id=state_id)
    elif country_id:
        query = query.filter_by(country_id=country_id)
    schools = query.order_by(School.name).all()
    html = '<option value="">All Institutions</option>'
    for s in schools:
        html += f'<option value="{s.id}">{s.name}</option>'
    return html, 200
