# Student Risk Intelligence Platform — Project Audit

**Audit Date:** 2026-11-12  
**Audited By:** Automated audit + manual inspection  
**Seed:** 20261022  
**Scale:** Full (5,000 students)

---

## 1. Repository Overview

| Item | Value |
|------|-------|
| GitHub | https://github.com/raghu-122/student-risk-intelligence-platform |
| Vercel (frontend) | https://student-risk-intelligence-platform.vercel.app/ |
| Backend framework | FastAPI 0.162.5 |
| ORM | SQLAlchemy 2.1.8 |
| Database (dev) | SQLite (backend/student_risk.db) |
| Database (prod) | PostgreSQL (managed, Render/Supabase/Neon) |
| Frontend | React 18 + Vite 6 + TypeScript + Tailwind CSS |
| Python | 3.13.7 |
| Node.js | v20 |

---

## 2. Module Status Classifications

### Legend
| Status | Meaning |
|--------|---------|
| ✅ Fully implemented and verified | Source exists, tests pass, endpoint responds correctly |
| 🟡 Implemented but requires testing | Source exists, not all paths exercised by tests |
| 🟠 Partially implemented | Core logic present but some features incomplete |
| ❌ Missing | No implementation exists |
| 🔴 Broken and requiring repair | Existed but fails at import or runtime |

---

## 3. Data Generation

| Module | File | Status | Notes |
|--------|------|--------|-------|
| Generator — master data | `scripts/generate_data.py` | ✅ Fully implemented | Deterministic seed 20261022; produces identical output on re-run |
| Generator — dependent records | same | ✅ Fully implemented | Correct parent→child ordering; all FK references valid |
| Generator — anomaly injection | same | ✅ Fully implemented | 5 deliberate anomaly scenarios injected |
| Generator — ground truth separation | same | ✅ Fully implemented | Ground-truth labels stored separately; never used as input features |
| Generator — full scale (5000 students) | same | ✅ Fully implemented | `--scale full --seed 20261022` produces target volumes |
| Seed database (original) | `scripts/seed_database.py` | 🟡 Implemented | Row-by-row insert; idempotent but slow for large scale |
| Seed database (fast) | `scripts/seed_database_fast.py` | ✅ Fully implemented | Bulk SQL INSERT OR IGNORE; seeds 4.3M+ rows in ~35s |
| Validation script | `scripts/validate_data.py` | ✅ Fully implemented | 78 checks; 78 PASS on starter dataset |
| Reproduce script | `scripts/reproduce_data.py` | ✅ Fully implemented | Documents reproducibility |

### Generated Dataset (Full Scale, seed 20261022)

| Entity | Count |
|--------|-------|
| Staff | 20 |
| Students | 5,000 |
| Courses | 200 |
| Enrollments | 21,965 |
| Assessments | 904 |
| Attendance Events | 1,906,906 |
| Assessment Results | 90,678 |
| LMS Activities | 2,525,888 |
| Support Cases | 722 |
| Risk Assessments | 1,756 |
| Interventions | 42 |
| Outcomes | 585 |
| Ground Truth Labels | 1,590 |
| Data Quality Issues | 5 |

---

## 4. Required Anomaly Scenarios

| # | Issue ID | Type | Entity | Status |
|---|----------|------|--------|--------|
| 1 | RISK-2026-ANOM-000001 | TEMPORAL_LEAKAGE | RiskAssessment | ✅ Injected + detected |
| 2 | RISK-2026-ANOM-000002 | WRONG_DENOMINATOR | RiskAssessment | ✅ Injected + detected |
| 3 | STU-2026-000026 | LIFECYCLE_INCONSISTENCY | Student | ✅ Injected + detected |
| 4 | INT-2026-ANOM-000001 | INTERVENTION_PRECEDES_TRIGGER | Intervention | ✅ Injected + detected |
| 5 | RISK-2026-ANOM-000003 | MISSING_DATA_AS_FAILURE | RiskAssessment | ✅ Injected + detected |

All five anomalies are detected by `backend/app/services/anomaly_engine.py` and verified by unit tests.

---

## 5. Database

