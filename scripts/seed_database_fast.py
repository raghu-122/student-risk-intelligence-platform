#!/usr/bin/env python3
"""
Fast bulk-insert seeder using SQLAlchemy Core for speed.
Truncates all tables and re-seeds from generated CSVs.
Run generate_data.py first, then this script.
Usage: python scripts/seed_database_fast.py
"""
import csv, json, sys, os
from pathlib import Path
from datetime import date, datetime
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
os.chdir(ROOT / "backend")

CSV_DIR = ROOT / "data" / "generated" / "csv"
GT_DIR  = ROOT / "data" / "ground_truth"

from app.db.database import engine
from app.db.init_db import create_tables, seed_default_users
from app.db.database import SessionLocal
from sqlalchemy import text, MetaData

CHUNK = 2000  # rows per bulk insert

def to_date(s):
    try: return date.fromisoformat(s) if s and s not in ("None", "") else None
    except: return None

def to_float(s):
    try: return float(s) if s not in (None, "", "None") else None
    except: return None

def to_int(s):
    try: return int(s) if s not in (None, "", "None") else None
    except: return None

def to_bool(s):
    return str(s).lower() in ("true", "1", "yes")

def to_dt(s):
    try: return datetime.fromisoformat(s) if s and s not in ("None", "") else None
    except: return None

def to_json(s):
    try: return json.loads(s) if s and s not in ("None", "") else None
    except: return None

