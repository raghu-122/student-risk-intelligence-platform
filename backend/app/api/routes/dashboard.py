from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.api.dependencies.auth import get_current_user
from app.models.intervention import Intervention
from app.models.risk_assessment import RiskAssessment
from app.models.student import Student
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


@router.get("/at-risk-students")
def at_risk_students(
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    latest = (
        db.query(
            RiskAssessment.risk_id.label("risk_id"),
            func.row_number().over(
                partition_by=RiskAssessment.student_id,
                order_by=(
                    RiskAssessment.assessment_timestamp.desc(),
                    RiskAssessment.cutoff_date.desc(),
                    RiskAssessment.risk_id.desc(),
                ),
            ).label("position"),
        )
        .filter(
            RiskAssessment.is_anomaly.is_(False),
            RiskAssessment.risk_score.isnot(None),
        )
        .subquery()
    )
    rows = (
        db.query(RiskAssessment, Student)
        .join(
            latest,
            RiskAssessment.risk_id == latest.c.risk_id,
        )
        .join(Student, Student.student_id == RiskAssessment.student_id)
        .filter(
            latest.c.position == 1,
            RiskAssessment.risk_category.in_(("CRITICAL", "HIGH")),
        )
        .order_by(RiskAssessment.risk_score.desc(), Student.student_id)
        .limit(limit)
        .all()
    )
    return [
        {
            "student_id": student.student_id,
            "full_name": f"{student.first_name} {student.last_name}",
            "department": student.department,
            "risk_score": risk.risk_score,
            "risk_category": risk.risk_category,
        }
        for risk, student in rows
    ]


@router.get("/recent-interventions")
def recent_interventions(
    limit: int = Query(5, ge=1, le=100),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    rows = (
        db.query(Intervention)
        .order_by(Intervention.trigger_date.desc(), Intervention.intervention_id)
        .limit(limit)
        .all()
    )
    return [
        {
            "intervention_id": intervention.intervention_id,
            "student_id": intervention.student_id,
            "intervention_type": intervention.intervention_type,
            "intervention_status": intervention.intervention_status,
            "trigger_date": intervention.trigger_date,
        }
        for intervention in rows
    ]
