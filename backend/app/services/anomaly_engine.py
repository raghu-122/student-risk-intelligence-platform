"""
Anomaly Detection Engine — detects all 5 required anomaly types.

Each detector looks for a specific class of data integrity violation.
Detection operates on clearly labelled (is_anomaly=True) records so it
does NOT corrupt normal production data.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.core.constants import AnomalyType, AttendanceStatus
from app.models.assessment import Assessment
from app.models.assessment_result import AssessmentResult
from app.models.attendance import AttendanceEvent
from app.models.enrollment import Enrollment
from app.models.intervention import Intervention
from app.models.risk_assessment import RiskAssessment
from app.models.student import Student


# ---------------------------------------------------------------------------
# Anomaly 1 — Temporal leakage
# ---------------------------------------------------------------------------
def detect_temporal_leakage(db: Session, risk_id: str) -> Optional[Dict[str, Any]]:
    """
    Detect if a risk assessment has available assessment data after its cutoff_date.
    A correct engine must only use data with assessment_date <= cutoff_date.
    """
    ra = db.query(RiskAssessment).filter(RiskAssessment.risk_id == risk_id).first()
    if not ra or not ra.enrollment_id:
        return None

    future_rows = (
        db.query(AssessmentResult, Assessment)
        .join(Assessment, AssessmentResult.assessment_id == Assessment.assessment_id)
        .filter(
            AssessmentResult.enrollment_id == ra.enrollment_id,
            Assessment.assessment_date > ra.cutoff_date,
        )
        .all()
    )

    if future_rows:
        future_dates = sorted({str(a.assessment_date) for _, a in future_rows})
        return {
            "issue_type": AnomalyType.TEMPORAL_LEAKAGE,
            "affected_entity": "RiskAssessment",
            "affected_record_id": risk_id,
            "expected_behavior": f"All assessment data must have assessment_date <= {ra.cutoff_date}",
            "observed_behavior": (
                f"{len(future_rows)} assessment result(s) exist with assessment_date after cutoff: {future_dates}"
            ),
            "ground_truth_label": "ANOMALY_CONFIRMED",
            "detection_status": "DETECTED",
            "explanation": (
                f"Risk assessment {risk_id} (cutoff {ra.cutoff_date}) is linked to enrollment "
                f"{ra.enrollment_id} which has assessment records dated AFTER the cutoff. "
                "This would cause the model to illegitimately use future grade information."
            ),
            "severity": "CRITICAL",
            "is_injected_anomaly": True,
        }
    return None


# ---------------------------------------------------------------------------
# Anomaly 2 — Wrong denominator in attendance calculation
# ---------------------------------------------------------------------------
def detect_wrong_denominator(db: Session, enrollment_id: str) -> Optional[Dict[str, Any]]:
    """
    Correct:  rate = attended / (total - approved_absences)
    Wrong:    rate = attended / total  (approved absences included in denominator)
    Detects when the two differ by > 1 percentage point.
    """
    evts = db.query(AttendanceEvent).filter(
        AttendanceEvent.enrollment_id == enrollment_id
    ).all()

    if len(evts) < 3:
        return None

    total = len(evts)
    approved = sum(1 for e in evts if e.attendance_status == AttendanceStatus.APPROVED_ABSENCE)
    attended = sum(
        1 for e in evts
        if e.attendance_status in (AttendanceStatus.PRESENT, AttendanceStatus.LATE)
    )
    effective = total - approved

    if effective == 0:
        return None

    correct_rate = attended / effective
    wrong_rate = attended / total

    if abs(correct_rate - wrong_rate) > 0.01:
        return {
            "issue_type": AnomalyType.WRONG_DENOMINATOR,
            "affected_entity": "AttendanceEvent",
            "affected_record_id": enrollment_id,
            "expected_behavior": (
                f"Attendance rate = {attended}/{effective} = {correct_rate:.1%} "
                f"(approved absences excluded from denominator)"
            ),
            "observed_behavior": (
                f"Wrong rate = {attended}/{total} = {wrong_rate:.1%} "
                f"(approved absences incorrectly included in denominator)"
            ),
            "ground_truth_label": "ANOMALY_CONFIRMED",
            "detection_status": "DETECTED",
            "explanation": (
                f"Enrollment {enrollment_id} has {approved} approved-absence session(s). "
                f"Correct denominator is {effective} (total {total} minus {approved} approved). "
                f"Wrong calculation overstates absence by {(wrong_rate - correct_rate) * 100:.1f}pp."
            ),
            "severity": "HIGH",
            "is_injected_anomaly": True,
        }
    return None


# ---------------------------------------------------------------------------
# Anomaly 3 — Lifecycle inconsistency (withdrawn student with active records)
# ---------------------------------------------------------------------------
def detect_lifecycle_inconsistency(db: Session, student_id: str) -> Optional[Dict[str, Any]]:
    """
    A WITHDRAWN student must not have ACTIVE enrollments or in-flight interventions.
    """
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student or student.current_status != "WITHDRAWN":
        return None

    active_enrollments = db.query(Enrollment).filter(
        Enrollment.student_id == student_id,
        Enrollment.enrollment_status == "ACTIVE",
    ).all()

    active_interventions = db.query(Intervention).filter(
        Intervention.student_id == student_id,
        Intervention.intervention_status.in_(["RECOMMENDED", "APPROVED", "ASSIGNED", "IN_PROGRESS"]),
    ).all()

    issues: List[str] = []
    if active_enrollments:
        issues.append(f"{len(active_enrollments)} ACTIVE enrollment(s): {[e.enrollment_id for e in active_enrollments]}")
    if active_interventions:
        issues.append(f"{len(active_interventions)} in-flight intervention(s): {[i.intervention_id for i in active_interventions]}")

    if issues:
        return {
            "issue_type": AnomalyType.LIFECYCLE_INCONSISTENCY,
            "affected_entity": "Student",
            "affected_record_id": student_id,
            "expected_behavior": "WITHDRAWN student should have no ACTIVE enrollments or in-progress interventions",
            "observed_behavior": f"WITHDRAWN student {student_id} has: {'; '.join(issues)}",
            "ground_truth_label": "ANOMALY_CONFIRMED",
            "detection_status": "DETECTED",
            "explanation": (
                f"Student {student_id} carries status WITHDRAWN but still has active records "
                "that violate the documented lifecycle rules."
            ),
            "severity": "HIGH",
            "is_injected_anomaly": True,
        }
    return None


# ---------------------------------------------------------------------------
# Anomaly 4 — Intervention precedes trigger
# ---------------------------------------------------------------------------
def detect_intervention_precedes_trigger(db: Session, intervention_id: str) -> Optional[Dict[str, Any]]:
    """
    An intervention's start_date must be >= its trigger_date.
    If start_date < trigger_date it is a chronological impossibility.
    """
    intv = db.query(Intervention).filter(Intervention.intervention_id == intervention_id).first()
    if not intv:
        return None

    if intv.start_date and intv.trigger_date and intv.start_date < intv.trigger_date:
        days_before = (intv.trigger_date - intv.start_date).days
        return {
            "issue_type": AnomalyType.INTERVENTION_PRECEDES_TRIGGER,
            "affected_entity": "Intervention",
            "affected_record_id": intervention_id,
            "expected_behavior": f"start_date ({intv.start_date}) must be >= trigger_date ({intv.trigger_date})",
            "observed_behavior": (
                f"Intervention {intervention_id} has start_date={intv.start_date} "
                f"which is {days_before} day(s) BEFORE trigger_date={intv.trigger_date}"
            ),
            "ground_truth_label": "ANOMALY_CONFIRMED",
            "detection_status": "DETECTED",
            "explanation": (
                f"Chronological violation: intervention {intervention_id} appears to have started "
                f"{days_before} day(s) before the event that triggered it."
            ),
            "severity": "CRITICAL",
            "is_injected_anomaly": True,
        }
    return None


# ---------------------------------------------------------------------------
# Anomaly 5 — Missing data interpreted as failure
# ---------------------------------------------------------------------------
def detect_missing_data_as_failure(db: Session, risk_id: str) -> Optional[Dict[str, Any]]:
    """
    Detect if NULL assessment marks were treated as 0 (failure) instead of being excluded.
    Signal: anomaly risk assessment has high academic_performance factor score
    despite enrollment having NULL marks, implying the NULLs were counted as zeros.
    """
    ra = db.query(RiskAssessment).filter(RiskAssessment.risk_id == risk_id).first()
    if not ra or not ra.is_anomaly or not ra.enrollment_id:
        return None

    null_results = (
        db.query(AssessmentResult)
        .filter(
            AssessmentResult.enrollment_id == ra.enrollment_id,
            AssessmentResult.marks_obtained.is_(None),
        )
        .all()
    )

    factor_scores = ra.factor_scores or {}
    academic_score = factor_scores.get("academic_performance")

    if null_results and academic_score is not None and academic_score > 60:
        return {
            "issue_type": AnomalyType.MISSING_DATA_AS_FAILURE,
            "affected_entity": "RiskAssessment",
            "affected_record_id": risk_id,
            "expected_behavior": "NULL marks_obtained should be excluded from average, not treated as 0",
            "observed_behavior": (
                f"Academic performance risk score {academic_score:.1f} is artificially high "
                f"because {len(null_results)} NULL result(s) were scored as 0"
            ),
            "ground_truth_label": "ANOMALY_CONFIRMED",
            "detection_status": "DETECTED",
            "explanation": (
                f"Risk assessment {risk_id} for enrollment {ra.enrollment_id} has "
                f"{len(null_results)} assessment result(s) with NULL marks_obtained. "
                "Treating NULL as 0 inflates the academic risk score inappropriately. "
                "Correct behaviour: exclude NULL results and return INSUFFICIENT_DATA if too few graded results remain."
            ),
            "severity": "HIGH",
            "is_injected_anomaly": True,
        }
    return None


# ---------------------------------------------------------------------------
# Convenience: run all checks
# ---------------------------------------------------------------------------
def run_all_checks(db: Session, injected_ids: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Run all five anomaly detectors against the provided injected record IDs.
    Returns list of detected-anomaly dicts.
    """
    detected: List[Dict[str, Any]] = []

    if rid := injected_ids.get("temporal_leakage_risk_id"):
        result = detect_temporal_leakage(db, rid)
        if result:
            detected.append(result)

    if eid := injected_ids.get("wrong_denominator_enrollment_id"):
        result = detect_wrong_denominator(db, eid)
        if result:
            detected.append(result)

    if sid := injected_ids.get("withdrawn_student_id"):
        result = detect_lifecycle_inconsistency(db, sid)
        if result:
            detected.append(result)

    if iid := injected_ids.get("bad_intervention_id"):
        result = detect_intervention_precedes_trigger(db, iid)
        if result:
            detected.append(result)

    if mrid := injected_ids.get("missing_data_risk_id"):
        result = detect_missing_data_as_failure(db, mrid)
        if result:
            detected.append(result)

    return detected

