from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.database import get_db
from app.api.dependencies.auth import get_current_user
from app.models.enrollment import Enrollment
from app.models.student import Student
from app.models.course import Course

router = APIRouter(prefix="/enrollments", tags=["Enrollments"])


@router.get("")
def list_enrollments(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    student_id: Optional[str] = None, course_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db), _=Depends(get_current_user),
):
    q = db.query(Enrollment)
    if student_id:
        q = q.filter(Enrollment.student_id == student_id)
    if course_id:
        q = q.filter(Enrollment.course_id == course_id)
    if status:
        q = q.filter(Enrollment.enrollment_status == status)
    total = q.count()
    items = q.order_by(Enrollment.enrollment_id).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "page": page, "page_size": page_size,
            "pages": (total + page_size - 1) // page_size,
            "items": [{"enrollment_id": e.enrollment_id, "student_id": e.student_id,
                        "course_id": e.course_id, "enrollment_status": e.enrollment_status,
                        "final_grade": e.final_grade, "effective_from": e.effective_from,
                        "effective_to": e.effective_to} for e in items]}

