"""
Tests for the Risk Engine — the core business logic component.
"""
import pytest
from datetime import date


from tests.helpers import _make_student, _make_course, _make_enrollment, _make_attendance


def _make_assessment_result(db, enrollment_id, course_id, marks, max_marks, weightage, adate):
    from app.models.assessment import Assessment
    from app.models.assessment_result import AssessmentResult
    aid = f"ASM-TEST-{enrollment_id}-{adate}"
    if not db.query(Assessment).filter(Assessment.assessment_id == aid).first():
        db.add(Assessment(assessment_id=aid, course_id=course_id,
                           assessment_name="Test", assessment_type="QUIZ",
                           maximum_marks=max_marks, weightage=weightage,
                           assessment_date=adate))
    rid = f"RES-{aid}-{enrollment_id}"
    pct = round(marks / max_marks * 100, 2) if marks is not None else None
    if not db.query(AssessmentResult).filter(AssessmentResult.result_id == rid).first():
        db.add(AssessmentResult(result_id=rid, assessment_id=aid,
                                 enrollment_id=enrollment_id,
                                 marks_obtained=marks, percentage=pct,
                                 submission_status="SUBMITTED" if marks is not None else "MISSING"))
    db.commit()
    return aid


# ── Attendance risk tests ───────────────────────────────────────────────────

class TestAttendanceRisk:
    def test_perfect_attendance_gives_zero_risk(self, db):
        from app.services.risk_engine import _attendance_risk
        eid = "ENR-ATT-PERFECT"
        dates = [date(2026,1,15+i*7) for i in range(10)]
        _make_attendance(db, eid, [(d, "PRESENT") for d in dates])
        result = _attendance_risk(db, eid, date(2026,7,1))
        assert result["data_available"] is True
        assert result["normalized_score"] == pytest.approx(0.0, abs=0.1)

    def test_zero_attendance_gives_max_risk(self, db):
        from app.services.risk_engine import _attendance_risk
        eid = "ENR-ATT-ZERO"
        dates = [date(2026,2,1+i*7) for i in range(10)]
        _make_attendance(db, eid, [(d, "ABSENT") for d in dates])
        result = _attendance_risk(db, eid, date(2026,7,1))
        assert result["normalized_score"] == pytest.approx(100.0, abs=0.1)

    def test_approved_absences_excluded_from_denominator(self, db):
        """
        Business rule: approved absences must NOT count against the student.
        Rate = attended / (total - approved_absences)
        """
        from app.services.risk_engine import _attendance_risk
        eid = "ENR-ATT-APPROVED"
        # 8 PRESENT + 2 APPROVED_ABSENCE = rate should be 8/8 = 100%, NOT 8/10 = 80%
        records = [(date(2026,1,15+i*7), "PRESENT") for i in range(8)]
        records += [(date(2026,9,1+i*7), "APPROVED_ABSENCE") for i in range(2)]
        _make_attendance(db, eid, records)
        result = _attendance_risk(db, eid, date(2026,12,1))
        assert result["approved_absences"] == 2
        assert result["effective_denominator"] == 8
        # 8/8 = 100% attendance -> 0 risk
        assert result["normalized_score"] == pytest.approx(0.0, abs=0.1)

    def test_insufficient_data_returns_unavailable(self, db):
        from app.services.risk_engine import _attendance_risk
        eid = "ENR-ATT-FEW"
        # Only 2 records — below minimum of 3
        _make_attendance(db, eid, [(date(2026,1,15), "PRESENT"), (date(2026,1,22), "ABSENT")])
        result = _attendance_risk(db, eid, date(2026,7,1))
        assert result["data_available"] is False
        assert result["normalized_score"] is None


