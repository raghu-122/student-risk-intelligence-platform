"""
Analytics API routes — real-time aggregated metrics from the database.
No hardcoded values: every figure is derived from actual records.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from app.db.database import get_db
from app.api.dependencies.auth import get_current_user
from app.models.student import Student
from app.models.enrollment import Enrollment
from app.models.attendance import AttendanceEvent
from app.models.assessment_result import AssessmentResult
from app.models.assessment import Assessment
from app.models.lms_activity import LMSActivity
from app.models.risk_assessment import RiskAssessment
from app.models.intervention import Intervention
from app.models.outcome import Outcome
from app.models.support_case import SupportCase

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def _latest_risk_subquery(db):
    return (
        db.query(
            RiskAssessment.student_id,
            func.max(RiskAssessment.assessment_timestamp).label("latest"),
        )
        .group_by(RiskAssessment.student_id)
        .subquery()
    )


@router.get("/overview")
def analytics_overview(db: Session = Depends(get_db), _=Depends(get_current_user)):
    """High-level platform statistics."""
    total_students = db.query(func.count(Student.student_id)).scalar() or 0
    active_students = db.query(func.count(Student.student_id)).filter(Student.current_status == "ACTIVE").scalar() or 0
    total_courses = db.query(func.count()).select_from(Enrollment).scalar() or 0
    total_enrollments = total_courses  # same query

    sq = _latest_risk_subquery(db)
    latest_risks = (
        db.query(RiskAssessment)
        .join(sq, (RiskAssessment.student_id == sq.c.student_id)
              & (RiskAssessment.assessment_timestamp == sq.c.latest))
        .all()
    )
    high_risk = sum(1 for r in latest_risks if r.risk_category == "HIGH")
    medium_risk = sum(1 for r in latest_risks if r.risk_category == "MEDIUM")
    low_risk = sum(1 for r in latest_risks if r.risk_category == "LOW")

    open_cases = db.query(func.count(SupportCase.case_id)).filter(
        SupportCase.case_status.in_(["OPEN", "ASSIGNED", "IN_PROGRESS"])
    ).scalar() or 0

    completed = db.query(func.count(Intervention.intervention_id)).filter(
        Intervention.intervention_status == "COMPLETED"
    ).scalar() or 0
    total_interv = db.query(func.count(Intervention.intervention_id)).scalar() or 0
    completion_rate = round(completed / total_interv * 100, 1) if total_interv > 0 else 0.0

    improved = db.query(func.count(Outcome.outcome_id)).filter(Outcome.outcome_label == "IMPROVED").scalar() or 0
    total_outcomes = db.query(func.count(Outcome.outcome_id)).scalar() or 0
    improvement_rate = round(improved / total_outcomes * 100, 1) if total_outcomes > 0 else 0.0

    return {
        "total_students": total_students,
        "active_students": active_students,
        "high_risk_students": high_risk,
        "medium_risk_students": medium_risk,
        "low_risk_students": low_risk,
        "open_support_cases": open_cases,
        "intervention_completion_rate": completion_rate,
        "outcome_improvement_rate": improvement_rate,
        "total_outcomes": total_outcomes,
    }


@router.get("/attendance")
def analytics_attendance(db: Session = Depends(get_db), _=Depends(get_current_user)):
    """Attendance analytics by status."""
    rows = (
        db.query(AttendanceEvent.attendance_status, func.count(AttendanceEvent.attendance_id))
        .group_by(AttendanceEvent.attendance_status)
        .all()
    )
    status_map = {s: c for s, c in rows}
    total = sum(status_map.values())
    present = status_map.get("PRESENT", 0)
    absent = status_map.get("ABSENT", 0)
    approved = status_map.get("APPROVED_ABSENCE", 0)
    late = status_map.get("LATE", 0)

    # By department
    dept_rows = (
        db.query(Student.department, AttendanceEvent.attendance_status, func.count())
        .join(Enrollment, AttendanceEvent.enrollment_id == Enrollment.enrollment_id)
        .join(Student, Enrollment.student_id == Student.student_id)
        .group_by(Student.department, AttendanceEvent.attendance_status)
        .all()
    )
    dept_map = {}
    for dept, status, cnt in dept_rows:
        if dept not in dept_map:
            dept_map[dept] = {"department": dept, "total": 0, "present": 0, "absent": 0}
        dept_map[dept]["total"] += cnt
        if status == "PRESENT":
            dept_map[dept]["present"] += cnt
        elif status == "ABSENT":
            dept_map[dept]["absent"] += cnt

    for d in dept_map.values():
        d["attendance_rate"] = round(d["present"] / d["total"] * 100, 1) if d["total"] > 0 else 0.0

    return {
        "total_events": total,
        "present": present,
        "absent": absent,
        "approved_absence": approved,
        "late": late,
        "overall_attendance_rate": round(present / total * 100, 1) if total > 0 else 0.0,
        "by_department": list(dept_map.values()),
        "by_status": [{"status": s, "count": c} for s, c in rows],
    }


@router.get("/performance")
def analytics_performance(db: Session = Depends(get_db), _=Depends(get_current_user)):
    """Academic performance analytics."""
    rows = (
        db.query(AssessmentResult.submission_status, func.count(AssessmentResult.result_id))
        .group_by(AssessmentResult.submission_status)
        .all()
    )
    avg_pct = db.query(func.avg(AssessmentResult.percentage)).filter(
        AssessmentResult.percentage.isnot(None)
    ).scalar()

    # Pass/fail distribution (>=50% pass)
    total_graded = db.query(func.count(AssessmentResult.result_id)).filter(
        AssessmentResult.percentage.isnot(None)
    ).scalar() or 0
    passed = db.query(func.count(AssessmentResult.result_id)).filter(
        AssessmentResult.percentage >= 50
    ).scalar() or 0
    failed = total_graded - passed

    # By assessment type
    type_rows = (
        db.query(Assessment.assessment_type, func.avg(AssessmentResult.percentage), func.count())
        .join(AssessmentResult, Assessment.assessment_id == AssessmentResult.assessment_id)
        .filter(AssessmentResult.percentage.isnot(None))
        .group_by(Assessment.assessment_type)
        .all()
    )

    return {
        "average_percentage": round(avg_pct, 2) if avg_pct else None,
        "total_graded": total_graded,
        "passed": passed,
        "failed": failed,
        "pass_rate": round(passed / total_graded * 100, 1) if total_graded > 0 else 0.0,
        "by_submission_status": [{"status": s, "count": c} for s, c in rows],
        "by_assessment_type": [
            {"type": t, "avg_percentage": round(avg, 1) if avg else None, "count": cnt}
            for t, avg, cnt in type_rows
        ],
    }


@router.get("/engagement")
def analytics_engagement(db: Session = Depends(get_db), _=Depends(get_current_user)):
    """LMS engagement analytics."""
    rows = (
        db.query(LMSActivity.activity_type, func.count(LMSActivity.activity_id))
        .group_by(LMSActivity.activity_type)
        .all()
    )
    total_activities = sum(c for _, c in rows)
    avg_duration = db.query(func.avg(LMSActivity.duration_minutes)).filter(
        LMSActivity.duration_minutes.isnot(None)
    ).scalar()

    # Engagement by department
    dept_rows = (
        db.query(Student.department, func.count(LMSActivity.activity_id))
        .join(Enrollment, LMSActivity.enrollment_id == Enrollment.enrollment_id)
        .join(Student, Enrollment.student_id == Student.student_id)
        .group_by(Student.department)
        .all()
    )

    return {
        "total_activities": total_activities,
        "avg_session_duration_minutes": round(avg_duration, 1) if avg_duration else None,
        "by_activity_type": [{"type": t, "count": c} for t, c in rows],
        "by_department": [{"department": d, "activity_count": c} for d, c in dept_rows],
    }


@router.get("/risk-distribution")
def analytics_risk_distribution(db: Session = Depends(get_db), _=Depends(get_current_user)):
    """Risk distribution (mirrors dashboard endpoint, available under /analytics)."""
    sq = _latest_risk_subquery(db)
    rows = (
        db.query(RiskAssessment.risk_category, func.count(RiskAssessment.risk_id))
        .join(sq, (RiskAssessment.student_id == sq.c.student_id)
              & (RiskAssessment.assessment_timestamp == sq.c.latest))
        .group_by(RiskAssessment.risk_category)
        .all()
    )
    return [{"category": cat, "count": cnt} for cat, cnt in rows]


@router.get("/intervention-effectiveness")
def analytics_intervention_effectiveness(db: Session = Depends(get_db), _=Depends(get_current_user)):
    """Intervention effectiveness based on outcome labels."""
    rows = (
        db.query(Outcome.outcome_label, func.count(Outcome.outcome_id))
        .group_by(Outcome.outcome_label)
        .all()
    )
    total = sum(c for _, c in rows)
    by_label = {lbl: cnt for lbl, cnt in rows}

    improved = by_label.get("IMPROVED", 0)
    no_change = by_label.get("NO_CHANGE", 0)
    declined = by_label.get("DECLINED", 0)
    insufficient = by_label.get("INSUFFICIENT_DATA", 0)

    # By intervention type
    type_rows = (
        db.query(Intervention.intervention_type, Outcome.outcome_label, func.count())
        .join(Outcome, Intervention.intervention_id == Outcome.intervention_id, isouter=True)
        .filter(Outcome.outcome_label.isnot(None))
        .group_by(Intervention.intervention_type, Outcome.outcome_label)
        .all()
    )

    type_map = {}
    for itype, olabel, cnt in type_rows:
        if itype not in type_map:
            type_map[itype] = {"intervention_type": itype, "total": 0, "improved": 0}
        type_map[itype]["total"] += cnt
        if olabel == "IMPROVED":
            type_map[itype]["improved"] += cnt
    for t in type_map.values():
        t["effectiveness_rate"] = round(t["improved"] / t["total"] * 100, 1) if t["total"] > 0 else 0.0

    return {
        "total_outcomes": total,
        "improved": improved,
        "no_change": no_change,
        "declined": declined,
        "insufficient_data": insufficient,
        "improvement_rate": round(improved / total * 100, 1) if total > 0 else 0.0,
        "by_outcome_label": [{"label": lbl, "count": cnt} for lbl, cnt in rows],
        "by_intervention_type": list(type_map.values()),
    }