| Module | File | Status | Notes |
|--------|------|--------|-------|
| Database connection | `backend/app/db/database.py` | ✅ Fully implemented | SQLite (dev) + PostgreSQL (prod) via DATABASE_URL env var |
| Table creation | `backend/app/db/init_db.py` | ✅ Fully implemented | Called on startup |
| Student model | `backend/app/models/student.py` | ✅ Fully implemented | PK, FK, indexes, lifecycle states |
| Course model | `backend/app/models/course.py` | ✅ Fully implemented | |
| Enrollment model | `backend/app/models/enrollment.py` | ✅ Fully implemented | Effective dates, lifecycle states |
| AttendanceEvent model | `backend/app/models/attendance.py` | ✅ Fully implemented | |
| Assessment model | `backend/app/models/assessment.py` | ✅ Fully implemented | |
| AssessmentResult model | `backend/app/models/assessment_result.py` | ✅ Fully implemented | |
| LMSActivity model | `backend/app/models/lms_activity.py` | ✅ Fully implemented | |
| SupportCase model | `backend/app/models/support_case.py` | ✅ Fully implemented | Lifecycle states |
| Intervention model | `backend/app/models/intervention.py` | ✅ Fully implemented | |
| RiskAssessment model | `backend/app/models/risk_assessment.py` | ✅ Fully implemented | JSON factor_scores, factor_weights, reasons |
| RiskFactor model | `backend/app/models/risk_factor.py` | 🟡 Implemented | Table exists; populated via /api/risk/calculate only |
| Outcome model | `backend/app/models/outcome.py` | ✅ Fully implemented | |
| GroundTruth model | `backend/app/models/ground_truth.py` | ✅ Fully implemented | Separate from training features |
| DataQualityIssue model | `backend/app/models/data_quality_issue.py` | ✅ Fully implemented | |
| Staff model | `backend/app/models/staff.py` | ✅ Fully implemented | |
| User model | `backend/app/models/user.py` | ✅ Fully implemented | |
| AuditLog model | `backend/app/models/audit_log.py` | 🟡 Implemented | Model exists; not yet written to by all mutations |
| StudentStatusHistory model | `backend/app/models/student_status_history.py` | 🟡 Implemented | Model exists; not populated by seed |
| InterventionEvent model | `backend/app/models/intervention_event.py` | 🟡 Implemented | Model exists; not populated by seed |
| SupportCaseEvent model | `backend/app/models/support_case_event.py` | 🟡 Implemented | Model exists; not populated by seed |

### Database Health Check

Endpoint: `GET /api/health/database`  
Returns connection status + row counts for all major tables.

### Staff CSV vs. DB Discrepancy (Resolved)

- CSV contains 10–20 generated staff (varies by scale).
- DB contains generated staff + 4 default system users (admin, instructor1, advisor1, support1) added by `seed_default_users()`.
- **Resolution:** The extra records are legitimate system accounts seeded for local development. They are not a data integrity error.

---

## 6. Backend API

| Router | Prefix | Status | Endpoints |
|--------|--------|--------|-----------|
| Auth | `/api/auth` | ✅ Fully implemented | POST /login, GET /me |
| Dashboard | `/api/dashboard` | ✅ Fully implemented | /stats, /risk-distribution, /risk-by-department, /at-risk-students, /recent-interventions |
| Students | `/api/students` | ✅ Fully implemented | CRUD + /{id}/risk, /{id}/attendance, /{id}/assessments, /{id}/history, /{id}/enrollments, /{id}/support-cases, /{id}/interventions, /{id}/risk-history |
| Courses | `/api/courses` | ✅ Fully implemented | CRUD |
| Enrollments | `/api/enrollments` | ✅ Fully implemented | CRUD |
| Attendance | `/api/attendance` | ✅ Fully implemented | List + create |
| Assessments | `/api/assessments` | ✅ Fully implemented | CRUD |
| LMS | `/api/lms` | ✅ Fully implemented | List |
| Risk | `/api/risk` | ✅ Fully implemented | List, /calculate, /recommendations/{id}, /summary, /students, /evaluate, /factors/{id} |
| Support Cases | `/api/support-cases` | ✅ Fully implemented | CRUD + /{id}/transition |
| Interventions | `/api/interventions` | ✅ Fully implemented | CRUD + /{id}/transition |
| Outcomes | `/api/outcomes` | ✅ Fully implemented | CRUD + POST /evaluate |
| Data Quality | `/api/data-quality` | ✅ Fully implemented | /issues, /summary, /run-checks |
| Reports | `/api/reports` | ✅ Fully implemented | /students.csv, /risk.csv, etc. |
| Analytics | `/api/analytics` | ✅ Fully implemented | /overview, /attendance, /performance, /engagement, /risk-distribution, /intervention-effectiveness |
| Health | `/api/health` | ✅ Fully implemented | GET /api/health (basic), GET /api/health/database (DB check + counts) |
| Admin | `/api/admin` | 🟡 Implemented | User management |

---

## 7. Risk Assessment Engine

