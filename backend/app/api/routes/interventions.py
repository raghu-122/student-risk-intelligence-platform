from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date
from pydantic import BaseModel
from app.db.database import get_db
from app.api.dependencies.auth import get_current_user
from app.models.intervention import Intervention
from app.models.intervention_event import InterventionEvent
import uuid

router = APIRouter(prefix="/interventions", tags=["Interventions"])

VALID_TRANSITIONS = {
    "RECOMMENDED": ["APPROVED", "REJECTED"],
    "APPROVED": ["ASSIGNED", "CANCELLED"],
    "ASSIGNED": ["IN_PROGRESS", "CANCELLED"],
    "IN_PROGRESS": ["COMPLETED", "CANCELLED"],
    "COMPLETED": [],
    "CANCELLED": [],
    "REJECTED": [],
}


class InterventionCreate(BaseModel):
    intervention_id: Optional[str] = None
    student_id: str
    enrollment_id: Optional[str] = None
    case_id: Optional[str] = None
    risk_assessment_id: Optional[str] = None
    intervention_type: str
    trigger_date: date
    assigned_staff_id: Optional[str] = None
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    expected_outcome: Optional[str] = None


class StatusUpdate(BaseModel):
    to_status: str
    notes: Optional[str] = None
    completion_date: Optional[date] = None


@router.get("")
def list_interventions(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    student_id: Optional[str] = None, intervention_status: Optional[str] = None,
    intervention_type: Optional[str] = None,
    db: Session = Depends(get_db), _=Depends(get_current_user),
):
    q = db.query(Intervention)
    if student_id:
        q = q.filter(Intervention.student_id == student_id)
    if intervention_status:
        q = q.filter(Intervention.intervention_status == intervention_status)
    if intervention_type:
        q = q.filter(Intervention.intervention_type == intervention_type)
    total = q.count()
    items = q.order_by(Intervention.trigger_date.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "page": page, "page_size": page_size,
            "items": [{"intervention_id": i.intervention_id, "student_id": i.student_id,
                        "intervention_type": i.intervention_type, "intervention_status": i.intervention_status,
                        "trigger_date": i.trigger_date, "due_date": i.due_date,
                        "assigned_staff_id": i.assigned_staff_id} for i in items]}


@router.get("/{intervention_id}")
def get_intervention(intervention_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    i = db.query(Intervention).filter(Intervention.intervention_id == intervention_id).first()
    if not i:
        raise HTTPException(404, f"Intervention {intervention_id} not found")
    events = db.query(InterventionEvent).filter(InterventionEvent.intervention_id == intervention_id).all()
    return {
        "intervention_id": i.intervention_id, "student_id": i.student_id,
        "enrollment_id": i.enrollment_id, "case_id": i.case_id,
        "risk_assessment_id": i.risk_assessment_id, "intervention_type": i.intervention_type,
        "trigger_date": i.trigger_date, "start_date": i.start_date, "due_date": i.due_date,
        "completion_date": i.completion_date, "intervention_status": i.intervention_status,
        "expected_outcome": i.expected_outcome, "actual_outcome": i.actual_outcome,
        "events": [{"event_id": e.event_id, "event_type": e.event_type,
                     "from_status": e.from_status, "to_status": e.to_status,
                     "notes": e.notes, "timestamp": e.event_timestamp} for e in events],
    }


@router.post("", status_code=201)
def create_intervention(payload: InterventionCreate, db: Session = Depends(get_db), cu=Depends(get_current_user)):
    if payload.start_date and payload.start_date < payload.trigger_date:
        raise HTTPException(400, "start_date cannot precede trigger_date — chronological violation")
    if not payload.intervention_id:
        count = db.query(Intervention).count() + 1
        int_id = f"INT-2026-{count:06d}"
    else:
        int_id = payload.intervention_id
    i = Intervention(
        intervention_id=int_id, **{k: v for k, v in payload.model_dump().items() if k != "intervention_id"},
        intervention_status="RECOMMENDED",
    )
    db.add(i)
    evt = InterventionEvent(
        event_id=f"IE-{uuid.uuid4().hex[:12].upper()}",
        intervention_id=int_id, event_type="CREATED", to_status="RECOMMENDED",
        performed_by=cu.username,
    )
    db.add(evt); db.commit(); db.refresh(i)
    return {"intervention_id": int_id, "intervention_status": i.intervention_status}


@router.post("/{intervention_id}/transition")
def transition_intervention(intervention_id: str, payload: StatusUpdate, db: Session = Depends(get_db), cu=Depends(get_current_user)):
    i = db.query(Intervention).filter(Intervention.intervention_id == intervention_id).first()
    if not i:
        raise HTTPException(404, f"Intervention {intervention_id} not found")
    allowed = VALID_TRANSITIONS.get(i.intervention_status, [])
    if payload.to_status not in allowed:
        raise HTTPException(400, f"Cannot transition from {i.intervention_status} to {payload.to_status}. Allowed: {allowed}")
    old = i.intervention_status
    i.intervention_status = payload.to_status
    if payload.completion_date:
        i.completion_date = payload.completion_date
    if payload.notes:
        i.actual_outcome = payload.notes
    evt = InterventionEvent(
        event_id=f"IE-{uuid.uuid4().hex[:12].upper()}",
        intervention_id=intervention_id, event_type="STATUS_CHANGE",
        from_status=old, to_status=payload.to_status,
        performed_by=cu.username, notes=payload.notes,
    )
    db.add(evt); db.commit()
    return {"intervention_id": intervention_id, "from_status": old, "to_status": payload.to_status}

