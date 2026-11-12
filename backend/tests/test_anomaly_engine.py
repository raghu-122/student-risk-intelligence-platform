"""Tests for all 5 anomaly detection scenarios."""
import pytest
from datetime import date
from tests.helpers import _make_student, _make_course, _make_enrollment, _make_attendance


class TestAnomalyDetection:

    def test_anomaly1_temporal_leakage_detected(self, db):
        """Anomaly 1: Risk assessment that used future assessment data must be detected."""
        from app.models.risk_assessment import RiskAssessment
        from app.models.assessment import Assessment
        from app.models.assessment_result import AssessmentResult
        from app.services.anomaly_engine import detect_temporal_leakage

        sid = "STU-AN1"; cid = "CRS-AN1"; eid = "ENR-AN1"
        _make_student(db, sid); _make_course(db, cid); _make_enrollment(db, sid, cid, eid)

        # Injected anomaly risk with cutoff 2026-06-01
        ra = RiskAssessment(risk_id="RISK-AN1-001", student_id=sid, enrollment_id=eid,
                             cutoff_date=date(2026, 6, 1), risk_score=72.5, risk_category="HIGH",
                             factor_scores={}, factor_weights={}, reasons=[],
                             data_completeness=0.8, model_version="v0.9-BUGGY", is_anomaly=True)
        db.add(ra)

        # Assessment dated AFTER cutoff (2026-06-15) — this is the leakage
        db.add(Assessment(assessment_id="ASM-AN1-POST", course_id=cid,
                           assessment_name="Future Exam", assessment_type="FINAL",
                           maximum_marks=100, weightage=0.4, assessment_date=date(2026, 7, 15)))
        db.add(AssessmentResult(result_id="RES-AN1-POST-ENR-AN1",
                                 assessment_id="ASM-AN1-POST", enrollment_id=eid,
                                 marks_obtained=90, percentage=90, submission_status="SUBMITTED"))
        db.commit()

        result = detect_temporal_leakage(db, "RISK-AN1-001")
        assert result is not None, "Temporal leakage should be detected"
        assert result["issue_type"] == "TEMPORAL_LEAKAGE"
        assert result["detection_status"] == "DETECTED"

    def test_anomaly2_wrong_denominator_detected(self, db):
        """Anomaly 2: Attendance rate computed with wrong denominator."""
        from datetime import timedelta
        from app.models.risk_assessment import RiskAssessment
        from app.services.anomaly_engine import detect_wrong_denominator

        sid = "STU-AN2"
        cid = "CRS-AN2"
        eid = "ENR-AN2"
        _make_student(db, sid)
        _make_course(db, cid)
        _make_enrollment(db, sid, cid, eid)
        base = date(2026, 1, 15)
        # 7 PRESENT + 3 APPROVED_ABSENCE = 10 total
        # Correct rate: 7/7 = 100%; Wrong rate: 7/10 = 70%  → delta = 30pp > 1pp threshold
        records = [(base + timedelta(weeks=i), "PRESENT") for i in range(7)]
        records += [(date(2026, 9, 1) + timedelta(weeks=i), "APPROVED_ABSENCE") for i in range(3)]
        _make_attendance(db, eid, records)

        db.add(RiskAssessment(
            risk_id="RISK-AN2-001", student_id=sid, enrollment_id=eid,
            cutoff_date=date(2026, 12, 31), risk_score=30.0, risk_category="MEDIUM",
            factor_scores={"attendance": 30.0}, factor_weights={}, reasons=[],
            data_completeness=1.0, model_version="v0.9-BUGGY", is_anomaly=True,
        ))
        db.commit()

        result = detect_wrong_denominator(db, eid)
        assert result is not None, "The recorded incorrect attendance factor should be detected"
        assert result["issue_type"] == "WRONG_DENOMINATOR"
        assert "approved absences excluded" in result["expected_behavior"]

    def test_anomaly2_valid_approved_absence_not_flagged(self, db):
        """Approved absences alone are valid and do not establish a calculation error."""
        from datetime import timedelta
        from app.services.anomaly_engine import detect_wrong_denominator

        eid = "ENR-AN2-VALID"
        base = date(2026, 1, 15)
        records = [(base + timedelta(weeks=i), "PRESENT") for i in range(7)]
        records += [(date(2026, 9, 1) + timedelta(weeks=i), "APPROVED_ABSENCE") for i in range(3)]
        _make_attendance(db, eid, records)

        assert detect_wrong_denominator(db, eid) is None

    def test_anomaly3_lifecycle_inconsistency_detected(self, db):
        """Anomaly 3: Withdrawn student has active enrollment."""
        from app.models.student import Student
        from app.models.enrollment import Enrollment
        from app.services.anomaly_engine import detect_lifecycle_inconsistency

        sid = "STU-WD-AN3"
        db.add(Student(student_id=sid, first_name="With", last_name="Drawn",
                        email="wd@test.com", enrollment_date=date(2026,1,15),
                        academic_year="2026", department="CS",
                        program="B.Sc CS", current_status="WITHDRAWN"))
        db.add(Enrollment(enrollment_id=f"ENR-WD-{sid}", student_id=sid,
                           course_id="CRS-NODATA",  # reuse existing
                           enrollment_date=date(2026,1,15),
                           effective_from=date(2026,1,15),
                           enrollment_status="ACTIVE"))  # violation!
        db.commit()

        result = detect_lifecycle_inconsistency(db, sid)
        assert result is not None, "Lifecycle inconsistency should be detected"
        assert result["issue_type"] == "LIFECYCLE_INCONSISTENCY"

    def test_anomaly4_intervention_precedes_trigger_detected(self, db):
        """Anomaly 4: Intervention start_date < trigger_date."""
        from app.models.student import Student
        from app.models.intervention import Intervention
        from app.services.anomaly_engine import detect_intervention_precedes_trigger

        sid = "STU-IV-AN4"
        if not db.query(Student).filter(Student.student_id == sid).first():
            db.add(Student(student_id=sid, first_name="IV", last_name="Test",
                            email="iv4@test.com", enrollment_date=date(2026,1,15),
                            academic_year="2026", department="CS", program="B.Sc CS",
                            current_status="ACTIVE"))
        iid = "INT-AN4-001"
        db.add(Intervention(intervention_id=iid, student_id=sid,
                             intervention_type="ACADEMIC_TUTORING",
                             trigger_date=date(2026, 7, 10),   # triggered on July 10
                             start_date=date(2026, 7, 1),       # started on July 1 — BEFORE trigger!
                             due_date=date(2026, 8, 1),
                             intervention_status="IN_PROGRESS"))
        db.commit()

        result = detect_intervention_precedes_trigger(db, iid)
        assert result is not None, "Chronological violation should be detected"
        assert result["issue_type"] == "INTERVENTION_PRECEDES_TRIGGER"

    def test_anomaly5_missing_data_as_failure_detected(self, db):
        """Anomaly 5: NULL marks treated as 0, inflating academic risk score."""
        from app.models.risk_assessment import RiskAssessment
        from app.models.assessment_result import AssessmentResult
        from app.models.assessment import Assessment
        from app.services.anomaly_engine import detect_missing_data_as_failure

        sid = "STU-MD-AN5"; cid = "CRS-MD-AN5"; eid = "ENR-MD-AN5"
        _make_student(db, sid); _make_course(db, cid); _make_enrollment(db, sid, cid, eid)

        # NULL marks (should be excluded, not scored as 0)
        db.add(Assessment(assessment_id="ASM-MD-001", course_id=cid,
                           assessment_name="Quiz 1", assessment_type="QUIZ",
                           maximum_marks=100, weightage=1.0, assessment_date=date(2026,4,1)))
        db.add(AssessmentResult(result_id="RES-MD-001-ENR-MD-AN5",
                                 assessment_id="ASM-MD-001", enrollment_id=eid,
                                 marks_obtained=None, percentage=None,  # NULL = missing
                                 submission_status="MISSING"))

        # Risk assessment with inflated score (NULL treated as 0)
        ra = RiskAssessment(
            risk_id="RISK-MD-AN5-001", student_id=sid, enrollment_id=eid,
            cutoff_date=date(2026,7,1), risk_score=78.0, risk_category="CRITICAL",
            factor_scores={"academic_performance": 78.0},  # inflated
            factor_weights={}, reasons=[], data_completeness=0.6,
            model_version="v0.8-BUGGY", is_anomaly=True,
        )
        db.add(ra); db.commit()

        result = detect_missing_data_as_failure(db, "RISK-MD-AN5-001")
        assert result is not None, "Missing-data-as-failure anomaly should be detected"
        assert result["issue_type"] == "MISSING_DATA_AS_FAILURE"
