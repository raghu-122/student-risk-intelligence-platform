from datetime import date
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from app.db.database import get_db
from app.api.dependencies.auth import get_current_user
from app.models.enrollment import Enrollment
from app.models.intervention import Intervention
from app.models.outcome import Outcome
from app.models.risk_assessment import RiskAssessment
from app.models.student import Student
from app.services.outcome_engine import evaluate_outcome

router = APIRouter(prefix="/outcomes", tags=["Outcomes"])


class OutcomeEvaluationRequest(BaseModel):
    student_id: str
    enrollment_id: str
    baseline_cutoff: date
    evaluation_period_start: date
    evaluation_period_end: date
    intervention_id: Optional[str] = None
    baseline_risk_score: Optional[float] = None


@router.post("/evaluate", status_code=201)
def create_outcome_evaluation(
    payload: OutcomeEvaluationRequest,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    if payload.evaluation_period_start <= payload.baseline_cutoff:
        raise HTTPException(422, "Evaluation period must start after the baseline cutoff")
    if payload.evaluation_period_end < payload.evaluation_period_start:
        raise HTTPException(422, "Evaluation period end must be on or after its start")

    student = db.query(Student).filter(Student.student_id == payload.student_id).first()
    enrollment = db.query(Enrollment).filter(Enrollment.enrollment_id == payload.enrollment_id).first()
    if not student or not enrollment:
        raise HTTPException(404, "Student or enrollment not found")
    if enrollment.student_id != student.student_id:
        raise HTTPException(422, "Enrollment does not belong to the supplied student")

    if payload.intervention_id:
        intervention = db.query(Intervention).filter(
            Intervention.intervention_id == payload.intervention_id
        ).first()
        if not intervention:
            raise HTTPException(404, "Intervention not found")
        if intervention.student_id != student.student_id:
            raise HTTPException(422, "Intervention does not belong to the supplied student")

    baseline_risk_score = payload.baseline_risk_score
    if baseline_risk_score is None:
        baseline = (
            db.query(RiskAssessment)
            .filter(
                RiskAssessment.student_id == student.student_id,
                RiskAssessment.enrollment_id == enrollment.enrollment_id,
                RiskAssessment.cutoff_date <= payload.baseline_cutoff,
                RiskAssessment.is_anomaly.is_(False),
            )
            .order_by(RiskAssessment.cutoff_date.desc(), RiskAssessment.assessment_timestamp.desc())
            .first()
        )
        baseline_risk_score = baseline.risk_score if baseline else None

    result = evaluate_outcome(
        db=db,
        student_id=student.student_id,
        enrollment_id=enrollment.enrollment_id,
        baseline_cutoff=payload.baseline_cutoff,
        eval_start=payload.evaluation_period_start,
        eval_end=payload.evaluation_period_end,
        baseline_risk_score=baseline_risk_score,
        intervention_id=payload.intervention_id,
    )

    existing = (
        db.query(Outcome)
        .filter(
            Outcome.enrollment_id == enrollment.enrollment_id,
            Outcome.intervention_id == payload.intervention_id,
            Outcome.evaluation_period_start == payload.evaluation_period_start,
            Outcome.evaluation_period_end == payload.evaluation_period_end,
        )
        .first()
    )
    if existing:
        for field, value in result.items():
            setattr(existing, field, value)
        outcome = existing
    else:
        outcome = Outcome(
            outcome_id=f"OUT-{uuid.uuid4().hex[:16].upper()}",
            **result,
        )
        db.add(outcome)
    db.commit()
    db.refresh(outcome)
    return {
        "outcome_id": outcome.outcome_id,
        "student_id": outcome.student_id,
        "enrollment_id": outcome.enrollment_id,
        "intervention_id": outcome.intervention_id,
        "outcome_label": outcome.outcome_label,
        "baseline_risk_score": outcome.baseline_risk_score,
        "future_risk_score": outcome.future_risk_score,
        "academic_performance_change": outcome.academic_performance_change,
        "attendance_change": outcome.attendance_change,
        "engagement_change": outcome.engagement_change,
        "evaluation_period_start": outcome.evaluation_period_start,
        "evaluation_period_end": outcome.evaluation_period_end,
        "evaluation_date": outcome.evaluation_date,
    }


@router.get("")
def list_outcomes(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    student_id: Optional[str] = None, outcome_label: Optional[str] = None,
    db: Session = Depends(get_db), _=Depends(get_current_user),
):
    q = db.query(Outcome)
    if student_id:
        q = q.filter(Outcome.student_id == student_id)
    if outcome_label:
        q = q.filter(Outcome.outcome_label == outcome_label)
    total = q.count()
    items = q.order_by(Outcome.evaluation_date.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "page": page, "page_size": page_size,
            "items": [{"outcome_id": o.outcome_id, "student_id": o.student_id,
                        "enrollment_id": o.enrollment_id, "intervention_id": o.intervention_id,
                        "outcome_label": o.outcome_label, "baseline_risk_score": o.baseline_risk_score,
                        "future_risk_score": o.future_risk_score,
                        "academic_performance_change": o.academic_performance_change,
                        "attendance_change": o.attendance_change,
                        "engagement_change": o.engagement_change,
                        "evaluation_period_start": o.evaluation_period_start,
                        "evaluation_period_end": o.evaluation_period_end} for o in items]}


@router.get("/summary")
def outcome_summary(db: Session = Depends(get_db), _=Depends(get_current_user)):
    from sqlalchemy import func
    rows = db.query(Outcome.outcome_label, func.count(Outcome.outcome_id)).group_by(Outcome.outcome_label).all()
    total = sum(c for _, c in rows)
    return {
        "total": total,
        "distribution": [{"label": lbl, "count": cnt, "pct": round(cnt / total * 100, 1) if total else 0}
                          for lbl, cnt in rows],
        "note": "Outcome labels reflect observed changes, not causal attribution to interventions",
    }
