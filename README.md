# Student Risk Intelligence Platform

An academic early-warning and intervention-tracking application. The platform keeps student records, attendance, assessment performance, learning-management activity, support cases, risk assessments, interventions, and observed outcomes in one workflow. Risk scores are explainable and computed only from information available at the selected cutoff date.

This repository includes a React application, a FastAPI API, SQLAlchemy models, deterministic synthetic data generation, exports, and validation tools. It is intended for development and evaluation with synthetic data; it is not a clinical or automated decision-making system.

## Features

- Dashboard KPIs, latest risk distribution, high-risk students, and recent interventions.
- Student search and profiles with enrollments, risk history, support cases, and interventions.
- Course, attendance, assessment, results, and LMS activity views.
- Explainable risk assessment and rule-based intervention recommendations.
- Support-case and intervention creation and lifecycle tracking.
- Outcome evaluation over a baseline and a later evaluation period.
- Five labelled anomaly checks and a data-quality findings view.
- CSV, JSON, and PostgreSQL-compatible SQL seed exports.

## Architecture and technology

- Frontend: React 18, TypeScript, Vite, Tailwind CSS, Recharts, Axios, and Oxlint.
- Backend: Python, FastAPI, Pydantic, SQLAlchemy, and PostgreSQL through psycopg2.
- Tests: pytest, FastAPI TestClient, and isolated SQLite databases.
- Data: fixed-seed synthetic generator using NumPy, pandas, and Faker.

## Prerequisites

- Python 3.10 or later.
- Node.js 18 or later and npm.
- PostgreSQL 14 or later for a persistent local application database.

## Configuration and installation

Create a PostgreSQL database and user, then copy and edit the backend environment file:

```powershell
createdb student_risk_db
Copy-Item backend\.env.example backend\.env
```

Set `DATABASE_URL` to the local PostgreSQL connection string and replace `SECRET_KEY` with a randomly generated value before using the application outside a local development environment.

Install backend dependencies and start the API:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
Set-Location backend
python -m uvicorn app.main:app --reload
```

The API creates missing tables and development accounts on startup. It does not apply schema changes to tables that already exist; see [docs/DATABASE_SCHEMA.md](./docs/DATABASE_SCHEMA.md) before upgrading an existing database.

In another terminal, install and start the frontend:

```powershell
Copy-Item frontend\.env.example frontend\.env
Set-Location frontend
npm ci
npm run dev
```

The frontend reads `VITE_API_URL` from `frontend\.env`; the default points to `http://localhost:8000`.

## Development accounts

The backend creates these local development accounts when it initializes an empty user table:

| Username | Password | Role |
|---|---|---|
| `admin` | `admin123` | Platform administrator |
| `instructor1` | `demo123` | Instructor |
| `advisor1` | `demo123` | Academic administrator |
| `support1` | `demo123` | Support staff |

These are public development defaults, not production credentials. Replace or disable them before exposing the service.

## Database seeding and data exports

Generate and validate the reproducible starter dataset:

```powershell
Set-Location ..
python scripts\generate_data.py --scale starter --seed 20261022
python scripts\validate_data.py
```

Seed the configured PostgreSQL database from the generated CSV files:

```powershell
python scripts\seed_database.py
```

The seeder creates missing tables and skips rows whose primary keys already exist. For a fresh schema, the application also creates its development accounts. Do not load the SQL export and run the CSV seeder against the same database, because both contain the same synthetic entity rows.

The generator supports:

```powershell
python scripts\generate_data.py --scale full --seed 20261022
```

The full scale targets 5,000 students, 200 courses, and 20,000 enrollments. Both scales use the same generator and seed. Generated artifacts are written beneath `data\generated\csv`, `data\generated\json`, and `data\generated\sql`; labels, manifests, anomaly fixtures, and validation evidence are under `data\ground_truth`, `data\manifests`, and `data\validation`.

The SQL file contains inserts for the exported tables and expects their schema to exist already. Do not run it after the CSV seeder has populated those tables.

## Running and testing

Backend tests:

```powershell
Set-Location backend
python -m pytest -q
```

Frontend lint and production build:

```powershell
Set-Location frontend
npm run lint
npm run build
```

Data validation and repeatability:

```powershell
Set-Location ..
python scripts\validate_data.py
python scripts\reproduce_data.py --scale starter --seed 20261022
```

The reproducibility command generates two copies in temporary directories, compares exported-file checksums and row counts, and does not overwrite the checked-in starter data.

## API documentation

With the backend running, use Swagger UI at [http://localhost:8000/api/docs](http://localhost:8000/api/docs), ReDoc at [http://localhost:8000/api/redoc](http://localhost:8000/api/redoc), or the OpenAPI document at [http://localhost:8000/api/openapi.json](http://localhost:8000/api/openapi.json). The health endpoint is `GET /health`.

## Documentation

- [Data dictionary](./docs/DATA_DICTIONARY.md)
- [Database schema](./docs/DATABASE_SCHEMA.md)
- [Business rules](./docs/BUSINESS_RULES.md)
- [Data generation](./docs/DATA_GENERATION.md)
- [Validation report](./docs/VALIDATION_REPORT.md)
- [AI prompt history](./docs/AI_PROMPT_HISTORY.md)
