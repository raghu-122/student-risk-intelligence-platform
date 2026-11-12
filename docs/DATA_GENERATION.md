# Data Generation

## Commands

From the repository root:

```powershell
python scripts\generate_data.py --scale starter --seed 20261022
python scripts\generate_data.py --scale full --seed 20261022
python scripts\validate_data.py
python scripts\reproduce_data.py --scale starter --seed 20261022
```

The default seed is `20261022`. Both scales use the same generator and deterministic ID conventions. Reproducibility compares hashes of CSV, JSON, SQL, ground-truth, and anomaly exports generated in separate temporary directories; it does not overwrite the checked-in dataset.

## Scales

| Scale | Students | Courses | Enrollments |
|---|---:|---:|---:|
| Starter | 500 | 50 | 2,000 |
| Full | 5,000 | 200 | 20,000 |

The generator also creates staff, assessments and results, attendance events, LMS activities, support cases, risk assessments, interventions, outcomes, ground-truth labels, and five injected anomaly fixtures. Counts depend on seed for generated activity and lifecycle subsets; exact current starter counts are in `data/manifests/manifest.json`.

## Exports and seeding

- `data/generated/csv/`: relational entity exports.
- `data/generated/json/`: one JSON array per generated CSV.
- `data/generated/sql/seed.sql`: PostgreSQL-compatible `INSERT` statements; assumes tables already exist.
- `data/ground_truth/`: expected risk/outcome/anomaly labels; kept separate from model input features.
- `data/validation/anomaly_records.json`: references to the five explicit anomaly source rows.
- `data/manifests/manifest.json`: scale, seed, row counts, and SHA-256 checksums.
- `data/validation/validation_report.json`: results from the data validator.

The preferred database import is:

```powershell
python scripts\seed_database.py
```

It reads the CSV exports, creates missing model tables, seeds local development users, and loads ground-truth rows. The SQL export is an alternative import route; do not apply both routes to the same populated tables.

## Derivation and labels

Risk-factor values and composite scores use the backend business rules documented in [BUSINESS_RULES.md](./BUSINESS_RULES.md). Attendance, assessment, LMS activity, and support-case records are the source data. Normal risk rows only use source records available by their cutoff. Outcomes are computed from the baseline and future source windows. Anomaly labels and expected outcomes are stored separately and must never be treated as model input features.