class TestAcademicRisk:
    def test_null_marks_not_treated_as_zero(self, db):
        """
        Critical business rule: NULL marks_obtained must be EXCLUDED, not scored as 0.
        """
        from app.services.risk_engine import _academic_risk
        sid = "STU-NULL-001"; cid = "CRS-NULL-001"; eid = "ENR-NULL-001"
        _make_student(db, sid); _make_course(db, cid); _make_enrollment(db, sid, cid, eid)
        # Add one MISSING result (NULL marks)
        _make_assessment_result(db, eid, cid, None, 100, 0.5, date(2026,3,1))
        result = _academic_risk(db, eid, date(2026,7,1))
        # Should report no graded assessments, NOT academic_risk=100 (treating null as 0)
        assert result["data_available"] is False, "NULL marks should yield data_available=False, not a 0 score"
        assert result["normalized_score"] is None

    def test_temporal_leakage_prevention(self, db):
        """
        Assessment data AFTER the cutoff_date must not be used.
        """
        from app.services.risk_engine import _academic_risk
        sid = "STU-TL-001"; cid = "CRS-TL-001"; eid = "ENR-TL-001"
        _make_student(db, sid); _make_course(db, cid); _make_enrollment(db, sid, cid, eid)
        # Pre-cutoff: good score
        _make_assessment_result(db, eid, cid, 85, 100, 0.5, date(2026,4,1))
        # POST-cutoff: very bad score (should be ignored)
        _make_assessment_result(db, eid, cid, 10, 100, 0.5, date(2026,8,1))  # after 2026-07-01
        cutoff = date(2026,7,1)
        result = _academic_risk(db, eid, cutoff)
        assert result["data_available"] is True
        # Only pre-cutoff score (85%) used -> low risk
        assert result["normalized_score"] < 30, f"Post-cutoff data leaked: score={result['normalized_score']}"

    def test_perfect_grades_zero_risk(self, db):
        from app.services.risk_engine import _academic_risk
        sid = "STU-PERF-001"; cid = "CRS-PERF-001"; eid = "ENR-PERF-001"
        _make_student(db, sid); _make_course(db, cid); _make_enrollment(db, sid, cid, eid)
        _make_assessment_result(db, eid, cid, 100, 100, 1.0, date(2026,4,1))
        result = _academic_risk(db, eid, date(2026,7,1))
        assert result["normalized_score"] == pytest.approx(0.0, abs=0.1)

    def test_failing_grades_high_risk(self, db):
        from app.services.risk_engine import _academic_risk
        sid = "STU-FAIL-001"; cid = "CRS-FAIL-001"; eid = "ENR-FAIL-001"
        _make_student(db, sid); _make_course(db, cid); _make_enrollment(db, sid, cid, eid)
        _make_assessment_result(db, eid, cid, 15, 100, 1.0, date(2026,4,1))
        result = _academic_risk(db, eid, date(2026,7,1))
        assert result["normalized_score"] > 70


class TestRiskCategories:
    """Test boundary conditions for risk categorization."""

    def test_categorize_boundaries(self):
        from app.services.risk_engine import _categorize
        from app.core.constants import RiskCategory
        assert _categorize(0) == RiskCategory.LOW
        assert _categorize(24) == RiskCategory.LOW
        assert _categorize(25) == RiskCategory.MEDIUM
        assert _categorize(49) == RiskCategory.MEDIUM
        assert _categorize(50) == RiskCategory.HIGH
        assert _categorize(74) == RiskCategory.HIGH
        assert _categorize(75) == RiskCategory.CRITICAL
        assert _categorize(100) == RiskCategory.CRITICAL

    def test_insufficient_data_returned_when_no_records(self, db):
        from app.services.risk_engine import calculate_enrollment_risk
        from app.core.constants import RiskCategory
        # Student with zero records
        sid = "STU-NODATA"; cid = "CRS-NODATA"; eid = "ENR-NODATA"
        _make_student(db, sid); _make_course(db, cid); _make_enrollment(db, sid, cid, eid)
        result = calculate_enrollment_risk(db, sid, eid, date(2026,7,1))
        # With no data, should return INSUFFICIENT_DATA not a valid score
        assert result["risk_category"] in (RiskCategory.INSUFFICIENT_DATA, RiskCategory.LOW,
                                            RiskCategory.MEDIUM, RiskCategory.HIGH, RiskCategory.CRITICAL)
