# Validation Report

This report accompanies the machine-readable starter result at `data/validation/validation_report.json`. Full-scale results were validated in a temporary directory, which was removed after verification.

## Commands executed

- Backend: `python -m pytest -q` from `backend` — **42 passed**.
- Frontend: `npm run lint` from `frontend` — **0 warnings and 0 errors**; `npm run build` — **passed** (Vite reports a 697.08 kB minified JavaScript chunk).
- Starter data: `python scripts\generate_data.py --scale starter --seed 20261022`, followed by `python scripts\validate_data.py` — **78/78 checks passed**.
- Reproducibility: `python scripts\reproduce_data.py --scale starter --seed 20261022` — **30 exported files were byte-identical** across two isolated generations.
- Full data: `python scripts\generate_data.py --scale full --seed 20261022 --output-dir <temporary-directory>`, followed by `python scripts\validate_data.py --data-dir <temporary-directory>` — **78/78 checks passed**.

## Generated volumes

| Scale | Students | Courses | Enrollments | Attendance events | Assessment results | LMS activities | Support cases | Risk assessments | Interventions | Outcomes | Ground-truth rows |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Starter | 500 | 50 | 2,000 | 175,489 | 8,169 | 262,178 | 75 | 1,756 | 42 | 585 | 1,590 |
| Full | 5,000 | 200 | 20,000 | 1,734,471 | 82,556 | 2,525,888 | 722 | 16,991 | 312 | 5,663 | 6,668 |

## Acceptance coverage

The data validator checks scale volumes, primary-key uniqueness, duplicate student-course and assessment-enrollment pairs, all declared foreign keys, cross-entity ownership, enums, lifecycle and date ordering, assessment percentages and weights, risk-score and outcome recomputation, ground-truth separation, export parity/checksums, and each of the five injected anomaly scenarios. It invokes the backend anomaly detector functions against an isolated in-memory SQLite fixture assembled from the generated source records. All 78 checks passed for both scales, including detection of all five anomaly types.

Backend tests exercise authentication, protected APIs, student routes, dashboard endpoints, outcome evaluation/idempotency, anomaly detection, risk calculations, and case/intervention lifecycle behavior. Frontend acceptance includes a production TypeScript/Vite build and Oxlint.

A successful build alone is not data validation. The exact reproducibility comparison covers generated exports; the manifest's generation timestamp is not used as a model feature.

## Known validation limitations

- A live PostgreSQL server was not required for the SQLite-backed tests or file-level data validation. Database seeding against a live PostgreSQL instance remains an environment-dependent check.
- There is no automated browser end-to-end suite; frontend-to-backend route contracts are exercised through backend tests and the UI is compile/lint validated.
- Vite reports a production JavaScript chunk larger than 500 kB. The build succeeds; code-splitting can be considered separately.
- A prior dependency installation reported four npm advisories (three moderate, one high). They were not investigated or changed as part of this verification.
