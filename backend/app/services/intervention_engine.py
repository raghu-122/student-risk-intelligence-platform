"""
Intervention Recommendation Engine — rule-based, explainable recommendations.
Each recommendation is derived from actual risk factor scores, never arbitrary.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List

from app.core.constants import CasePriority, InterventionStatus, InterventionType


def recommend_interventions(
    risk_assessment: Dict[str, Any],
    trigger_date: date,
    available_staff_id: str | None = None,
) -> List[Dict[str, Any]]:
    """
    Generate intervention recommendations from a risk assessment dict.
    Returns a list of recommendation dicts (not yet persisted).
    """
    factors: Dict[str, Any] = risk_assessment.get("factor_scores") or {}
    student_id: str = risk_assessment.get("student_id", "")
    enrollment_id: str | None = risk_assessment.get("enrollment_id")
    risk_id: str | None = risk_assessment.get("risk_id")
    overall_score: float = risk_assessment.get("risk_score") or 0.0

    recs: List[Dict[str, Any]] = []
    active_risk_count = 0

    def _add(itype: str, reason: str, priority: str, days_due: int, expected: str) -> None:
        nonlocal active_risk_count
        active_risk_count += 1
        recs.append({
            "intervention_type": itype,
            "reason": reason,
            "priority": priority,
            "trigger_date": trigger_date,
            "due_date": trigger_date + timedelta(days=days_due),
            "expected_outcome": expected,
            "student_id": student_id,
            "enrollment_id": enrollment_id,
            "risk_assessment_id": risk_id,
            "assigned_staff_id": available_staff_id,
            "intervention_status": InterventionStatus.RECOMMENDED,
        })

    att = factors.get("attendance")
    if att is not None and att > 40:
        _add(
            InterventionType.ATTENDANCE_COUNSELLING,
            f"Attendance risk {att:.1f}/100 — chronic or at-risk absenteeism detected",
            CasePriority.HIGH if att > 60 else CasePriority.MEDIUM,
            14,
            "Attendance rate improves above 75% within 4 weeks",
        )

    acad = factors.get("academic_performance")
    if acad is not None and acad > 40:
        _add(
            InterventionType.ACADEMIC_TUTORING,
            f"Academic performance risk {acad:.1f}/100 — below expected standard",
            CasePriority.HIGH if acad > 60 else CasePriority.MEDIUM,
            21,
            "Assessment scores improve by ≥10 percentage points",
        )

    trend = factors.get("performance_trend")
    if trend is not None and trend > 55:
        _add(
            InterventionType.INSTRUCTOR_MEETING,
            f"Declining performance trend (risk {trend:.1f}/100)",
            CasePriority.MEDIUM,
            7,
            "Instructor identifies root cause; action plan agreed within one week",
        )

    lms = factors.get("lms_engagement")
    if lms is not None and lms > 50:
        _add(
            InterventionType.ENGAGEMENT_SUPPORT,
            f"LMS engagement risk {lms:.1f}/100 — insufficient platform activity",
            CasePriority.LOW if lms < 70 else CasePriority.MEDIUM,
            14,
            "LMS activity increases to expected levels within 3 weeks",
        )

    supp = factors.get("historical_support")
    if supp is not None and supp > 40:
        _add(
            InterventionType.ADVISOR_REVIEW,
            f"Multiple historical support cases (risk {supp:.1f}/100)",
            CasePriority.HIGH,
            7,
            "Advisor reviews case history and builds comprehensive support plan",
        )

    # Personalised plan when ≥3 risk factors are active OR overall is CRITICAL
    if active_risk_count >= 3 or overall_score >= 75:
        recs.append({
            "intervention_type": InterventionType.PERSONALIZED_PLAN,
            "reason": (
                f"Multiple simultaneous risk indicators "
                f"({active_risk_count} factor(s), overall score {overall_score:.1f})"
            ),
            "priority": CasePriority.CRITICAL,
            "trigger_date": trigger_date,
            "due_date": trigger_date + timedelta(days=5),
            "expected_outcome": "Coordinated multi-factor support plan developed within 1 week",
            "student_id": student_id,
            "enrollment_id": enrollment_id,
            "risk_assessment_id": risk_id,
            "assigned_staff_id": available_staff_id,
            "intervention_status": InterventionStatus.RECOMMENDED,
        })

    return recs

