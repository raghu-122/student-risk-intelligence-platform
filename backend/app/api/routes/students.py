from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import List, Optional
from pydantic import BaseModel
from datetime import date
from app.db.database import get_db
from app.api.dependencies.auth import get_current_user
from app.models.student import Student
from app.models.enrollment import Enrollment
from app.models.support_case import SupportCase
from app.models.intervention import Intervention
from app.models.risk_assessment import RiskAssessment
from app.models.attendance import AttendanceEvent
from app.models.assessment_result import AssessmentResult
from app.models.assessment import Assessment
from app.models.lms_activity import LMSActivity

router = APIRouter(prefix="/students", tags=["Students"])


class StudentResponse(BaseModel):
    student_id: str
    first_name: str
    last_name: str
    email: str
    enrollment_date: date
    academic_year: str
    department: str
    program: str
    current_status: str
    model_config = {"from_attributes": True}


class StudentCreate(BaseModel):
    student_id: str
    first_name: str
    last_name: str
    email: str
    enrollment_date: date
    academic_year: str
    department: str
    program: str
    current_status: str = "ACTIVE"


@router.get("")
def list_students(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    department: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "student_id",
    sort_dir: str = "asc",
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    q = db.query(Student)
    if department:
        q = q.filter(Student.department == department)
    if status:
        q = q.filter(Student.current_status == status)
    if search:
        like = f"%{search}%"
        q = q.filter(or_(
            Student.first_name.ilike(like),
            Student.last_name.ilike(like),
            Student.student_id.ilike(like),
            Student.email.ilike(like),
        ))
    total = q.count()
    col = getattr(Student, sort_by, Student.student_id)
    q = q.order_by(col.desc() if sort_dir == "desc" else col.asc())
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total, "page": page, "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
        "items": [StudentResponse.model_validate(s) for s in items],
    }


