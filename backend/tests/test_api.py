"""API endpoint tests."""
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

