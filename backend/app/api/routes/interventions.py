from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Literal, Optional
from datetime import date
from pydantic import BaseModel
from app.db.database import get_db
from app.api.dependencies.auth import get_current_user
from app.models.intervention import Intervention
from app.models.intervention_event import InterventionEvent
from app.models.student import Student
from app.models.enrollment import Enrollment
from app.models.support_case import SupportCase
from app.models.risk_assessment import RiskAssessment
from app.models.staff import Staff
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
    intervention_type: Literal[
        "ATTENDANCE_COUNSELLING", "ACADEMIC_TUTORING", "INSTRUCTOR_MEETING",
        "ENGAGEMENT_SUPPORT", "ADVISOR_REVIEW", "WELFARE_ASSESSMENT", "PERSONALIZED_PLAN",
    ]
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
    if payload.due_date and payload.due_date < (payload.start_date or payload.trigger_date):
        raise HTTPException(400, "due_date cannot precede the intervention start date")
    student = db.query(Student).filter(Student.student_id == payload.student_id).first()
    if not student:
        raise HTTPException(404, f"Student {payload.student_id} not found")
    if payload.enrollment_id:
        enrollment = db.query(Enrollment).filter(
            Enrollment.enrollment_id == payload.enrollment_id
        ).first()
        if not enrollment:
            raise HTTPException(404, f"Enrollment {payload.enrollment_id} not found")
        if enrollment.student_id != student.student_id:
            raise HTTPException(422, "Enrollment does not belong to the supplied student")
    if payload.case_id:
        case = db.query(SupportCase).filter(SupportCase.case_id == payload.case_id).first()
        if not case:
            raise HTTPException(404, f"Support case {payload.case_id} not found")
        if case.student_id != student.student_id:
            raise HTTPException(422, "Support case does not belong to the supplied student")
    if payload.risk_assessment_id:
        risk = db.query(RiskAssessment).filter(
            RiskAssessment.risk_id == payload.risk_assessment_id
        ).first()
        if not risk:
            raise HTTPException(404, f"Risk assessment {payload.risk_assessment_id} not found")
        if risk.student_id != student.student_id:
            raise HTTPException(422, "Risk assessment does not belong to the supplied student")
        if payload.enrollment_id and risk.enrollment_id != payload.enrollment_id:
            raise HTTPException(422, "Risk assessment does not belong to the supplied enrollment")
    if payload.assigned_staff_id and not db.query(Staff).filter(
        Staff.staff_id == payload.assigned_staff_id
    ).first():
        raise HTTPException(404, f"Staff member {payload.assigned_staff_id} not found")
    if not payload.intervention_id:
        count = db.query(Intervention).count() + 1
        int_id = f"INT-2026-{count:06d}"
    else:
        int_id = payload.intervention_id
        if db.query(Intervention).filter(Intervention.intervention_id == int_id).first():
            raise HTTPException(409, f"Intervention {int_id} already exists")
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
    if payload.to_status == "COMPLETED":
        completion_date = payload.completion_date or date.today()
        start_date = i.start_date or i.trigger_date
        if completion_date < start_date:
            raise HTTPException(400, "completion_date cannot precede the intervention start date")
        i.start_date = start_date
        i.completion_date = completion_date
    elif payload.completion_date:
        raise HTTPException(422, "completion_date is only valid when completing an intervention")
    elif payload.to_status == "IN_PROGRESS" and not i.start_date:
        i.start_date = max(date.today(), i.trigger_date)
    i.intervention_status = payload.to_status
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
