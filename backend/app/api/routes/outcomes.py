from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.database import get_db
from app.api.dependencies.auth import get_current_user
from app.models.outcome import Outcome

router = APIRouter(prefix="/outcomes", tags=["Outcomes"])


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

