from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.database import get_db
from app.api.dependencies.auth import get_current_user
from app.models.assessment import Assessment
from app.models.assessment_result import AssessmentResult

router = APIRouter(prefix="/assessments", tags=["Assessments"])


@router.get("")
def list_assessments(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    course_id: Optional[str] = None, assessment_type: Optional[str] = None,
    db: Session = Depends(get_db), _=Depends(get_current_user),
):
    q = db.query(Assessment)
    if course_id:
        q = q.filter(Assessment.course_id == course_id)
    if assessment_type:
        q = q.filter(Assessment.assessment_type == assessment_type)
    total = q.count()
    items = q.order_by(Assessment.assessment_date).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "page": page, "page_size": page_size,
            "items": [{"assessment_id": a.assessment_id, "course_id": a.course_id,
                        "assessment_name": a.assessment_name, "assessment_type": a.assessment_type,
                        "maximum_marks": a.maximum_marks, "weightage": a.weightage,
                        "assessment_date": a.assessment_date} for a in items]}


@router.get("/results")
def list_results(
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    enrollment_id: Optional[str] = None, assessment_id: Optional[str] = None,
    db: Session = Depends(get_db), _=Depends(get_current_user),
):
    q = db.query(AssessmentResult)
    if enrollment_id:
        q = q.filter(AssessmentResult.enrollment_id == enrollment_id)
    if assessment_id:
        q = q.filter(AssessmentResult.assessment_id == assessment_id)
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "page": page, "page_size": page_size,
            "items": [{"result_id": r.result_id, "assessment_id": r.assessment_id,
                        "enrollment_id": r.enrollment_id, "marks_obtained": r.marks_obtained,
                        "percentage": r.percentage, "submission_status": r.submission_status} for r in items]}