@router.get("/{student_id}")
def get_student(student_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    s = db.query(Student).filter(Student.student_id == student_id).first()
    if not s:
        raise HTTPException(404, f"Student {student_id} not found")
    return StudentResponse.model_validate(s)


@router.get("/{student_id}/enrollments")
def student_enrollments(student_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    enrs = db.query(Enrollment).filter(Enrollment.student_id == student_id).all()
    return [{"enrollment_id": e.enrollment_id, "course_id": e.course_id,
              "status": e.enrollment_status, "final_grade": e.final_grade,
              "effective_from": e.effective_from, "effective_to": e.effective_to} for e in enrs]


@router.get("/{student_id}/risk-history")
def student_risk_history(student_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    risks = (db.query(RiskAssessment)
             .filter(RiskAssessment.student_id == student_id)
             .order_by(RiskAssessment.assessment_timestamp.desc()).all())
    return [{"risk_id": r.risk_id, "risk_score": r.risk_score, "risk_category": r.risk_category,
              "cutoff_date": r.cutoff_date, "data_completeness": r.data_completeness,
              "reasons": r.reasons, "factor_scores": r.factor_scores,
              "assessment_timestamp": r.assessment_timestamp} for r in risks]


@router.get("/{student_id}/support-cases")
def student_support_cases(student_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    cases = db.query(SupportCase).filter(SupportCase.student_id == student_id).all()
    return [{"case_id": c.case_id, "case_type": c.case_type, "priority": c.priority,
              "case_status": c.case_status, "opened_at": c.opened_at} for c in cases]


@router.get("/{student_id}/interventions")
def student_interventions(student_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    intv = db.query(Intervention).filter(Intervention.student_id == student_id).all()
    return [{"intervention_id": i.intervention_id, "intervention_type": i.intervention_type,
              "intervention_status": i.intervention_status, "trigger_date": i.trigger_date,
              "due_date": i.due_date} for i in intv]


@router.post("", status_code=201)
def create_student(payload: StudentCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if db.query(Student).filter(Student.student_id == payload.student_id).first():
        raise HTTPException(409, "Student ID already exists")
    s = Student(**payload.model_dump())
    db.add(s); db.commit(); db.refresh(s)
    return StudentResponse.model_validate(s)


@router.put("/{student_id}")
def update_student(student_id: str, payload: dict, db: Session = Depends(get_db), _=Depends(get_current_user)):
    s = db.query(Student).filter(Student.student_id == student_id).first()
    if not s:
        raise HTTPException(404, f"Student {student_id} not found")
    for k, v in payload.items():
        if hasattr(s, k) and k != "student_id":
            setattr(s, k, v)
    db.commit(); db.refresh(s)
    return StudentResponse.model_validate(s)


@router.get("/{student_id}/risk")
def student_latest_risk(student_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    """Return the latest risk assessment for a student."""
    s = db.query(Student).filter(Student.student_id == student_id).first()
    if not s:
        raise HTTPException(404, f"Student {student_id} not found")
    r = (db.query(RiskAssessment)
         .filter(RiskAssessment.student_id == student_id)
         .order_by(RiskAssessment.assessment_timestamp.desc()).first())
    if not r:
        return {"student_id": student_id, "risk_assessment": None, "message": "No risk assessment found"}
    return {
        "risk_id": r.risk_id, "student_id": r.student_id, "enrollment_id": r.enrollment_id,
        "risk_score": r.risk_score, "risk_category": r.risk_category, "cutoff_date": r.cutoff_date,
        "data_completeness": r.data_completeness, "model_version": r.model_version,
        "factor_scores": r.factor_scores, "factor_weights": r.factor_weights,
        "reasons": r.reasons, "assessment_timestamp": r.assessment_timestamp,
        "is_anomaly": r.is_anomaly,
    }


@router.get("/{student_id}/attendance")
def student_attendance_summary(student_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    """Return attendance summary across all enrollments for a student."""
    s = db.query(Student).filter(Student.student_id == student_id).first()
    if not s:
        raise HTTPException(404, f"Student {student_id} not found")
    enrollments = db.query(Enrollment).filter(Enrollment.student_id == student_id).all()
    enrollment_ids = [e.enrollment_id for e in enrollments]
    if not enrollment_ids:
        return {"student_id": student_id, "total": 0, "present": 0, "absent": 0, "attendance_rate": None, "events": []}

    rows = (db.query(AttendanceEvent.attendance_status, func.count(AttendanceEvent.attendance_id))
            .filter(AttendanceEvent.enrollment_id.in_(enrollment_ids))
            .group_by(AttendanceEvent.attendance_status).all())
    status_map = {s_: c for s_, c in rows}
    total = sum(status_map.values())
    present = status_map.get("PRESENT", 0)
    absent = status_map.get("ABSENT", 0)
    approved = status_map.get("APPROVED_ABSENCE", 0)

    # Recent events
    recent = (db.query(AttendanceEvent)
              .filter(AttendanceEvent.enrollment_id.in_(enrollment_ids))
              .order_by(AttendanceEvent.attendance_date.desc()).limit(20).all())
    return {
        "student_id": student_id,
        "total_sessions": total,
        "present": present,
        "absent": absent,
        "approved_absence": approved,
        "attendance_rate": round((present + approved) / total * 100, 1) if total > 0 else None,
        "by_status": [{"status": st, "count": c} for st, c in rows],
        "recent_events": [{"attendance_id": e.attendance_id, "enrollment_id": e.enrollment_id,
                           "attendance_date": e.attendance_date, "attendance_status": e.attendance_status,
                           "session_number": e.session_number} for e in recent],
    }


@router.get("/{student_id}/assessments")
def student_assessments_summary(student_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    """Return assessment results for a student."""
    s = db.query(Student).filter(Student.student_id == student_id).first()
    if not s:
        raise HTTPException(404, f"Student {student_id} not found")
    enrollments = db.query(Enrollment).filter(Enrollment.student_id == student_id).all()
    enrollment_ids = [e.enrollment_id for e in enrollments]
    if not enrollment_ids:
        return {"student_id": student_id, "results": [], "avg_percentage": None}

    results = (db.query(AssessmentResult, Assessment)
               .join(Assessment, AssessmentResult.assessment_id == Assessment.assessment_id)
               .filter(AssessmentResult.enrollment_id.in_(enrollment_ids))
               .order_by(Assessment.assessment_date.desc()).limit(50).all())

    avg = db.query(func.avg(AssessmentResult.percentage)).filter(
        AssessmentResult.enrollment_id.in_(enrollment_ids),
        AssessmentResult.percentage.isnot(None)
    ).scalar()

    return {
        "student_id": student_id,
        "avg_percentage": round(avg, 1) if avg else None,
        "results": [{
            "result_id": r.result_id, "assessment_id": r.assessment_id,
            "assessment_name": a.assessment_name, "assessment_type": a.assessment_type,
            "assessment_date": a.assessment_date, "maximum_marks": a.maximum_marks,
            "marks_obtained": r.marks_obtained, "percentage": r.percentage,
            "submission_status": r.submission_status,
        } for r, a in results],
    }


@router.get("/{student_id}/history")
def student_history(student_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    """Return full event history for a student."""
    s = db.query(Student).filter(Student.student_id == student_id).first()
    if not s:
        raise HTTPException(404, f"Student {student_id} not found")

    # Risk history
    risks = (db.query(RiskAssessment).filter(RiskAssessment.student_id == student_id)
             .order_by(RiskAssessment.assessment_timestamp.desc()).limit(10).all())
    # Support cases
    cases = db.query(SupportCase).filter(SupportCase.student_id == student_id).all()
    # Interventions
    intervs = db.query(Intervention).filter(Intervention.student_id == student_id).all()

    return {
        "student_id": student_id,
        "risk_history": [{"risk_id": r.risk_id, "risk_score": r.risk_score, "risk_category": r.risk_category,
                           "cutoff_date": r.cutoff_date, "assessment_timestamp": r.assessment_timestamp,
                           "reasons": r.reasons} for r in risks],
        "support_cases": [{"case_id": c.case_id, "case_type": c.case_type, "priority": c.priority,
                           "case_status": c.case_status, "opened_at": c.opened_at} for c in cases],
        "interventions": [{"intervention_id": i.intervention_id, "intervention_type": i.intervention_type,
                           "intervention_status": i.intervention_status, "trigger_date": i.trigger_date,
                           "completion_date": i.completion_date} for i in intervs],
    }