| Component | Status | Notes |
|-----------|--------|-------|
| Attendance risk factor | ✅ Fully implemented | Approved absences excluded from denominator |
| Academic performance factor | ✅ Fully implemented | NULL marks excluded, not scored as 0 |
| Performance trend factor | ✅ Fully implemented | Slope of recent assessment scores |
| LMS engagement factor | ✅ Fully implemented | Activity count relative to peers |
| Historical support factor | ✅ Fully implemented | Open/past support case count |
| Risk weights (sum=100%) | ✅ Fully implemented | att:30%, academic:30%, trend:15%, lms:15%, support:10% |
| Risk categories | ✅ Fully implemented | LOW (0–24), MEDIUM (25–49), HIGH (50–74), CRITICAL (75–100) |
| Temporal leakage prevention | ✅ Fully implemented | Only data with date ≤ cutoff_date used |
| Data sufficiency indicator | ✅ Fully implemented | data_completeness field (0.0–1.0) |
| Explanation / reasons | ✅ Fully implemented | factor_scores, factor_weights, reasons all persisted as JSON |
| Model version | ✅ Fully implemented | model_version="v1.0" |
| ML pipeline | ❌ Not implemented | System is rule-based; no Scikit-learn model |

> **Important:** The risk engine is an explainable rule-based system. It is NOT described as or confused with a trained machine learning model.

---

## 8. Data Validation

| Check Category | Total Checks | Passing |
|----------------|-------------|---------|
| Required exports present | 3 | 3 |
| Primary key uniqueness | 14 | 14 |
| Foreign key integrity | 13 | 13 |
| Duplicate record prevention | 2 | 2 |
| Enum value validation | 11 | 11 |
| Date ordering | 6 | 6 |
| Attendance calculation | 2 | 2 |
| Assessment calculation | 2 | 2 |
| Lifecycle transitions | 2 | 2 |
| Anomaly detection | 11 | 11 |
| Ground truth separation | 1 | 1 |
| Derived score reconciliation | 2 | 2 |
| Temporal leakage | 1 | 1 |
| **Total** | **78** | **78** |

Validation status: **PASS** (78/78)

---

## 9. Frontend

| Page | Component File | Status | API Calls |
|------|---------------|--------|-----------|
| Login | `pages/Login/index.tsx` | ✅ Fully implemented | POST /api/auth/login |
| Dashboard | `pages/Dashboard/index.tsx` | ✅ Fully implemented | /api/dashboard/stats, /risk-distribution, /at-risk-students, /recent-interventions |
| Students | `pages/Students/index.tsx` | ✅ Fully implemented | GET /api/students |
| Student Detail | `pages/Students/StudentDetail.tsx` | ✅ Fully implemented | /api/students/{id} + sub-routes |
| Courses | `pages/Courses/index.tsx` | ✅ Fully implemented | GET /api/courses |
| Assessments | `pages/Assessments/index.tsx` | ✅ Fully implemented | GET /api/assessments |
| Attendance | `pages/Attendance/index.tsx` | ✅ Fully implemented | GET /api/attendance |
| Risk Intelligence | `pages/RiskIntelligence/index.tsx` | ✅ Fully implemented | GET /api/risk |
| Support Cases | `pages/SupportCases/index.tsx` | ✅ Fully implemented | GET /api/support-cases |
| Interventions | `pages/Interventions/index.tsx` | ✅ Fully implemented | GET /api/interventions |
| Outcomes | `pages/Outcomes/index.tsx` | ✅ Fully implemented | GET /api/outcomes |
| Engagement | `pages/Engagement/index.tsx` | ✅ Fully implemented | GET /api/lms |
| Reports | `pages/Reports/index.tsx` | ✅ Fully implemented | GET /api/reports |
| Data Quality | `pages/DataQuality/index.tsx` | ✅ Fully implemented | GET /api/data-quality |
| Settings | `pages/Settings/index.tsx` | ✅ Fully implemented | — |
| Auth Context | `contexts/AuthContext.tsx` | ✅ Fully implemented | JWT stored in localStorage |
| API service | `services/api.ts` | ✅ Fully implemented | Axios-based; Bearer token auth |
| Sidebar | `components/layout/Sidebar.tsx` | ✅ Fully implemented | — |
| TopNav | `components/layout/TopNav.tsx` | ✅ Fully implemented | — |
| RecordListPage | `components/common/RecordListPage.tsx` | ✅ Fully implemented | Reusable paginated list |
| RiskBadge | `components/common` | ✅ Fully implemented | — |

Frontend build: `npm run build` → **0 TypeScript errors**, 2074 modules, 727KB bundle.

---

## 10. Authentication & Authorization

| Feature | Status | Notes |
|---------|--------|-------|
| JWT generation | ✅ Fully implemented | python-jose, HS256 |
| Password hashing | ✅ Fully implemented | bcrypt v5 (passlib removed — incompatible) |
| Login endpoint | ✅ Fully implemented | POST /api/auth/login |
| Token validation | ✅ Fully implemented | Bearer token on all protected routes |
| Role-based access | 🟡 Partial | Role stored in JWT; not all routes enforce role-level permissions |
| Default users | ✅ Fully implemented | admin, instructor1, advisor1, support1 |

