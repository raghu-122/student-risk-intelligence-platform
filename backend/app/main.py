from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from app.core.config import settings
from app.db.init_db import create_tables, seed_default_users

from app.api.routes import (
    auth, dashboard, students, courses, enrollments,
    attendance, assessments, lms, risk, support_cases,
    interventions, outcomes, data_quality, reports, admin,
    analytics, health,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """ASGI lifespan: create tables, seed default users, and populate seed data if empty.
    Skips seeding in test environments to keep test suite fast.
    """
    import logging
    import app.db.database as _db
    _log = logging.getLogger(__name__)
    create_tables()
    _log.info(f"[STARTUP] Environment: {settings.ENVIRONMENT}")
    if settings.ENVIRONMENT != "test":
        db = _db.SessionLocal()
        try:
            seed_default_users(db)
            from app.models.student import Student
            student_count = db.query(Student).count()
            _log.info(f"[STARTUP] Student count in DB: {student_count}")
            if student_count == 0:
                _log.info("[STARTUP] No students found — running database seeder...")
                from app.db.seeder import seed_database
                counts = seed_database(engine=_db.engine)
                _log.info(f"[STARTUP] Seeding complete: {counts}")
            else:
                _log.info(f"[STARTUP] Database already seeded with {student_count} students — skipping.")
        except Exception as e:
            _log.warning(f"[STARTUP] Data check/seed notice: {e}", exc_info=True)
        finally:
            db.close()
    yield  # app runs here


app = FastAPI(
    title="Student Risk Intelligence Platform API",
    description=(
        "Student Risk Intelligence & Intervention Management System. "
        "Three-tier architecture: React frontend → FastAPI backend → PostgreSQL/SQLite."
    ),
    version="1.0.1",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"])
def health_check():
    """Health-check endpoint used by Docker and monitoring tools."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.1",
    }


# ── API routers ──────────────────────────────────────────────────────────────
PREFIX = "/api"

app.include_router(auth.router, prefix=PREFIX)
app.include_router(dashboard.router, prefix=PREFIX)
app.include_router(students.router, prefix=PREFIX)
app.include_router(courses.router, prefix=PREFIX)
app.include_router(enrollments.router, prefix=PREFIX)
app.include_router(attendance.router, prefix=PREFIX)
app.include_router(assessments.router, prefix=PREFIX)
app.include_router(lms.router, prefix=PREFIX)
app.include_router(risk.router, prefix=PREFIX)
app.include_router(support_cases.router, prefix=PREFIX)
app.include_router(interventions.router, prefix=PREFIX)
app.include_router(outcomes.router, prefix=PREFIX)
app.include_router(data_quality.router, prefix=PREFIX)
app.include_router(reports.router, prefix=PREFIX)
app.include_router(admin.router, prefix=PREFIX)
app.include_router(analytics.router, prefix=PREFIX)
app.include_router(health.router, prefix=PREFIX)

