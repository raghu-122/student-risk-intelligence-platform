from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timezone
from pydantic import BaseModel
from app.db.database import get_db
from app.api.dependencies.auth import get_current_user
from app.models.support_case import SupportCase
from app.models.support_case_event import SupportCaseEvent
import uuid

router = APIRouter(prefix="/support-cases", tags=["Support Cases"])

VALID_TRANSITIONS = {
    "OPEN": ["ASSIGNED"],
    "ASSIGNED": ["IN_PROGRESS", "OPEN"],
    "IN_PROGRESS": ["RESOLVED", "ASSIGNED"],
    "RESOLVED": ["CLOSED", "IN_PROGRESS"],
    "CLOSED": ["IN_PROGRESS"],  # allow reopening
}


class CaseCreate(BaseModel):
    case_id: Optional[str] = None
    student_id: str
    enrollment_id: Optional[str] = None
    case_type: str
    description: str
    priority: str = "MEDIUM"
    assigned_staff_id: Optional[str] = None


class StatusTransition(BaseModel):
    to_status: str
    notes: Optional[str] = None
    performed_by: Optional[str] = None


@router.get("")
def list_cases(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    case_status: Optional[str] = None, student_id: Optional[str] = None,
    priority: Optional[str] = None,
    db: Session = Depends(get_db), _=Depends(get_current_user),
):
    q = db.query(SupportCase)
    if case_status:
        q = q.filter(SupportCase.case_status == case_status)
    if student_id:
        q = q.filter(SupportCase.student_id == student_id)
    if priority:
        q = q.filter(SupportCase.priority == priority)
    total = q.count()
    items = q.order_by(SupportCase.opened_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "page": page, "page_size": page_size,
            "items": [{"case_id": c.case_id, "student_id": c.student_id,
                        "case_type": c.case_type, "priority": c.priority,
                        "case_status": c.case_status, "opened_at": c.opened_at,
                        "assigned_staff_id": c.assigned_staff_id} for c in items]}


@router.get("/{case_id}")
def get_case(case_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    c = db.query(SupportCase).filter(SupportCase.case_id == case_id).first()
    if not c:
        raise HTTPException(404, f"Case {case_id} not found")
    events = db.query(SupportCaseEvent).filter(SupportCaseEvent.case_id == case_id).order_by(SupportCaseEvent.event_timestamp).all()
    return {
        "case_id": c.case_id, "student_id": c.student_id, "enrollment_id": c.enrollment_id,
        "case_type": c.case_type, "description": c.description, "priority": c.priority,
        "assigned_staff_id": c.assigned_staff_id, "case_status": c.case_status,
        "opened_at": c.opened_at, "closed_at": c.closed_at, "resolution_notes": c.resolution_notes,
        "events": [{"event_id": e.event_id, "event_type": e.event_type, "from_status": e.from_status,
                     "to_status": e.to_status, "performed_by": e.performed_by,
                     "notes": e.notes, "timestamp": e.event_timestamp} for e in events],
    }


@router.post("", status_code=201)
def create_case(payload: CaseCreate, db: Session = Depends(get_db), cu=Depends(get_current_user)):
    if not payload.case_id:
        # auto-generate
        count = db.query(SupportCase).count() + 1
        case_id = f"CASE-2026-{count:06d}"
    else:
        case_id = payload.case_id
    c = SupportCase(
        case_id=case_id, student_id=payload.student_id, enrollment_id=payload.enrollment_id,
        case_type=payload.case_type, description=payload.description, priority=payload.priority,
        assigned_staff_id=payload.assigned_staff_id,
        case_status="ASSIGNED" if payload.assigned_staff_id else "OPEN",
    )
    db.add(c)
    evt = SupportCaseEvent(
        event_id=f"SCE-{uuid.uuid4().hex[:12].upper()}",
        case_id=case_id, event_type="CREATED", to_status=c.case_status,
        performed_by=cu.username,
    )
    db.add(evt)
    db.commit(); db.refresh(c)
    return {"case_id": c.case_id, "case_status": c.case_status}


@router.post("/{case_id}/transition")
def transition_case(case_id: str, payload: StatusTransition, db: Session = Depends(get_db), cu=Depends(get_current_user)):
    c = db.query(SupportCase).filter(SupportCase.case_id == case_id).first()
    if not c:
        raise HTTPException(404, f"Case {case_id} not found")
    allowed = VALID_TRANSITIONS.get(c.case_status, [])
    if payload.to_status not in allowed:
        raise HTTPException(400, f"Cannot transition from {c.case_status} to {payload.to_status}. Allowed: {allowed}")
    old_status = c.case_status
    c.case_status = payload.to_status
    if payload.to_status in ("RESOLVED", "CLOSED"):
        c.closed_at = datetime.now(timezone.utc)
    if payload.notes:
        c.resolution_notes = payload.notes
    evt = SupportCaseEvent(
        event_id=f"SCE-{uuid.uuid4().hex[:12].upper()}",
        case_id=case_id, event_type="STATUS_CHANGE",
        from_status=old_status, to_status=payload.to_status,
        performed_by=payload.performed_by or cu.username, notes=payload.notes,
    )
    db.add(evt); db.commit()
    return {"case_id": case_id, "from_status": old_status, "to_status": payload.to_status}

