"""API endpoint tests."""
from datetime import date
import pytest


class TestAuthAPI:
    def test_login_success(self, client, auth_headers):
        # auth_headers fixture already tests login succeeds
        assert auth_headers is not None

    def test_login_wrong_password(self, client, db):
        resp = client.post("/api/auth/login", json={"username": "testadmin", "password": "wrongpass"})
        assert resp.status_code == 401

    def test_protected_endpoint_requires_auth(self, client):
        resp = client.get("/api/students")
        assert resp.status_code in (401, 403)

    def test_me_endpoint(self, client, auth_headers):
        resp = client.get("/api/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "username" in data
        assert "role" in data


class TestHealthAPI:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"


class TestStudentsAPI:
    def _create_student(self, client, auth_headers):
        payload = {
            "student_id": "STU-API-TEST-001",
            "first_name": "API",
            "last_name": "Test",
            "email": "api.test@student.yottaflex.edu",
            "enrollment_date": "2026-01-15",
            "academic_year": "2026",
            "department": "Computer Science",
            "program": "B.Sc Computer Science",
            "current_status": "ACTIVE",
        }
        return client.post("/api/students", json=payload, headers=auth_headers)

    def test_create_student(self, client, auth_headers):
        resp = self._create_student(client, auth_headers)
        assert resp.status_code == 201
        assert resp.json()["student_id"] == "STU-API-TEST-001"

    def test_get_student(self, client, auth_headers):
        self._create_student(client, auth_headers)
        resp = client.get("/api/students/STU-API-TEST-001", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["department"] == "Computer Science"

    def test_list_students_paginated(self, client, auth_headers):
        self._create_student(client, auth_headers)
        resp = client.get("/api/students?page=1&page_size=10", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "items" in data

    def test_get_nonexistent_student(self, client, auth_headers):
        resp = client.get("/api/students/STU-DOES-NOT-EXIST", headers=auth_headers)
        assert resp.status_code == 404

    def test_filter_by_department(self, client, auth_headers):
        self._create_student(client, auth_headers)
        resp = client.get("/api/students?department=Computer+Science", headers=auth_headers)
        assert resp.status_code == 200


class TestDashboardAPI:
    def test_dashboard_stats(self, client, auth_headers):
        resp = client.get("/api/dashboard/stats", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        required_keys = ["total_students", "total_courses", "students_at_risk",
                          "active_support_cases", "active_interventions"]
        for k in required_keys:
            assert k in data, f"Missing key: {k}"

    def test_risk_distribution(self, client, auth_headers):
        resp = client.get("/api/dashboard/risk-distribution", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_dashboard_lists_latest_risk_once_per_student(self, client, auth_headers, db):
        from app.models.risk_assessment import RiskAssessment
        from tests.helpers import _make_course, _make_enrollment, _make_student

        sid = "STU-DASH-001"
        _make_student(db, sid)
        for index in (1, 2):
            cid = f"CRS-DASH-{index}"
            eid = f"ENR-DASH-{index}"
            _make_course(db, cid)
            _make_enrollment(db, sid, cid, eid)
            db.add(RiskAssessment(
                risk_id=f"RISK-DASH-{index}", student_id=sid, enrollment_id=eid,
                cutoff_date=date(2026, index, 1), risk_score=70 + index,
                risk_category="HIGH", factor_scores={}, factor_weights={}, reasons=[],
                data_completeness=1.0, model_version="v1.0", is_anomaly=False,
            ))
        db.commit()

        response = client.get("/api/dashboard/at-risk-students", headers=auth_headers)

        assert response.status_code == 200
        items = [row for row in response.json() if row["student_id"] == sid]
        assert len(items) == 1
        assert items[0]["risk_score"] == 72

    def test_recent_interventions_route(self, client, auth_headers):
        response = client.get("/api/dashboard/recent-interventions", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestOutcomeEvaluationAPI:
    def test_evaluate_outcome_creates_and_reuses_evaluation(self, client, auth_headers, db):
        from tests.helpers import _make_course, _make_enrollment, _make_student

        sid, cid, eid = "STU-OUTCOME-001", "CRS-OUTCOME-001", "ENR-OUTCOME-001"
        _make_student(db, sid)
        _make_course(db, cid)
        _make_enrollment(db, sid, cid, eid)
        payload = {
            "student_id": sid,
            "enrollment_id": eid,
            "baseline_cutoff": "2026-07-01",
            "evaluation_period_start": "2026-07-02",
            "evaluation_period_end": "2026-12-15",
        }

        first = client.post("/api/outcomes/evaluate", json=payload, headers=auth_headers)
        second = client.post("/api/outcomes/evaluate", json=payload, headers=auth_headers)

        assert first.status_code == 201
        assert second.status_code == 201
        assert first.json()["outcome_id"] == second.json()["outcome_id"]
        assert first.json()["outcome_label"] == "STABLE"

    def test_evaluate_outcome_rejects_overlapping_period(self, client, auth_headers):
        response = client.post(
            "/api/outcomes/evaluate",
            json={
                "student_id": "STU-UNKNOWN",
                "enrollment_id": "ENR-UNKNOWN",
                "baseline_cutoff": "2026-07-01",
                "evaluation_period_start": "2026-07-01",
                "evaluation_period_end": "2026-12-15",
            },
            headers=auth_headers,
        )

        assert response.status_code == 422


class TestLifecycleAPIs:
    def test_reopening_support_case_clears_closed_date(self, client, auth_headers, db):
        from datetime import datetime
        from app.models.support_case import SupportCase
        from tests.helpers import _make_student

        sid = "STU-CASE-REOPEN"
        _make_student(db, sid)
        case = SupportCase(
            case_id="CASE-REOPEN-001", student_id=sid, case_type="ACADEMIC",
            description="Reopened case", priority="MEDIUM", case_status="CLOSED",
            opened_at=datetime(2026, 1, 15), closed_at=datetime(2026, 2, 1),
        )
        db.add(case)
        db.commit()

        response = client.post(
            f"/api/support-cases/{case.case_id}/transition",
            json={"to_status": "IN_PROGRESS"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        db.refresh(case)
        assert case.case_status == "IN_PROGRESS"
        assert case.closed_at is None

    def test_intervention_completion_sets_lifecycle_dates(self, client, auth_headers, db):
        from app.models.intervention import Intervention
        from tests.helpers import _make_course, _make_enrollment, _make_student

        sid, cid, eid = "STU-INT-001", "CRS-INT-001", "ENR-INT-001"
        _make_student(db, sid)
        _make_course(db, cid)
        _make_enrollment(db, sid, cid, eid)
        intervention = Intervention(
            intervention_id="INT-API-COMPLETE", student_id=sid, enrollment_id=eid,
            intervention_type="ACADEMIC_TUTORING", trigger_date=date(2026, 1, 15),
            intervention_status="IN_PROGRESS",
        )
        db.add(intervention)
        db.commit()

        response = client.post(
            f"/api/interventions/{intervention.intervention_id}/transition",
            json={"to_status": "COMPLETED"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        db.refresh(intervention)
        assert intervention.intervention_status == "COMPLETED"
        assert intervention.start_date == date(2026, 1, 15)
        assert intervention.completion_date is not None


class TestDataGenerationIDs:
    """Verify ID format correctness from generate_data."""
    def test_student_id_format(self):
        from scripts.generate_data import stu_id
        assert stu_id(1) == "STU-2026-000001"
        assert stu_id(999) == "STU-2026-000999"

    def test_course_id_format(self):
        from scripts.generate_data import crs_id
        assert crs_id(1) == "CRS-000001"

    def test_enrollment_id_format(self):
        from scripts.generate_data import enr_id
        assert enr_id("STU-2026-000001", "CRS-000001") == "ENR-STU-2026-000001-CRS-000001"

    def test_assessment_id_format(self):
        from scripts.generate_data import asm_id
        assert asm_id(1) == "ASM-000001"

    def test_lms_id_format(self):
        from scripts.generate_data import lms_id
        assert lms_id(1) == "LMS-2026-000001"

    def test_case_id_format(self):
        from scripts.generate_data import case_id
        assert case_id(1) == "CASE-2026-000001"

    def test_intervention_id_format(self):
        from scripts.generate_data import int_id
        assert int_id(1) == "INT-2026-000001"

    def test_outcome_id_format(self):
        from scripts.generate_data import out_id
        assert out_id(1) == "OUT-2026-000001"
