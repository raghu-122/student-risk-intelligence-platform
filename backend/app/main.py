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
    import app.db.database as _db
    create_tables()
    if settings.ENVIRONMENT != "test":
        db = _db.SessionLocal()
        try:
            seed_default_users(db)
            from app.models.student import Student
            if db.query(Student).count() == 0:
                from app.db.seeder import seed_database
                seed_database(engine=_db.engine)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Startup data check/seed notice: {e}")
        finally:
            db.close()
    yield  # app runs here


app = FastAPI(
    title="Student Risk Intelligence Platform API",
    description=(
        "Student Risk Intelligence & Intervention Management System. "
        "Three-tier architecture: React frontend → FastAPI backend → PostgreSQL/SQLite."
    ),
    version="1.0.0",
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
        "version": "1.0.0",
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

