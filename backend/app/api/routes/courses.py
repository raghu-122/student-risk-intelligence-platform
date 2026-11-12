from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from app.db.database import get_db
from app.api.dependencies.auth import get_current_user
from app.models.course import Course
from app.models.enrollment import Enrollment

router = APIRouter(prefix="/courses", tags=["Courses"])


@router.get("")
def list_courses(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    department: Optional[str] = None, search: Optional[str] = None,
    db: Session = Depends(get_db), _=Depends(get_current_user),
):
    q = db.query(Course)
    if department:
        q = q.filter(Course.department == department)
    if search:
        like = f"%{search}%"
        q = q.filter(or_(Course.course_name.ilike(like), Course.course_code.ilike(like)))
    total = q.count()
    items = q.order_by(Course.course_id).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "page": page, "page_size": page_size,
            "pages": (total + page_size - 1) // page_size,
            "items": [{"course_id": c.course_id, "course_name": c.course_name,
                        "course_code": c.course_code, "department": c.department,
                        "credits": c.credits, "semester": c.semester,
                        "instructor_id": c.instructor_id} for c in items]}


@router.get("/{course_id}")
def get_course(course_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    c = db.query(Course).filter(Course.course_id == course_id).first()
    if not c:
        raise HTTPException(404, f"Course {course_id} not found")
    enr_count = db.query(Enrollment).filter(Enrollment.course_id == course_id).count()
    return {"course_id": c.course_id, "course_name": c.course_name, "course_code": c.course_code,
            "department": c.department, "credits": c.credits, "semester": c.semester,
            "instructor_id": c.instructor_id, "enrollment_count": enr_count}

