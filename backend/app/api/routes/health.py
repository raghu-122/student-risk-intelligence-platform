"""
Health check routes — system and database liveness.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.database import get_db
from datetime import datetime, timezone

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
def health():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat(), "version": "1.0.0"}


@router.get("/database")
def database_health(db: Session = Depends(get_db)):
    """Actually check the database connection and return table row counts."""
    try:
        db.execute(text("SELECT 1"))
        tables = {}
        for table in ["students", "courses", "enrollments", "attendance_events",
                      "assessments", "assessment_results", "lms_activities",
                      "support_cases", "interventions", "outcomes", "risk_assessments"]:
            try:
                result = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                tables[table] = result
            except Exception:
                tables[table] = "error"
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "table_counts": tables,
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

