# Student Risk Intelligence Platform

> Identify at-risk students early. Coordinate timely interventions. Measure outcomes.

[![Tests](https://img.shields.io/badge/tests-42%20passed-brightgreen)](backend/tests/)
[![Python](https://img.shields.io/badge/python-3.13-blue)](backend/)
[![React](https://img.shields.io/badge/react-18-blue)](frontend/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.162-green)](backend/)

---

## Overview

The **Student Risk Intelligence Platform** is a full-stack application that:

- Monitors student attendance, academic performance, LMS engagement and support history
- Calculates explainable risk scores using a transparent rule-based engine
- Coordinates interventions and tracks outcomes
- Provides role-based dashboards for instructors, administrators and support staff

**Live frontend:** https://student-risk-intelligence-platform.vercel.app/

**Tech stack:** FastAPI + SQLAlchemy (backend) · React 18 + Vite + TypeScript (frontend) · SQLite (dev) / PostgreSQL (prod)

---

## Quick Start (Local Development)

### Prerequisites

- Python 3.13+
- Node.js 20+
- Git

### 1 — Clone and set up the backend

```bash
git clone https://github.com/raghu-122/student-risk-intelligence-platform.git
cd student-risk-intelligence-platform

# Create and activate a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install backend dependencies
pip install -r backend/requirements.txt
```

### 2 — Configure environment variables

Copy the example env file and edit it:

```bash
cp backend/.env.example backend/.env
```

Minimum required variables (`backend/.env`):

```env
DATABASE_URL=sqlite:///./student_risk.db
SECRET_KEY=change-me-to-a-secure-random-string
ENVIRONMENT=development
CORS_ORIGINS=["http://localhost:5173"]
```

### 3 — Generate synthetic data (optional but recommended)

> ⚠️ **Note:** `data/raw/attendance_events.csv` (162 MB) and `data/raw/lms_activities.csv` (225 MB) exceed GitHub's 100 MB limit and are gitignored. Regenerate them locally.

**Starter dataset** (500 students — fast, good for development):

```bash
python scripts/generate_data.py --scale starter --seed 20261022
python scripts/seed_database_fast.py
```

**Full dataset** (5,000 students — takes ~5 minutes to generate, ~35 s to seed):

```bash
python scripts/generate_data.py --scale full --seed 20261022
python scripts/seed_database_fast.py
```

### 4 — Start the backend

```bash
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

API docs: http://127.0.0.1:8000/api/docs  
Health check: http://127.0.0.1:8000/api/health/database

### 5 — Start the frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:5173

### Default Login Credentials

| Role | Username | Password |
|------|----------|----------|
| Platform Administrator | admin | admin123 |
| Instructor | instructor1 | demo123 |
| Academic Advisor | advisor1 | demo123 |
| Support Staff | support1 | demo123 |

---

## Running Tests

> **Important:** Tests must be run outside the sandbox (or with network/thread access). The test suite uses `anyio` threads internally.

```bash
# From the project root (with venv active)
python -m pytest backend/tests/ -v --tb=short
```

Expected output: **42 passed**

---

## Project Structure

```
student-risk-intelligence-platform/
├── backend/
│   ├── app/
│   │   ├── api/routes/      # FastAPI route handlers
│   │   ├── core/            # Config, security, constants
│   │   ├── db/              # Database setup and init
│   │   ├── models/          # SQLAlchemy ORM models
│   │   └── services/        # Risk engine, intervention engine
│   ├── tests/               # Pytest test suite (42 tests)
│   ├── requirements.txt
│   └── runtime.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # Reusable UI components
│   │   ├── pages/           # Route-level pages
│   │   └── services/        # API client
│   └── package.json
├── scripts/
│   ├── generate_data.py     # Synthetic data generator (seed 20261022)
│   ├── seed_database_fast.py # Fast bulk seeder
│   └── validate_data.py     # Data quality validation
├── data/
│   ├── raw/                 # Generated CSVs (large files gitignored)
│   ├── processed/
│   ├── ground_truth/        # Anomaly labels (kept separate from features)
│   └── exports/
├── documentation/
│   ├── PROJECT_AUDIT.md
│   └── validation_report.md
├── render.yaml              # Render.com deployment config
├── Procfile                 # Heroku-style process file
└── pytest.ini
```

---

## Risk Engine

The platform uses a **transparent, explainable rule-based risk engine** (not a black-box ML model).

**Risk factors and weights:**

| Factor | Weight |
|--------|--------|
| Attendance rate | 30% |
| Academic performance | 30% |
| Performance trend | 15% |
| LMS engagement | 15% |
| Support history | 10% |

**Risk categories:**

| Score | Category |
|-------|----------|
| 0–29 | Low Risk |
| 30–59 | Medium Risk |
| 60–100 | High Risk |

Every prediction includes human-readable reasons explaining which factors drove the score.

---

## Key API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/login` | Authenticate and receive JWT |
| GET | `/api/health/database` | DB connection + table counts |
| GET | `/api/dashboard/stats` | Platform KPI summary |
| GET | `/api/risk/summary` | Risk distribution across all students |
| GET | `/api/risk/students` | Paginated list with latest risk scores |
| GET | `/api/risk/factors/{student_id}` | Detailed factor breakdown |
| POST | `/api/risk/evaluate` | Re-evaluate risk for a student |
| GET | `/api/analytics/overview` | Trend analytics |
| GET | `/api/students/{id}/risk` | Student-level risk assessment |

Full interactive docs: `/api/docs`

---

## Production Deployment

### Backend (Render.com)

1. Connect your GitHub repository to [Render.com](https://render.com)
2. Render will auto-detect `render.yaml` and configure the service
3. Set these environment variables in the Render dashboard:
   - `DATABASE_URL` — your managed PostgreSQL URL (Supabase, Neon, Render Postgres)
   - `SECRET_KEY` — a strong random secret
   - `CORS_ORIGINS` — `["https://student-risk-intelligence-platform.vercel.app"]`
   - `ENVIRONMENT` — `production`

### Frontend (Vercel)

1. The frontend auto-deploys from GitHub via Vercel
2. Set `VITE_API_URL` in the Vercel dashboard to your deployed Render backend URL
3. Trigger a redeploy

---

## Data Quality and Anomaly Detection

The platform deliberately injects **5 anomaly scenarios** into the dataset to validate detection:

| ID | Anomaly Type | Severity |
|----|-------------|---------|
| ANO-001 | Temporal leakage (future grades in risk score) | Critical |
| ANO-002 | Wrong attendance denominator | High |
| ANO-003 | Withdrawn student remains active | Medium |
| ANO-004 | Intervention precedes triggering event | High |
| ANO-005 | Missing data interpreted as failure | Medium |

All 5 anomaly types are automatically detected by the validation engine and confirmed by the test suite.

See `documentation/validation_report.md` for the full validation report.

---

## Seed Data Statistics (Full Scale, Seed 20261022)

| Entity | Count |
|--------|-------|
| Students | 5,000 |
| Courses | 200 |
| Enrollments | 21,965 |
| Attendance Events | 1,906,906 |
| Assessment Results | 90,678 |
| LMS Activities | 2,525,888 |
| Support Cases | 722 |
| Risk Assessments | 1,756 |

---

## License

MIT
