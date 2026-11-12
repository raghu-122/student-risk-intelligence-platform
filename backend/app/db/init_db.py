"""Database initialization: create tables and seed default users."""
from sqlalchemy.orm import Session
from app.models import *  # noqa: F401,F403  — registers all ORM models with Base
from app.core.security import hash_password


def create_tables(bind=None) -> None:
    """Create all database tables if they don't exist."""
    import app.db.database as _db
    _db.Base.metadata.create_all(bind=bind or _db.engine)


def seed_default_users(db: Session) -> None:
    """Seed default platform administrator and demo accounts if not already present."""
    from app.models.staff import Staff
    from app.models.user import User

    if db.query(User).filter(User.username == "admin").first():
        return  # Already seeded

    # Platform admin staff record
    admin_staff = Staff(
        staff_id="STF-000001",
        first_name="Platform",
        last_name="Administrator",
        email="admin@yottaflex.edu",
        role="PLATFORM_ADMINISTRATOR",
        department="Administration",
    )
    db.add(admin_staff)

    admin_user = User(
        user_id="USR-000001",
        username="admin",
        email="admin@yottaflex.edu",
        hashed_password=hash_password("admin123"),
        role="PLATFORM_ADMINISTRATOR",
        staff_id="STF-000001",
    )
    db.add(admin_user)

    # Demo instructor
    instr_staff = Staff(
        staff_id="STF-000002",
        first_name="Demo",
        last_name="Instructor",
        email="instructor1@yottaflex.edu",
        role="INSTRUCTOR",
        department="Computer Science",
    )
    db.add(instr_staff)
    db.add(User(
        user_id="USR-000002",
        username="instructor1",
        email="instructor1@yottaflex.edu",
        hashed_password=hash_password("demo123"),
        role="INSTRUCTOR",
        staff_id="STF-000002",
    ))

    # Demo academic administrator
    adm_staff = Staff(
        staff_id="STF-000003",
        first_name="Demo",
        last_name="Advisor",
        email="advisor1@yottaflex.edu",
        role="ACADEMIC_ADMINISTRATOR",
        department="Administration",
    )
    db.add(adm_staff)
    db.add(User(
        user_id="USR-000003",
        username="advisor1",
        email="advisor1@yottaflex.edu",
        hashed_password=hash_password("demo123"),
        role="ACADEMIC_ADMINISTRATOR",
        staff_id="STF-000003",
    ))

    # Demo support staff
    sup_staff = Staff(
        staff_id="STF-000004",
        first_name="Demo",
        last_name="Support",
        email="support1@yottaflex.edu",
        role="SUPPORT_STAFF",
        department="Student Services",
    )
    db.add(sup_staff)
    db.add(User(
        user_id="USR-000004",
        username="support1",
        email="support1@yottaflex.edu",
        hashed_password=hash_password("demo123"),
        role="SUPPORT_STAFF",
        staff_id="STF-000004",
    ))

    db.commit()

