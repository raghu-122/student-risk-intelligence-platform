from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date
from app.db.database import get_db
from app.api.dependencies.auth import get_current_user
from app.models.attendance import AttendanceEvent
from app.models.enrollment import Enrollment
from app.core.constants import AttendanceStatus

router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.get("")
def list_attendance(
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    enrollment_id: Optional[str] = None, date_from: Optional[date] = None,
    date_to: Optional[date] = None, status: Optional[str] = None,
    db: Session = Depends(get_db), _=Depends(get_current_user),
):
    q = db.query(AttendanceEvent)
    if enrollment_id:
        q = q.filter(AttendanceEvent.enrollment_id == enrollment_id)
    if date_from:
        q = q.filter(AttendanceEvent.attendance_date >= date_from)
    if date_to:
        q = q.filter(AttendanceEvent.attendance_date <= date_to)
    if status:
        q = q.filter(AttendanceEvent.attendance_status == status)
    total = q.count()
    items = q.order_by(AttendanceEvent.attendance_date).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "page": page, "page_size": page_size,
            "items": [{"attendance_id": a.attendance_id, "enrollment_id": a.enrollment_id,
                        "attendance_date": a.attendance_date, "attendance_status": a.attendance_status,
                        "session_number": a.session_number} for a in items]}


@router.get("/summary/{enrollment_id}")
def attendance_summary(enrollment_id: str, cutoff: Optional[date] = None, db: Session = Depends(get_db), _=Depends(get_current_user)):
    """Return computed attendance rate for an enrollment, correctly excluding approved absences."""
    q = db.query(AttendanceEvent).filter(AttendanceEvent.enrollment_id == enrollment_id)
    if cutoff:
        q = q.filter(AttendanceEvent.attendance_date <= cutoff)
    evts = q.all()
    total = len(evts)
    if total == 0:
        return {"enrollment_id": enrollment_id, "total_sessions": 0, "attendance_rate": None}
    approved = sum(1 for e in evts if e.attendance_status == AttendanceStatus.APPROVED_ABSENCE)
    effective = total - approved
    attended = sum(1 for e in evts if e.attendance_status in (AttendanceStatus.PRESENT, AttendanceStatus.LATE))
    rate = round(attended / effective, 4) if effective > 0 else None
    return {
        "enrollment_id": enrollment_id, "total_sessions": total,
        "effective_denominator": effective, "approved_absences": approved,
        "attended": attended, "attendance_rate": rate,
        "note": "approved_absences excluded from denominator per business rule"
    }

