from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.database import get_db
from app.api.dependencies.auth import get_current_user
from app.models.data_quality_issue import DataQualityIssue
from app.models.risk_assessment import RiskAssessment
from app.models.ground_truth import GroundTruth
from app.services.anomaly_engine import (
    detect_temporal_leakage, detect_wrong_denominator,
    detect_lifecycle_inconsistency, detect_intervention_precedes_trigger,
    detect_missing_data_as_failure,
)

router = APIRouter(prefix="/data-quality", tags=["Data Quality"])


@router.get("/issues")
def list_issues(
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    issue_type: Optional[str] = None, severity: Optional[str] = None,
    is_injected: Optional[bool] = None,
    db: Session = Depends(get_db), _=Depends(get_current_user),
):
    q = db.query(DataQualityIssue)
    if issue_type:
        q = q.filter(DataQualityIssue.issue_type == issue_type)
    if severity:
        q = q.filter(DataQualityIssue.severity == severity)
    if is_injected is not None:
        q = q.filter(DataQualityIssue.is_injected_anomaly == is_injected)
    total = q.count()
    items = q.order_by(DataQualityIssue.detected_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total, "page": page, "page_size": page_size,
        "items": [{
            "issue_id": i.issue_id, "issue_type": i.issue_type,
            "affected_entity": i.affected_entity, "affected_record_id": i.affected_record_id,
            "expected_behavior": i.expected_behavior, "observed_behavior": i.observed_behavior,
            "ground_truth_label": i.ground_truth_label, "detection_status": i.detection_status,
            "explanation": i.explanation, "severity": i.severity,
            "is_injected_anomaly": i.is_injected_anomaly, "detected_at": i.detected_at,
        } for i in items],
    }


@router.get("/summary")
def anomaly_summary(db: Session = Depends(get_db), _=Depends(get_current_user)):
    from sqlalchemy import func
    total = db.query(func.count(DataQualityIssue.issue_id)).scalar() or 0
    injected = db.query(func.count(DataQualityIssue.issue_id)).filter(DataQualityIssue.is_injected_anomaly == True).scalar() or 0
    by_type = db.query(DataQualityIssue.issue_type, func.count()).group_by(DataQualityIssue.issue_type).all()
    by_severity = db.query(DataQualityIssue.severity, func.count()).group_by(DataQualityIssue.severity).all()
    return {
        "total_issues": total,
        "injected_anomalies": injected,
        "by_type": [{"type": t, "count": c} for t, c in by_type],
        "by_severity": [{"severity": s, "count": c} for s, c in by_severity],
        "anomaly_descriptions": {
            "TEMPORAL_LEAKAGE": "Risk score used assessment data after its cutoff date",
            "WRONG_DENOMINATOR": "Attendance rate calculated using wrong denominator (approved absences not excluded)",
            "LIFECYCLE_INCONSISTENCY": "Withdrawn student has active enrollment or in-progress intervention",
            "INTERVENTION_PRECEDES_TRIGGER": "Intervention start_date precedes its trigger_date",
            "MISSING_DATA_AS_FAILURE": "NULL assessment marks treated as 0 in risk calculation",
        },
    }


@router.post("/run-checks")
def run_checks(db: Session = Depends(get_db), cu=Depends(get_current_user)):
    """Re-run all anomaly detectors against injected anomaly records and persist results."""
    from app.models.data_quality_issue import DataQualityIssue
    import uuid

    # Find injected anomaly records
    anomaly_risks = db.query(RiskAssessment).filter(RiskAssessment.is_anomaly == True).all()
    from app.models.intervention import Intervention
    from app.models.student import Student
    from app.models.enrollment import Enrollment

    detected = []

    for ra in anomaly_risks:
        result = detect_temporal_leakage(db, ra.risk_id)
        if result:
            detected.append(result)
        result = detect_missing_data_as_failure(db, ra.risk_id)
        if result:
            detected.append(result)

    # Check enrollments linked to anomaly risks
    for ra in anomaly_risks:
        if ra.enrollment_id:
            result = detect_wrong_denominator(db, ra.enrollment_id)
            if result:
                detected.append(result)

    # Check withdrawn students
    withdrawn = db.query(Student).filter(Student.current_status == "WITHDRAWN").all()
    for s in withdrawn:
        result = detect_lifecycle_inconsistency(db, s.student_id)
        if result:
            detected.append(result)

    # Check interventions with bad dates
    all_intervs = db.query(Intervention).all()
    for iv in all_intervs:
        result = detect_intervention_precedes_trigger(db, iv.intervention_id)
        if result:
            detected.append(result)

    # Persist newly detected issues
    persisted = []
    for d in detected:
        issue_id = f"DQI-{uuid.uuid4().hex[:12].upper()}"
        issue = DataQualityIssue(
            issue_id=issue_id,
            issue_type=d["issue_type"],
            affected_entity=d["affected_entity"],
            affected_record_id=d["affected_record_id"],
            expected_behavior=d["expected_behavior"],
            observed_behavior=d["observed_behavior"],
            ground_truth_label=d.get("ground_truth_label"),
            detection_status=d.get("detection_status", "DETECTED"),
            explanation=d["explanation"],
            severity=d.get("severity", "HIGH"),
            is_injected_anomaly=d.get("is_injected_anomaly", True),
        )
        db.add(issue)
        persisted.append({"issue_id": issue_id, "issue_type": d["issue_type"],
                           "affected_record_id": d["affected_record_id"]})
    db.commit()
    return {"checks_run": 5, "issues_found": len(detected), "persisted": persisted}

