"""
Analytics Engine — dashboard KPIs and chart datasets.
All values are computed from real database records; nothing is hardcoded.
"""
from __future__ import annotations

from typing import Any, Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.intervention import Intervention
from app.models.outcome import Outcome
from app.models.risk_assessment import RiskAssessment
from app.models.student import Student
from app.models.support_case import SupportCase
from app.models.attendance import AttendanceEvent
from app.models.assessment_result import AssessmentResult
from app.models.assessment import Assessment


def _latest_risk_subquery(db: Session):
    return (
        db.query(
            RiskAssessment.student_id,
            func.max(RiskAssessment.assessment_timestamp).label("latest"),
        )
        .group_by(RiskAssessment.student_id)
        .subquery()
    )


def get_dashboard_stats(db: Session) -> Dict[str, Any]:
    total_students = db.query(func.count(Student.student_id)).scalar() or 0
    total_courses = db.query(func.count(Course.course_id)).scalar() or 0
    total_enrollments = db.query(func.count(Enrollment.enrollment_id)).scalar() or 0

    sq = _latest_risk_subquery(db)
    latest_risks = (
        db.query(RiskAssessment)
        .join(
            sq,
            (RiskAssessment.student_id == sq.c.student_id)
            & (RiskAssessment.assessment_timestamp == sq.c.latest),
        )
        .all()
    )

    students_at_risk = sum(1 for r in latest_risks if r.risk_category in ("HIGH", "CRITICAL"))
    critical_risk = sum(1 for r in latest_risks if r.risk_category == "CRITICAL")
    high_risk = sum(1 for r in latest_risks if r.risk_category == "HIGH")

    active_cases = (
        db.query(func.count(SupportCase.case_id))
        .filter(SupportCase.case_status.in_(["OPEN", "ASSIGNED", "IN_PROGRESS"]))
        .scalar() or 0
    )
    active_interventions = (
        db.query(func.count(Intervention.intervention_id))
        .filter(Intervention.intervention_status.in_(["APPROVED", "ASSIGNED", "IN_PROGRESS"]))
        .scalar() or 0
    )
    completed_interv = (
        db.query(func.count(Intervention.intervention_id))
        .filter(Intervention.intervention_status == "COMPLETED")
        .scalar() or 0
    )
    total_interv = (
        db.query(func.count(Intervention.intervention_id))
        .filter(
            Intervention.intervention_status.in_(
                ["COMPLETED", "CANCELLED", "REJECTED", "IN_PROGRESS"]
            )
        )
        .scalar() or 0
    )
    completion_rate = round(completed_interv / total_interv * 100, 1) if total_interv > 0 else 0.0

    improving = (
        db.query(func.count(Outcome.outcome_id))
        .filter(Outcome.outcome_label == "IMPROVED")
        .scalar() or 0
    )

    return {
        "total_students": total_students,
        "total_courses": total_courses,
        "total_enrollments": total_enrollments,
        "students_at_risk": students_at_risk,
        "critical_risk_students": critical_risk,
        "high_risk_students": high_risk,
        "active_support_cases": active_cases,
        "active_interventions": active_interventions,
        "intervention_completion_rate": completion_rate,
        "students_improving": improving,
    }


def get_risk_distribution(db: Session) -> List[Dict[str, Any]]:
    sq = _latest_risk_subquery(db)
    rows = (
        db.query(RiskAssessment.risk_category, func.count(RiskAssessment.risk_id))
        .join(
            sq,
            (RiskAssessment.student_id == sq.c.student_id)
            & (RiskAssessment.assessment_timestamp == sq.c.latest),
        )
        .group_by(RiskAssessment.risk_category)
        .all()
    )
    return [{"category": cat, "count": cnt} for cat, cnt in rows]


def get_risk_by_department(db: Session) -> List[Dict[str, Any]]:
    sq = _latest_risk_subquery(db)
    rows = (
        db.query(Student.department, RiskAssessment.risk_category, func.count())
        .join(RiskAssessment, Student.student_id == RiskAssessment.student_id)
        .join(
            sq,
            (RiskAssessment.student_id == sq.c.student_id)
            & (RiskAssessment.assessment_timestamp == sq.c.latest),
        )
        .group_by(Student.department, RiskAssessment.risk_category)
        .all()
    )
    dept_map: Dict[str, Dict[str, Any]] = {}
    for dept, cat, cnt in rows:
        if dept not in dept_map:
            dept_map[dept] = {"department": dept}
        dept_map[dept][cat] = cnt
    return list(dept_map.values())


def get_outcome_distribution(db: Session) -> List[Dict[str, Any]]:
    rows = (
        db.query(Outcome.outcome_label, func.count(Outcome.outcome_id))
        .group_by(Outcome.outcome_label)
        .all()
    )
    return [{"label": lbl, "count": cnt} for lbl, cnt in rows]


def get_intervention_outcomes(db: Session) -> List[Dict[str, Any]]:
    rows = (
        db.query(Intervention.intervention_status, func.count(Intervention.intervention_id))
        .group_by(Intervention.intervention_status)
        .all()
    )
    return [{"status": s, "count": c} for s, c in rows]

