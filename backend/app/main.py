from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone

from app.core.config import settings
from app.db.database import SessionLocal
from app.db.init_db import create_tables, seed_default_users

from app.api.routes import (
    auth, dashboard, students, courses, enrollments,
    attendance, assessments, lms, risk, support_cases,
    interventions, outcomes, data_quality, reports, admin,
)

app = FastAPI(
    title="Student Risk Intelligence Platform API",
    description=(
        "AI-powered Student Risk Intelligence & Intervention Management System. "
        "Three-tier architecture: React frontend → FastAPI backend → PostgreSQL."
    ),
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event() -> None:
    """Create DB tables and seed default users on startup."""
    create_tables()
    db = SessionLocal()
    try:
        seed_default_users(db)
    finally:
        db.close()


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

