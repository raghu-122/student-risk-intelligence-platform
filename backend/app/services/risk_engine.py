"""
Risk Engine — Calculates explainable student risk scores.

Business rules:
- Uses ONLY data with dates <= cutoff_date (temporal-leakage prevention).
- NULL marks are NEVER treated as 0; they are excluded from averages.
- Attendance rate = (PRESENT + LATE) / (total - APPROVED_ABSENCE).
- If data completeness < MIN_DATA_COMPLETENESS the result is INSUFFICIENT_DATA.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from app.core.constants import (
    AttendanceStatus,
    MIN_DATA_COMPLETENESS,
    RISK_WEIGHTS,
    RiskCategory,
)
from app.models.assessment import Assessment
from app.models.assessment_result import AssessmentResult
from app.models.attendance import AttendanceEvent
from app.models.enrollment import Enrollment
from app.models.lms_activity import LMSActivity
from app.models.support_case import SupportCase

MODEL_VERSION = "v1.0"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _categorize(score: float) -> str:
    if score <= 24:
        return RiskCategory.LOW
    if score <= 49:
        return RiskCategory.MEDIUM
    if score <= 74:
        return RiskCategory.HIGH
    return RiskCategory.CRITICAL


# ---------------------------------------------------------------------------
# individual factor calculators
# ---------------------------------------------------------------------------

def _attendance_risk(db: Session, enrollment_id: str, cutoff: date) -> Dict[str, Any]:
    """
    Returns risk 0-100 (higher = worse).
    Rate = (PRESENT+LATE) / (total_sessions - APPROVED_ABSENCE).
    Approved absences are excluded from the denominator.
    """
    events = (
        db.query(AttendanceEvent)
        .filter(
            AttendanceEvent.enrollment_id == enrollment_id,
            AttendanceEvent.attendance_date <= cutoff,
        )
        .all()
    )

    if len(events) < 3:
        return {"data_available": False, "normalized_score": None,
                "explanation": f"Only {len(events)} attendance records before cutoff — insufficient"}

    approved = sum(1 for e in events if e.attendance_status == AttendanceStatus.APPROVED_ABSENCE)
    effective = len(events) - approved
    if effective == 0:
        return {"data_available": False, "normalized_score": None,
                "explanation": "All sessions are approved absences"}

    attended = sum(
        1 for e in events
        if e.attendance_status in (AttendanceStatus.PRESENT, AttendanceStatus.LATE)
    )
    rate = attended / effective
    score = round(max(0.0, min(100.0, (1 - rate) * 100)), 2)
    flag = ""
    if rate < 0.6:
        flag = " — CHRONIC ABSENTEEISM"
    elif rate < 0.75:
        flag = " — below 75% threshold"

    return {
        "data_available": True,
        "raw_value": round(rate, 4),
        "normalized_score": score,
        "explanation": (
            f"Attendance {rate:.1%} = {attended}/{effective} sessions"
            f" ({approved} approved-absence sessions excluded from denominator){flag}"
        ),
        "attended": attended,
        "effective_denominator": effective,
        "approved_absences": approved,
        "total_sessions": len(events),
    }


def _academic_risk(db: Session, enrollment_id: str, cutoff: date) -> Dict[str, Any]:
    """
    Weighted-average assessment score up to cutoff.
    NULL marks are excluded — NOT treated as 0.
    Uses assessment_date <= cutoff to prevent temporal leakage.
    """
    rows = (
        db.query(AssessmentResult, Assessment)
        .join(Assessment, AssessmentResult.assessment_id == Assessment.assessment_id)
        .filter(
            AssessmentResult.enrollment_id == enrollment_id,
            Assessment.assessment_date <= cutoff,  # temporal-leakage guard
        )
        .all()
    )

    graded = [(r, a) for r, a in rows if r.marks_obtained is not None and r.percentage is not None]
    missing_count = len(rows) - len(graded)

    if not graded:
        return {
            "data_available": False,
            "normalized_score": None,
            "explanation": "No graded assessments before cutoff — not treated as failure",
            "total_before_cutoff": len(rows),
            "missing_count": missing_count,
        }

    total_w = sum(a.weightage for _, a in graded)
    if total_w == 0:
        avg = sum(r.percentage for r, _ in graded) / len(graded)
    else:
        avg = sum(r.percentage * a.weightage for r, a in graded) / total_w

    score = round(max(0.0, min(100.0, (1 - avg / 100) * 100)), 2)
    note = ""
    if missing_count:
        note = f"; {missing_count} unsubmitted assessment(s) excluded (not scored as 0)"

    return {
        "data_available": True,
        "raw_value": round(avg, 2),
        "normalized_score": score,
        "explanation": f"Weighted average {avg:.1f}% over {len(graded)} graded assessment(s){note}",
        "graded_count": len(graded),
        "missing_count": missing_count,
    }


def _trend_risk(db: Session, enrollment_id: str, cutoff: date) -> Dict[str, Any]:
    """Compare first-half vs second-half graded assessment scores."""
    rows = (
        db.query(AssessmentResult, Assessment)
        .join(Assessment, AssessmentResult.assessment_id == Assessment.assessment_id)
        .filter(
            AssessmentResult.enrollment_id == enrollment_id,
            Assessment.assessment_date <= cutoff,
            AssessmentResult.marks_obtained.isnot(None),
        )
        .order_by(Assessment.assessment_date)
        .all()
    )

    if len(rows) < 2:
        return {"data_available": False, "normalized_score": None,
                "explanation": "Need ≥2 graded assessments for trend analysis"}

    mid = len(rows) // 2
    first_avg = sum(r.percentage for r, _ in rows[:mid]) / mid
    second_avg = sum(r.percentage for r, _ in rows[mid:]) / (len(rows) - mid)
    trend = second_avg - first_avg

    # -20 → +20 mapped to risk 100 → 0
    score = round(max(0.0, min(100.0, (-trend + 20) / 40 * 100)), 2)

    if trend > 5:
        label = f"Improving +{trend:.1f}%"
    elif trend < -5:
        label = f"Declining {trend:.1f}% — WARNING"
    else:
        label = f"Stable {trend:+.1f}%"

    return {
        "data_available": True,
        "raw_value": round(trend, 2),
        "normalized_score": score,
        "explanation": f"{label} (early avg {first_avg:.1f}% → recent avg {second_avg:.1f}%)",
        "first_half_avg": round(first_avg, 2),
        "second_half_avg": round(second_avg, 2),
    }


def _lms_risk(db: Session, enrollment_id: str, cutoff: date) -> Dict[str, Any]:
    """LMS engagement risk based on activity frequency relative to expected."""
    acts = (
        db.query(LMSActivity)
        .filter(
            LMSActivity.enrollment_id == enrollment_id,
            LMSActivity.activity_timestamp
            <= datetime.combine(cutoff, datetime.max.time()),
        )
        .all()
    )

    enr = db.query(Enrollment).filter(Enrollment.enrollment_id == enrollment_id).first()
    if enr and enr.effective_from <= cutoff:
        days = max(1, (cutoff - enr.effective_from).days)
    else:
        days = 90
    weeks = max(1, days / 7)
    expected = weeks * 2  # 2 activities/week expected

    engagement_rate = min(1.0, len(acts) / max(1, expected))
    score = round(max(0.0, min(100.0, (1 - engagement_rate) * 100)), 2)
    total_min = sum(a.duration_minutes or 0 for a in acts)
    types = len(set(a.activity_type for a in acts))

    label = ""
    if engagement_rate < 0.3:
        label = " — VERY LOW"
    elif engagement_rate < 0.6:
        label = " — below expected"

    return {
        "data_available": True,
        "raw_value": round(engagement_rate, 4),
        "normalized_score": score,
        "explanation": (
            f"LMS engagement {engagement_rate:.0%}: {len(acts)} activities, "
            f"{total_min} min total, {types} activity type(s){label}"
        ),
        "activity_count": len(acts),
        "total_minutes": total_min,
        "activity_types": types,
    }


def _support_risk(db: Session, student_id: str, cutoff: date) -> Dict[str, Any]:
    """Historical support risk based on number and severity of past cases."""
    cases = (
        db.query(SupportCase)
        .filter(
            SupportCase.student_id == student_id,
            SupportCase.opened_at
            <= datetime.combine(cutoff, datetime.max.time()),
        )
        .all()
    )

    total = len(cases)
    open_c = sum(1 for c in cases if c.case_status not in ("RESOLVED", "CLOSED"))
    critical = sum(1 for c in cases if c.priority == "CRITICAL")

    score = round(min(100.0, total * 15 + open_c * 10 + critical * 20), 2)

    return {
        "data_available": True,
        "raw_value": total,
        "normalized_score": score,
        "explanation": (
            f"Support history: {total} case(s), {open_c} open, {critical} critical-priority"
        ),
        "total_cases": total,
        "open_cases": open_c,
        "critical_cases": critical,
    }


# ---------------------------------------------------------------------------
# public entry point
# ---------------------------------------------------------------------------

def calculate_enrollment_risk(
    db: Session,
    student_id: str,
    enrollment_id: str,
    cutoff_date: date,
    model_version: str = MODEL_VERSION,
    is_anomaly: bool = False,
) -> Dict[str, Any]:
    """
    Calculate a full risk assessment for one enrollment as of cutoff_date.
    Returns a plain dict ready to be persisted as a RiskAssessment row.
    """
    weights = RISK_WEIGHTS.copy()

    factors: Dict[str, Dict[str, Any]] = {
        "attendance": _attendance_risk(db, enrollment_id, cutoff_date),
        "academic_performance": _academic_risk(db, enrollment_id, cutoff_date),
        "performance_trend": _trend_risk(db, enrollment_id, cutoff_date),
        "lms_engagement": _lms_risk(db, enrollment_id, cutoff_date),
        "historical_support": _support_risk(db, student_id, cutoff_date),
    }

    available = sum(1 for f in factors.values() if f.get("data_available"))
    completeness = round(available / len(factors), 2)

    if completeness < MIN_DATA_COMPLETENESS:
        return {
            "student_id": student_id,
            "enrollment_id": enrollment_id,
            "cutoff_date": cutoff_date,
            "risk_score": None,
            "risk_category": RiskCategory.INSUFFICIENT_DATA,
            "factor_scores": {k: v.get("normalized_score") for k, v in factors.items()},
            "factor_weights": weights,
            "reasons": [v.get("explanation", "") for v in factors.values()],
            "data_completeness": completeness,
            "model_version": model_version,
            "is_anomaly": is_anomaly,
            "factor_details": factors,
        }

    # Weighted composite (re-normalised across available factors)
    total_w = sum(weights[k] for k, v in factors.items() if v.get("data_available") and v.get("normalized_score") is not None)
    if total_w == 0:
        risk_score: Optional[float] = None
        risk_category = RiskCategory.INSUFFICIENT_DATA
    else:
        raw_score = sum(
            factors[k]["normalized_score"] * weights[k]
            for k in factors
            if factors[k].get("data_available") and factors[k].get("normalized_score") is not None
        ) / total_w

        # Small completeness penalty if some factors missing
        penalty = (1 - completeness) * 8
        risk_score = round(min(100.0, raw_score + penalty), 2)
        risk_category = _categorize(risk_score)

    reasons = [v.get("explanation", "") for v in factors.values() if v.get("explanation")]

    return {
        "student_id": student_id,
        "enrollment_id": enrollment_id,
        "cutoff_date": cutoff_date,
        "risk_score": risk_score,
        "risk_category": risk_category,
        "factor_scores": {k: v.get("normalized_score") for k, v in factors.items()},
        "factor_weights": weights,
        "reasons": reasons,
        "data_completeness": completeness,
        "model_version": model_version,
        "is_anomaly": is_anomaly,
        "factor_details": factors,
    }

