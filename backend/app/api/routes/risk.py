from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date as date_type
from app.db.database import get_db
from app.api.dependencies.auth import get_current_user
from app.models.risk_assessment import RiskAssessment
from app.models.risk_factor import RiskFactor
from app.models.enrollment import Enrollment
from app.models.student import Student
from app.services.risk_engine import calculate_enrollment_risk
from app.services.intervention_engine import recommend_interventions
from app.core.constants import RISK_CUTOFF_DATE
import uuid
from datetime import date

router = APIRouter(prefix="/risk", tags=["Risk Intelligence"])


@router.get("")
def list_risk_assessments(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    risk_category: Optional[str] = None, student_id: Optional[str] = None,
    department: Optional[str] = None, is_anomaly: Optional[bool] = None,
    db: Session = Depends(get_db), _=Depends(get_current_user),
):
    q = db.query(RiskAssessment)
    if risk_category:
        q = q.filter(RiskAssessment.risk_category == risk_category)
    if student_id:
        q = q.filter(RiskAssessment.student_id == student_id)
    if is_anomaly is not None:
        q = q.filter(RiskAssessment.is_anomaly == is_anomaly)
    if department:
        q = q.join(Student, RiskAssessment.student_id == Student.student_id).filter(Student.department == department)
    total = q.count()
    items = q.order_by(RiskAssessment.assessment_timestamp.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "page": page, "page_size": page_size,
            "pages": (total + page_size - 1) // page_size,
            "items": [{"risk_id": r.risk_id, "student_id": r.student_id,
                        "enrollment_id": r.enrollment_id, "risk_score": r.risk_score,
                        "risk_category": r.risk_category, "cutoff_date": r.cutoff_date,
                        "data_completeness": r.data_completeness, "model_version": r.model_version,
                        "assessment_timestamp": r.assessment_timestamp,
                        "factor_scores": r.factor_scores, "reasons": r.reasons} for r in items]}


@router.get("/{risk_id}")
def get_risk_assessment(risk_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    r = db.query(RiskAssessment).filter(RiskAssessment.risk_id == risk_id).first()
    if not r:
        raise HTTPException(404, f"Risk assessment {risk_id} not found")
    factors = db.query(RiskFactor).filter(RiskFactor.risk_id == risk_id).all()
    return {
        "risk_id": r.risk_id, "student_id": r.student_id, "enrollment_id": r.enrollment_id,
        "risk_score": r.risk_score, "risk_category": r.risk_category, "cutoff_date": r.cutoff_date,
        "data_completeness": r.data_completeness, "model_version": r.model_version,
        "factor_scores": r.factor_scores, "factor_weights": r.factor_weights,
        "reasons": r.reasons, "assessment_timestamp": r.assessment_timestamp, "is_anomaly": r.is_anomaly,
        "factors": [{"factor_name": f.factor_name, "raw_value": f.raw_value,
                      "normalized_score": f.normalized_score, "weight": f.weight,
                      "contribution": f.contribution, "explanation": f.explanation} for f in factors],
    }


@router.post("/calculate")
def calculate_risk(
    student_id: str, enrollment_id: str,
    cutoff_date: Optional[date_type] = None,
    db: Session = Depends(get_db), _=Depends(get_current_user),
):
    """Calculate and persist a risk assessment for a student enrollment."""
    if not db.query(Student).filter(Student.student_id == student_id).first():
        raise HTTPException(404, f"Student {student_id} not found")
    if not db.query(Enrollment).filter(Enrollment.enrollment_id == enrollment_id).first():
        raise HTTPException(404, f"Enrollment {enrollment_id} not found")

    cutoff = cutoff_date or date.fromisoformat(RISK_CUTOFF_DATE)
    result = calculate_enrollment_risk(db, student_id, enrollment_id, cutoff)

    risk_id = f"RISK-{student_id}-{uuid.uuid4().hex[:8].upper()}"
    ra = RiskAssessment(
        risk_id=risk_id,
        student_id=result["student_id"],
        enrollment_id=result["enrollment_id"],
        cutoff_date=result["cutoff_date"],
        risk_score=result["risk_score"],
        risk_category=result["risk_category"],
        factor_scores=result["factor_scores"],
        factor_weights=result["factor_weights"],
        reasons=result["reasons"],
        data_completeness=result["data_completeness"],
        model_version=result["model_version"],
        is_anomaly=False,
    )
    db.add(ra)

    # Persist individual factor rows
    for fname, fdata in (result.get("factor_details") or {}).items():
        score = fdata.get("normalized_score")
        weight = result["factor_weights"].get(fname, 0)
        rf = RiskFactor(
            factor_id=f"{risk_id}-{fname}",
            risk_id=risk_id,
            factor_name=fname,
            raw_value=fdata.get("raw_value"),
            normalized_score=score,
            weight=weight,
            contribution=round(score * weight, 2) if score is not None else None,
            explanation=fdata.get("explanation"),
        )
        db.add(rf)

    db.commit()
    result["risk_id"] = risk_id
    return result


@router.get("/recommendations/{student_id}")
def get_recommendations(
    student_id: str, enrollment_id: Optional[str] = None,
    db: Session = Depends(get_db), _=Depends(get_current_user),
):
    """Return latest intervention recommendations for a student."""
    q = db.query(RiskAssessment).filter(
        RiskAssessment.student_id == student_id, RiskAssessment.is_anomaly == False
    )
    if enrollment_id:
        q = q.filter(RiskAssessment.enrollment_id == enrollment_id)
    latest = q.order_by(RiskAssessment.assessment_timestamp.desc()).first()
    if not latest:
        return {"student_id": student_id, "recommendations": [], "message": "No risk assessment found"}

    ra_dict = {
        "risk_id": latest.risk_id,
        "student_id": latest.student_id,
        "enrollment_id": latest.enrollment_id,
        "risk_score": latest.risk_score,
        "factor_scores": latest.factor_scores or {},
    }
    recs = recommend_interventions(ra_dict, trigger_date=date.today())
    return {"student_id": student_id, "risk_assessment_id": latest.risk_id,
            "risk_score": latest.risk_score, "risk_category": latest.risk_category,
            "recommendations": recs}