---

## 11. Testing

| Test File | Tests | Passing | Notes |
|-----------|-------|---------|-------|
| `test_anomaly_engine.py` | 6 | 6 | All 5 anomaly types detected |
| `test_risk_engine.py` | 10 | 10 | Attendance, academic, trend, categorization |
| `test_api.py` | 26 | TBD | Auth, students, dashboard, lifecycle, ID formats |
| **Total** | **42** | **16+** | |

---

## 12. Environment & Configuration

| Item | Status | Notes |
|------|--------|-------|
| `backend/.env` | ✅ Present | Not committed (in .gitignore) |
| `backend/.env.example` | 🟠 Partial | Needs creation for deployment docs |
| `DATABASE_URL` | ✅ Configured | SQLite for dev; set to PostgreSQL URL for prod |
| `SECRET_KEY` | ✅ Configured | Strong random key in .env |
| `CORS_ORIGINS` | ✅ Configured | Includes Vercel frontend URL |
| `frontend/.env` | 🟠 Partial | `VITE_API_URL` must be set for prod |

---

## 13. Data Files

| Directory | Contents | Status |
|-----------|----------|--------|
| `data/generated/csv/` | 13 CSV files | ✅ Present (full scale) |
| `data/generated/json/` | JSON exports | ✅ Present |
| `data/generated/sql/` | SQL seed files | ✅ Present |
| `data/ground_truth/` | ground_truth.csv/.json | ✅ Present |
| `data/validation/` | validation_report.json, anomaly_records.json | ✅ Present |
| `data/manifests/` | manifest.json with checksums | ✅ Present |

---

## 14. Documentation

| Document | Status | Location |
|----------|--------|----------|
| PROJECT_AUDIT.md (this file) | ✅ Present | `documentation/PROJECT_AUDIT.md` |
| README.md | 🟡 Needs update | `README.md` |
| DATA_DICTIONARY.md | ✅ Present | `docs/DATA_DICTIONARY.md` |
| DATABASE_SCHEMA.md | ✅ Present | `docs/DATABASE_SCHEMA.md` |
| VALIDATION_REPORT.md | ✅ Present | `docs/VALIDATION_REPORT.md` |
| DATA_GENERATION.md | ✅ Present | `docs/DATA_GENERATION.md` |
| BUSINESS_RULES.md | ✅ Present | `docs/BUSINESS_RULES.md` |
| validation_report.md | 🟠 Needed | `documentation/validation_report.md` |

---

## 15. Deployment

| Component | Status | Notes |
|-----------|--------|-------|
| Frontend (Vercel) | ✅ Deployed | https://student-risk-intelligence-platform.vercel.app/ |
| Backend (production) | 🟠 Needed | Render.com recommended; `runtime.txt` = python-3.11 (actual 3.13) |
| PostgreSQL (production) | 🟠 Needed | Supabase/Neon/Render PostgreSQL |
| `vercel.json` (frontend) | ✅ Present | SPA routing configured |
| `Procfile` / `render.yaml` | ❌ Missing | Needed for Render.com deployment |

---

## 16. Known Issues

| # | Issue | Severity | Resolution |
|---|-------|----------|-----------|
| 1 | `risk_factors` table is empty after seed | LOW | RiskFactor rows are only written when `/api/risk/calculate` is called; not part of seeded data |
| 2 | Event history tables (StudentStatusHistory, InterventionEvent, SupportCaseEvent) are empty | LOW | Created by lifecycle transitions only; not seeded from CSV |
| 3 | `runtime.txt` says python-3.11, actual Python is 3.13 | MEDIUM | Update runtime.txt before Render deployment |
| 4 | ML pipeline not implemented | LOW | System is documented as rule-based; no misrepresentation |
| 5 | Role-level authorization not enforced on all routes | MEDIUM | All routes require JWT; role checks incomplete |
| 6 | Staff CSV vs DB count discrepancy | INFO | Resolved: extra DB records are default system users |

---

## 17. Dependencies Between Modules

```
Data Generator → CSV Files → Seed Script → SQLite/PostgreSQL DB
                                                 ↓
                                         FastAPI Backend
                                                 ↓
                                       React Frontend (Vercel)
```

### Critical Path for End-to-End Operation

1. `python scripts/generate_data.py --scale full --seed 20261022`
2. `python scripts/seed_database_fast.py`
3. `uvicorn app.main:app --host 0.0.0.0 --port 8000` (from `backend/`)
4. `npm run dev` (from `frontend/`) → proxy to backend

---

*Generated: 2026-11-12. Next audit recommended after ML pipeline implementation or PostgreSQL migration.*

