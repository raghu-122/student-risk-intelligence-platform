from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date
from app.db.database import get_db
from app.api.dependencies.auth import get_current_user
from app.models.lms_activity import LMSActivity

router = APIRouter(prefix="/lms", tags=["LMS Activity"])


@router.get("")
def list_lms_activity(
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    enrollment_id: Optional[str] = None, activity_type: Optional[str] = None,
    date_from: Optional[date] = None, date_to: Optional[date] = None,
    db: Session = Depends(get_db), _=Depends(get_current_user),
):
    q = db.query(LMSActivity)
    if enrollment_id:
        q = q.filter(LMSActivity.enrollment_id == enrollment_id)
    if activity_type:
        q = q.filter(LMSActivity.activity_type == activity_type)
    if date_from:
        from datetime import datetime
        q = q.filter(LMSActivity.activity_timestamp >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        from datetime import datetime
        q = q.filter(LMSActivity.activity_timestamp <= datetime.combine(date_to, datetime.max.time()))
    total = q.count()
    items = q.order_by(LMSActivity.activity_timestamp.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "page": page, "page_size": page_size,
            "items": [{"activity_id": a.activity_id, "enrollment_id": a.enrollment_id,
                        "activity_type": a.activity_type, "activity_timestamp": a.activity_timestamp,
                        "duration_minutes": a.duration_minutes} for a in items]}


@router.get("/summary/{enrollment_id}")
def lms_summary(enrollment_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    acts = db.query(LMSActivity).filter(LMSActivity.enrollment_id == enrollment_id).all()
    by_type: dict = {}
    for a in acts:
        by_type[a.activity_type] = by_type.get(a.activity_type, 0) + 1
    return {
        "enrollment_id": enrollment_id, "total_activities": len(acts),
        "total_minutes": sum(a.duration_minutes or 0 for a in acts),
        "by_type": by_type,
    }