def read_csv(name):
    p = CSV_DIR / name
    if not p.exists():
        print(f"  [SKIP] {name} not found"); return []
    with open(p, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    print(f"  Read {len(rows):,} rows from {name}")
    return rows

def bulk_insert(conn, table_name, rows, columns):
    if not rows:
        return
    for i in range(0, len(rows), CHUNK):
        batch = rows[i:i+CHUNK]
        conn.execute(text(
            f"INSERT OR IGNORE INTO {table_name} ({', '.join(columns)}) "
            f"VALUES ({', '.join(':' + c for c in columns)})"
        ), batch)
    conn.commit()

def main():
    t0 = time.time()
    print("Creating tables...")
    create_tables()

    db = SessionLocal()
    print("Seeding default users...")
    seed_default_users(db)
    db.close()

    with engine.connect() as conn:
        # ── Staff ──────────────────────────────────────────────
        rows = read_csv("staff.csv")
        print(f"  Inserting {len(rows)} staff (upsert)...")
        data = [{"staff_id": r["staff_id"], "first_name": r["first_name"],
                 "last_name": r["last_name"], "email": r["email"],
                 "role": r["role"], "department": r["department"],
                 "is_active": 1 if to_bool(r.get("is_active", True)) else 0}
                for r in rows]
        bulk_insert(conn, "staff", data,
                    ["staff_id","first_name","last_name","email","role","department","is_active"])

        # ── Students ───────────────────────────────────────────
        rows = read_csv("students.csv")
        print(f"  Inserting {len(rows):,} students...")
        data = [{"student_id": r["student_id"], "first_name": r["first_name"],
                 "last_name": r["last_name"], "email": r["email"],
                 "enrollment_date": r["enrollment_date"] or None,
                 "academic_year": r["academic_year"], "department": r["department"],
                 "program": r["program"], "current_status": r["current_status"]}
                for r in rows]
        bulk_insert(conn, "students", data,
                    ["student_id","first_name","last_name","email","enrollment_date",
                     "academic_year","department","program","current_status"])

        # ── Courses ────────────────────────────────────────────
        rows = read_csv("courses.csv")
        print(f"  Inserting {len(rows)} courses...")
        data = [{"course_id": r["course_id"], "course_name": r["course_name"],
                 "course_code": r["course_code"], "department": r["department"],
                 "credits": to_int(r["credits"]),
                 "semester": r["semester"],
                 "instructor_id": r.get("instructor_id") or None}
                for r in rows]
        bulk_insert(conn, "courses", data,
                    ["course_id","course_name","course_code","department","credits","semester","instructor_id"])

        # ── Enrollments ────────────────────────────────────────
        rows = read_csv("enrollments.csv")
        print(f"  Inserting {len(rows):,} enrollments...")
        data = [{"enrollment_id": r["enrollment_id"], "student_id": r["student_id"],
                 "course_id": r["course_id"],
                 "enrollment_date": r["enrollment_date"] or None,
                 "effective_from": r["effective_from"] or None,
                 "effective_to": r.get("effective_to") or None,
                 "enrollment_status": r["enrollment_status"],
                 "final_grade": to_float(r.get("final_grade"))}
                for r in rows]
        bulk_insert(conn, "enrollments", data,
                    ["enrollment_id","student_id","course_id","enrollment_date",
                     "effective_from","effective_to","enrollment_status","final_grade"])

        # ── Assessments ────────────────────────────────────────
        rows = read_csv("assessments.csv")
        print(f"  Inserting {len(rows)} assessments...")
        data = [{"assessment_id": r["assessment_id"], "course_id": r["course_id"],
                 "assessment_name": r["assessment_name"], "assessment_type": r["assessment_type"],
                 "maximum_marks": to_float(r["maximum_marks"]),
                 "weightage": to_float(r["weightage"]),
                 "assessment_date": r["assessment_date"] or None}
                for r in rows]
        bulk_insert(conn, "assessments", data,
                    ["assessment_id","course_id","assessment_name","assessment_type",
                     "maximum_marks","weightage","assessment_date"])

        # ── Attendance Events (large) ──────────────────────────
        rows = read_csv("attendance_events.csv")
        print(f"  Inserting {len(rows):,} attendance events (this may take several minutes)...")
        data = [{"attendance_id": r["attendance_id"], "enrollment_id": r["enrollment_id"],
                 "attendance_date": r["attendance_date"] or None,
                 "attendance_status": r["attendance_status"],
                 "session_number": to_int(r["session_number"]),
                 "issue_type": r.get("issue_type") or None}
                for r in rows]
        bulk_insert(conn, "attendance_events", data,
                    ["attendance_id","enrollment_id","attendance_date","attendance_status",
                     "session_number","issue_type"])

        # ── Assessment Results (medium-large) ─────────────────
        rows = read_csv("assessment_results.csv")
        print(f"  Inserting {len(rows):,} assessment results...")
        data = [{"result_id": r["result_id"], "assessment_id": r["assessment_id"],
                 "enrollment_id": r["enrollment_id"],
                 "marks_obtained": to_float(r.get("marks_obtained")),
                 "percentage": to_float(r.get("percentage")),
                 "submission_status": r["submission_status"],
                 "evaluated_at": r.get("evaluated_at") or None}
                for r in rows]
        bulk_insert(conn, "assessment_results", data,
                    ["result_id","assessment_id","enrollment_id","marks_obtained",
                     "percentage","submission_status","evaluated_at"])

        # ── LMS Activities (very large) ────────────────────────
        rows = read_csv("lms_activities.csv")
        print(f"  Inserting {len(rows):,} LMS activities (this may take several minutes)...")
        data = [{"activity_id": r["activity_id"], "enrollment_id": r["enrollment_id"],
                 "activity_type": r["activity_type"],
                 "activity_timestamp": r.get("activity_timestamp") or None,
                 "duration_minutes": to_int(r.get("duration_minutes")),
                 "resource_id": r.get("resource_id") or None}
                for r in rows]
        bulk_insert(conn, "lms_activities", data,
                    ["activity_id","enrollment_id","activity_type","activity_timestamp",
                     "duration_minutes","resource_id"])

        # ── Support Cases ──────────────────────────────────────
        rows = read_csv("support_cases.csv")
        print(f"  Inserting {len(rows)} support cases...")
        data = [{"case_id": r["case_id"], "student_id": r["student_id"],
                 "enrollment_id": r.get("enrollment_id") or None,
                 "case_type": r["case_type"], "description": r["description"],
                 "priority": r["priority"],
                 "assigned_staff_id": r.get("assigned_staff_id") or None,
                 "case_status": r["case_status"],
                 "opened_at": r.get("opened_at") or None,
                 "closed_at": r.get("closed_at") or None,
                 "resolution_notes": r.get("resolution_notes") or None}
                for r in rows]
        bulk_insert(conn, "support_cases", data,
                    ["case_id","student_id","enrollment_id","case_type","description","priority",
                     "assigned_staff_id","case_status","opened_at","closed_at","resolution_notes"])

        # ── Risk Assessments ───────────────────────────────────
        rows = read_csv("risk_assessments.csv")
        print(f"  Inserting {len(rows):,} risk assessments...")
        data = [{"risk_id": r["risk_id"], "student_id": r["student_id"],
                 "enrollment_id": r.get("enrollment_id") or None,
                 "cutoff_date": r["cutoff_date"] or None,
                 "risk_score": to_float(r.get("risk_score")),
                 "risk_category": r["risk_category"],
                 "factor_scores": r.get("factor_scores") or None,
                 "factor_weights": r.get("factor_weights") or None,
                 "reasons": r.get("reasons") or None,
                 "data_completeness": to_float(r.get("data_completeness")),
                 "model_version": r.get("model_version", "v1.0"),
                 "is_anomaly": 1 if to_bool(r.get("is_anomaly", False)) else 0}
                for r in rows]
        bulk_insert(conn, "risk_assessments", data,
                    ["risk_id","student_id","enrollment_id","cutoff_date","risk_score",
                     "risk_category","factor_scores","factor_weights","reasons",
                     "data_completeness","model_version","is_anomaly"])

        # ── Interventions ──────────────────────────────────────
        rows = read_csv("interventions.csv")
        print(f"  Inserting {len(rows)} interventions...")
        data = [{"intervention_id": r["intervention_id"], "student_id": r["student_id"],
                 "enrollment_id": r.get("enrollment_id") or None,
                 "case_id": r.get("case_id") or None,
                 "risk_assessment_id": r.get("risk_assessment_id") or None,
                 "intervention_type": r["intervention_type"],
                 "trigger_date": r["trigger_date"] or None,
                 "assigned_staff_id": r.get("assigned_staff_id") or None,
                 "start_date": r.get("start_date") or None,
                 "due_date": r.get("due_date") or None,
                 "completion_date": r.get("completion_date") or None,
                 "intervention_status": r["intervention_status"],
                 "expected_outcome": r.get("expected_outcome") or None,
                 "actual_outcome": r.get("actual_outcome") or None}
                for r in rows]
        bulk_insert(conn, "interventions", data,
                    ["intervention_id","student_id","enrollment_id","case_id","risk_assessment_id",
                     "intervention_type","trigger_date","assigned_staff_id","start_date","due_date",
                     "completion_date","intervention_status","expected_outcome","actual_outcome"])

        # ── Outcomes ───────────────────────────────────────────
        rows = read_csv("outcomes.csv")
        print(f"  Inserting {len(rows)} outcomes...")
        data = [{"outcome_id": r["outcome_id"], "student_id": r["student_id"],
                 "enrollment_id": r.get("enrollment_id") or None,
                 "intervention_id": r.get("intervention_id") or None,
                 "evaluation_period_start": r["evaluation_period_start"] or None,
                 "evaluation_period_end": r["evaluation_period_end"] or None,
                 "baseline_risk_score": to_float(r.get("baseline_risk_score")),
                 "future_risk_score": to_float(r.get("future_risk_score")),
                 "academic_performance_change": to_float(r.get("academic_performance_change")),
                 "attendance_change": to_float(r.get("attendance_change")),
                 "engagement_change": to_float(r.get("engagement_change")),
                 "outcome_label": r["outcome_label"],
                 "evaluation_date": r["evaluation_date"] or None}
                for r in rows]
        bulk_insert(conn, "outcomes", data,
                    ["outcome_id","student_id","enrollment_id","intervention_id",
                     "evaluation_period_start","evaluation_period_end","baseline_risk_score",
                     "future_risk_score","academic_performance_change","attendance_change",
                     "engagement_change","outcome_label","evaluation_date"])

        # ── Data Quality Issues ────────────────────────────────
        rows = read_csv("data_quality_issues.csv")
        print(f"  Inserting {len(rows)} data quality issues...")
        data = [{"issue_id": r["issue_id"], "issue_type": r["issue_type"],
                 "affected_entity": r["affected_entity"],
                 "affected_record_id": r["affected_record_id"],
                 "expected_behavior": r.get("expected_behavior") or None,
                 "observed_behavior": r.get("observed_behavior") or None,
                 "ground_truth_label": r.get("ground_truth_label") or None,
                 "detection_status": r.get("detection_status", "DETECTED"),
                 "explanation": r.get("explanation") or None,
                 "severity": r.get("severity", "HIGH"),
                 "is_injected_anomaly": 1 if to_bool(r.get("is_injected_anomaly", True)) else 0}
                for r in rows]
        bulk_insert(conn, "data_quality_issues", data,
                    ["issue_id","issue_type","affected_entity","affected_record_id",
                     "expected_behavior","observed_behavior","ground_truth_label",
                     "detection_status","explanation","severity","is_injected_anomaly"])

        # ── Ground Truth ───────────────────────────────────────
        gt_path = GT_DIR / "ground_truth.csv"
        if gt_path.exists():
            with open(gt_path, encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            print(f"  Inserting {len(rows)} ground-truth labels...")
            data = [{"gt_id": r["gt_id"],
                     "student_id": r.get("student_id") or None,
                     "risk_id": r.get("risk_id") or None,
                     "expected_risk_category": r.get("expected_risk_category") or None,
                     "expected_outcome_label": r.get("expected_outcome_label") or None,
                     "expected_anomaly_detected": 1 if to_bool(r.get("expected_anomaly_detected")) else 0
                        if r.get("expected_anomaly_detected") else None,
                     "evaluation_reference": r.get("evaluation_reference") or None,
                     "notes": r.get("notes") or None}
                    for r in rows]
            bulk_insert(conn, "ground_truth", data,
                        ["gt_id","student_id","risk_id","expected_risk_category",
                         "expected_outcome_label","expected_anomaly_detected",
                         "evaluation_reference","notes"])

        # ── Final counts ───────────────────────────────────────
        elapsed = time.time() - t0
        print(f"\n✅ Database seeded in {elapsed:.1f}s!")
        tables = [
            ("students", "student_id"), ("courses", "course_id"),
            ("enrollments", "enrollment_id"), ("attendance_events", "attendance_id"),
            ("assessment_results", "result_id"), ("lms_activities", "activity_id"),
            ("risk_assessments", "risk_id"), ("interventions", "intervention_id"),
            ("outcomes", "outcome_id"), ("support_cases", "case_id"),
            ("data_quality_issues", "issue_id"),
        ]
        for tbl, pk in tables:
            cnt = conn.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar()
            print(f"   {tbl}: {cnt:,}")

if __name__ == "__main__":
    main()

