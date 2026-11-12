from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.api.dependencies.auth import get_current_user
from app.services.analytics_engine import (
    get_dashboard_stats, get_risk_distribution,
    get_risk_by_department, get_outcome_distribution,
    get_intervention_outcomes,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats")
def dashboard_stats(db: Session = Depends(get_db), _=Depends(get_current_user)):
    """Return high-level KPI statistics for the dashboard."""
    return get_dashboard_stats(db)


@router.get("/risk-distribution")
def risk_distribution(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return get_risk_distribution(db)


@router.get("/risk-by-department")
def risk_by_department(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return get_risk_by_department(db)


@router.get("/outcome-distribution")
def outcome_distribution(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return get_outcome_distribution(db)


@router.get("/intervention-outcomes")
def intervention_outcomes(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return get_intervention_outcomes(db)

