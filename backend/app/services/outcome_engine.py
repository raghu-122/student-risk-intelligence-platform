"""
Outcome Evaluation Engine.

Compares a 'baseline' period (before cutoff) against a 'future' period.
Improvement/decline is computed on attendance rate, academic average,
and LMS engagement rate.

Important: This engine measures *association*, not causation.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from app.core.constants import AttendanceStatus, OutcomeLabel
from app.models.assessment import Assessment
from app.models.assessment_result import AssessmentResult
from app.models.attendance import AttendanceEvent
from app.models.enrollment import Enrollment
from app.models.lms_activity import LMSActivity

IMPROVE_THRESHOLD = 5.0   # pp improvement to count as improved
DECLINE_THRESHOLD = -5.0  # pp decline to count as declined


def _attendance_rate(db: Session, enrollment_id: str, start: Optional[date], end: date) -> Optional[float]:
    q = db.query(AttendanceEvent).filter(
        AttendanceEvent.enrollment_id == enrollment_id,
        AttendanceEvent.attendance_date <= end,
    )
    if start:
        q = q.filter(AttendanceEvent.attendance_date >= start)
    evts = q.all()
    if len(evts) < 2:
        return None
    approved = sum(1 for e in evts if e.attendance_status == AttendanceStatus.APPROVED_ABSENCE)
    effective = len(evts) - approved
    if effective == 0:
        return None
    attended = sum(1 for e in evts if e.attendance_status in (AttendanceStatus.PRESENT, AttendanceStatus.LATE))
    return attended / effective


def _academic_avg(db: Session, enrollment_id: str, start: Optional[date], end: date) -> Optional[float]:
    q = (
        db.query(AssessmentResult)
        .join(Assessment, AssessmentResult.assessment_id == Assessment.assessment_id)
        .filter(
            AssessmentResult.enrollment_id == enrollment_id,
            Assessment.assessment_date <= end,
            AssessmentResult.marks_obtained.isnot(None),
        )
    )
    if start:
        q = q.filter(Assessment.assessment_date >= start)
    rows = q.all()
    if not rows:
        return None
    return sum(r.percentage for r in rows if r.percentage is not None) / len(rows)


def _lms_rate(db: Session, enrollment_id: str, start: Optional[date], end: date) -> Optional[float]:
    """Activities per week."""
    q = db.query(LMSActivity).filter(
        LMSActivity.enrollment_id == enrollment_id,
        LMSActivity.activity_timestamp <= datetime.combine(end, datetime.max.time()),
    )
    if start:
        q = q.filter(LMSActivity.activity_timestamp >= datetime.combine(start, datetime.min.time()))
    acts = q.all()
    if start:
        days = max(1, (end - start).days)
    else:
        days = 180
    weeks = max(1, days / 7)
    return len(acts) / weeks


def evaluate_outcome(
    db: Session,
    student_id: str,
    enrollment_id: str,
    baseline_cutoff: date,
    eval_start: date,
    eval_end: date,
    baseline_risk_score: Optional[float],
    intervention_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Evaluate outcome by comparing baseline (<=cutoff) vs future (eval_start..eval_end).
    Returns a plain dict ready to be persisted as an Outcome row.
    """
    base_att = _attendance_rate(db, enrollment_id, None, baseline_cutoff)
    base_acad = _academic_avg(db, enrollment_id, None, baseline_cutoff)
    base_lms = _lms_rate(db, enrollment_id, None, baseline_cutoff)

    fut_att = _attendance_rate(db, enrollment_id, eval_start, eval_end)
    fut_acad = _academic_avg(db, enrollment_id, eval_start, eval_end)
    fut_lms = _lms_rate(db, enrollment_id, eval_start, eval_end)

    has_future = any(x is not None for x in (fut_att, fut_acad, fut_lms))
    if not has_future:
        return {
            "student_id": student_id,
            "enrollment_id": enrollment_id,
            "intervention_id": intervention_id,
            "evaluation_period_start": eval_start,
            "evaluation_period_end": eval_end,
            "baseline_risk_score": baseline_risk_score,
            "future_risk_score": None,
            "academic_performance_change": None,
            "attendance_change": None,
            "engagement_change": None,
            "outcome_label": OutcomeLabel.INSUFFICIENT_DATA,
            "evaluation_date": eval_end,
        }

    att_chg = round((fut_att - base_att) * 100, 2) if (fut_att is not None and base_att is not None) else None
    acad_chg = round(fut_acad - base_acad, 2) if (fut_acad is not None and base_acad is not None) else None
    lms_chg = round((fut_lms - base_lms) * 10, 2) if (fut_lms is not None and base_lms is not None) else None

    changes = [c for c in (att_chg, acad_chg, lms_chg) if c is not None]
    if not changes:
        label = OutcomeLabel.INSUFFICIENT_DATA
    else:
        avg_chg = sum(changes) / len(changes)
        improved = sum(1 for c in changes if c > IMPROVE_THRESHOLD)
        declined = sum(1 for c in changes if c < DECLINE_THRESHOLD)
        if improved >= 2 or avg_chg > IMPROVE_THRESHOLD:
            label = OutcomeLabel.IMPROVED
        elif declined >= 2 or avg_chg < DECLINE_THRESHOLD:
            label = OutcomeLabel.DECLINED
        else:
            label = OutcomeLabel.STABLE

    return {
        "student_id": student_id,
        "enrollment_id": enrollment_id,
        "intervention_id": intervention_id,
        "evaluation_period_start": eval_start,
        "evaluation_period_end": eval_end,
        "baseline_risk_score": baseline_risk_score,
        "future_risk_score": None,
        "academic_performance_change": acad_chg,
        "attendance_change": att_chg,
        "engagement_change": lms_chg,
        "outcome_label": label,
        "evaluation_date": eval_end,
    }

