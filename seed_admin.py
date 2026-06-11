import sys
from app import create_app
from app.extensions import db
from app.models.user import Role, User

def seed_admin():
    app = create_app('development')
    with app.app_context():
        # Define roles
        roles = [
            {"name": "Super Admin", "slug": "super_admin", "description": "Full system access"},
            {"name": "Staff", "slug": "staff", "description": "Internal application processing staff"},
            {"name": "Advisor", "slug": "advisor", "description": "Student counselor and advisor"},
            {"name": "Data Entry", "slug": "data_entry", "description": "Catalog and data management"},
            {"name": "Agency Owner", "slug": "agency_owner", "description": "Owner of a partner agency"},
            {"name": "Agency Agent", "slug": "agency_agent", "description": "Agent working for a partner agency"},
            {"name": "Student", "slug": "student", "description": "Standard student applicant"},
        ]
        
        print("Seeding roles...")
        for role_data in roles:
            role = Role.query.filter_by(slug=role_data['slug']).first()
            if not role:
                role = Role(**role_data)
                db.session.add(role)
        
        db.session.commit()
        print("Roles seeded.")

        # Create Super Admin
        admin_email = "admin@skolaz.com"
        admin = User.query.filter_by(email=admin_email).first()
        
        if not admin:
            print("Creating super admin user...")
            admin_role = Role.query.filter_by(slug="super_admin").first()
            admin = User(
                first_name="Super",
                last_name="Admin",
                email=admin_email,
                role_id=admin_role.id,
                status="active"
            )
            admin.set_password("Admin123!") # Strong default password
            db.session.add(admin)
            db.session.commit()
            print(f"Super admin created: {admin_email} / Admin123!")
        else:
            print("Super admin already exists.")

if __name__ == "__main__":
    seed_admin()
