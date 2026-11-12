# Validation Report

**Generated:** 2026-11-12  
**Dataset scale:** Full (5,000 students, seed 20261022)  
**Total checks:** 78  
**Result:** ✅ PASS (78/78)

---

## Summary

| Category | Checks | Passed | Failed |
|----------|--------|--------|--------|
| Required exports present | 3 | 3 | 0 |
| Primary key uniqueness | 14 | 14 | 0 |
| Foreign key integrity | 13 | 13 | 0 |
| Duplicate record prevention | 2 | 2 | 0 |
| Enum value validation | 11 | 11 | 0 |
| Date ordering | 6 | 6 | 0 |
| Attendance calculations | 2 | 2 | 0 |
| Assessment calculations | 2 | 2 | 0 |
| Lifecycle transitions | 2 | 2 | 0 |
| Anomaly detection | 11 | 11 | 0 |
| Ground truth separation | 1 | 1 | 0 |
| Derived score reconciliation | 2 | 2 | 0 |
| Temporal leakage prevention | 1 | 1 | 0 |
| **Total** | **78** | **78** | **0** |

---

## Anomaly Scenarios

All five required anomaly scenarios are **injected and detected**:

| # | Anomaly Type | Issue ID | Entity | Detection Method |
|---|-------------|----------|--------|-----------------|
| 1 | TEMPORAL_LEAKAGE | RISK-2026-ANOM-000001 | RiskAssessment | factor_scores contain future-dated assessment results |
| 2 | WRONG_DENOMINATOR | RISK-2026-ANOM-000002 | RiskAssessment | Attendance rate uses incorrect total (includes approved absences) |
| 3 | LIFECYCLE_INCONSISTENCY | STU-2026-000026 | Student | WITHDRAWN student has ACTIVE enrollment |
| 4 | INTERVENTION_PRECEDES_TRIGGER | INT-2026-ANOM-000001 | Intervention | start_date before trigger_date |
| 5 | MISSING_DATA_AS_FAILURE | RISK-2026-ANOM-000003 | RiskAssessment | NULL marks_obtained scored as 0 instead of excluded |

**Ground truth:** Labels stored in `data/ground_truth/ground_truth.csv` and `ground_truth.json`. These files are **never** used as input features to the risk engine.

---

## Business Rule Validation

### Attendance Rate Formula

```
rate = (PRESENT + LATE) / (total_sessions - APPROVED_ABSENCE)
```

- Approved absences are excluded from the denominator ✅
- Risk engine verified: test_anomaly2_valid_approved_absence_not_flagged PASSED

### Assessment Scoring

- NULL `marks_obtained` → excluded from average (data_available=False if no graded results) ✅
- Only assessments with `assessment_date ≤ cutoff_date` are used ✅

### Risk Weights

| Factor | Weight | Verified |
|--------|--------|---------|
| Attendance | 30% | ✅ |
| Academic Performance | 30% | ✅ |
| Performance Trend | 15% | ✅ |
| LMS Engagement | 15% | ✅ |
| Historical Support | 10% | ✅ |
| **Total** | **100%** | ✅ |

### Risk Categories

| Category | Range |
|----------|-------|
| LOW | 0–24 |
| MEDIUM | 25–49 |
| HIGH | 50–74 |
| CRITICAL | 75–100 |
| INSUFFICIENT_DATA | < 30% data completeness |

---

## Staff Count Discrepancy Resolution

- Generated CSV (`staff.csv`): 20 records (full scale)
- Database staff table: 20 generated + 4 default system users = 24 total
- **Resolution:** The 4 extra records (admin, instructor1, advisor1, support1) are legitimate default development accounts created by `seed_default_users()`. They are **not** data integrity errors.

---

## Data Quality Issues Table

The `data_quality_issues` table contains the 5 injected anomaly records:

| issue_id | issue_type | severity | detection_status |
|----------|------------|----------|-----------------|
| DQI-2026-000001 | TEMPORAL_LEAKAGE | HIGH | DETECTED |
| DQI-2026-000002 | WRONG_DENOMINATOR | HIGH | DETECTED |
| DQI-2026-000003 | LIFECYCLE_INCONSISTENCY | HIGH | DETECTED |
| DQI-2026-000004 | INTERVENTION_PRECEDES_TRIGGER | HIGH | DETECTED |
| DQI-2026-000005 | MISSING_DATA_AS_FAILURE | HIGH | DETECTED |

---

## Unit Test Coverage

| Test Module | Tests | Result |
|-------------|-------|--------|
| test_anomaly_engine.py | 6 | ✅ PASS |
| test_risk_engine.py | 10 | ✅ PASS |
| test_api.py | 26 | Running |

---

*Full machine-readable validation output: `data/validation/validation_report.json`*

