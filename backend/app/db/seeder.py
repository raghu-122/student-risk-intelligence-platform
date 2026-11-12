"""Database Seeder: Loads synthetic data from CSV/JSON into the database.
Supports both SQLite and PostgreSQL with idempotent bulk inserts.
"""
import csv
import json
import logging
from pathlib import Path
from datetime import date, datetime
from typing import Dict, Any, List, Optional
from sqlalchemy import text, Engine
from app.db.database import engine as default_engine
from app.db.init_db import create_tables, seed_default_users
from app.db.database import SessionLocal

logger = logging.getLogger(__name__)


def find_data_dir() -> Path:
    """Locate data directory relative to app or working directory."""
    candidates = [
        Path(__file__).resolve().parents[3] / "data",   # root/data from app/db/seeder.py
        Path(__file__).resolve().parents[2] / "data",   # root/data
        Path("data").resolve(),
        Path("../data").resolve(),
    ]
    for c in candidates:
        if c.exists() and (c / "generated").exists():
            return c
    return candidates[0]


DATA_DIR = find_data_dir()
CSV_DIR = DATA_DIR / "generated" / "csv"
JSON_DIR = DATA_DIR / "generated" / "json"
GT_DIR = DATA_DIR / "ground_truth"

CHUNK_SIZE = 1000


def _to_date(s: Optional[str]) -> Optional[date]:
    if not s or s in ("None", "", "null"):
        return None
    try:
        return date.fromisoformat(str(s).strip()[:10])
    except Exception:
        return None


def _to_float(s: Any) -> Optional[float]:
    if s is None or s in ("", "None", "null"):
        return None
    try:
        return round(float(s), 4)
    except Exception:
        return None


def _to_int(s: Any) -> Optional[int]:
    if s is None or s in ("", "None", "null"):
        return None
    try:
        return int(float(s))
    except Exception:
        return None


def _to_bool(s: Any) -> bool:
    return str(s).lower() in ("true", "1", "yes")


def _to_json_str(s: Any) -> Optional[str]:
    if not s or s in ("None", "", "null"):
        return None
    if isinstance(s, (dict, list)):
        return json.dumps(s)
    try:
        json.loads(str(s))
        return str(s)
    except Exception:
        return None


def _read_csv(filename: str) -> List[Dict[str, Any]]:
    p = CSV_DIR / filename
    if not p.exists():
        logger.warning(f"CSV not found: {p}")
        return []
    with open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _read_json(filename: str) -> List[Dict[str, Any]]:
    p = JSON_DIR / filename
    if not p.exists():
        return []
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        logger.warning(f"Failed to read JSON {p}: {e}")
        return []


def _bulk_insert(conn, table_name: str, rows: List[Dict[str, Any]], columns: List[str], pk_col: Optional[str] = None):
    if not rows:
        return
    dialect = conn.dialect.name
    cols_str = ", ".join(columns)
    params_str = ", ".join(f":{c}" for c in columns)

    if dialect == "sqlite":
        stmt_str = f"INSERT OR IGNORE INTO {table_name} ({cols_str}) VALUES ({params_str})"
    elif dialect == "postgresql":
        if pk_col:
            stmt_str = f"INSERT INTO {table_name} ({cols_str}) VALUES ({params_str}) ON CONFLICT ({pk_col}) DO NOTHING"
        else:
            stmt_str = f"INSERT INTO {table_name} ({cols_str}) VALUES ({params_str}) ON CONFLICT DO NOTHING"
    else:
        stmt_str = f"INSERT INTO {table_name} ({cols_str}) VALUES ({params_str})"

    statement = text(stmt_str)
    for i in range(0, len(rows), CHUNK_SIZE):
        batch = rows[i:i + CHUNK_SIZE]
        conn.execute(statement, batch)
    conn.commit()


def seed_database(engine: Optional[Engine] = None, include_large_tables: bool = True) -> Dict[str, int]:
    """Seed database with master, transactional, risk, and outcome records."""
    eng = engine or default_engine
    logger.info("Starting database seeding...")
    create_tables()

    db = SessionLocal()
    seed_default_users(db)
    db.close()

    counts: Dict[str, int] = {}

    with eng.connect() as conn:
        # 1. Staff
        staff_rows = _read_csv("staff.csv")
        if staff_rows:
            staff_data = [{
                "staff_id": r["staff_id"], "first_name": r["first_name"],
                "last_name": r["last_name"], "email": r["email"],
                "role": r["role"], "department": r["department"],
                "is_active": 1 if _to_bool(r.get("is_active", True)) else 0,
            } for r in staff_rows]
            _bulk_insert(conn, "staff", staff_data,
                         ["staff_id", "first_name", "last_name", "email", "role", "department", "is_active"],
                         "staff_id")

        # 2. Students
        stu_rows = _read_csv("students.csv")
        if stu_rows:
            stu_data = [{
                "student_id": r["student_id"], "first_name": r["first_name"],
                "last_name": r["last_name"], "email": r["email"],
                "enrollment_date": _to_date(r.get("enrollment_date")),
                "academic_year": r["academic_year"], "department": r["department"],
                "program": r["program"], "current_status": r["current_status"],
            } for r in stu_rows]
            _bulk_insert(conn, "students", stu_data,
                         ["student_id", "first_name", "last_name", "email", "enrollment_date",
                          "academic_year", "department", "program", "current_status"],
                         "student_id")

        # 3. Courses
        crs_rows = _read_csv("courses.csv")
        if crs_rows:
            crs_data = [{
                "course_id": r["course_id"], "course_name": r["course_name"],
                "course_code": r["course_code"], "department": r["department"],
                "credits": _to_int(r["credits"]) or 3, "semester": r["semester"],
                "instructor_id": r.get("instructor_id") or None,
            } for r in crs_rows]
            _bulk_insert(conn, "courses", crs_data,
                         ["course_id", "course_name", "course_code", "department", "credits", "semester", "instructor_id"],
                         "course_id")

        # 4. Enrollments
        enr_rows = _read_csv("enrollments.csv")
        if enr_rows:
            enr_data = [{
                "enrollment_id": r["enrollment_id"], "student_id": r["student_id"],
                "course_id": r["course_id"],
                "enrollment_date": _to_date(r.get("enrollment_date")),
                "effective_from": _to_date(r.get("effective_from")),
                "effective_to": _to_date(r.get("effective_to")),
                "enrollment_status": r["enrollment_status"],
                "final_grade": _to_float(r.get("final_grade")),
            } for r in enr_rows]
            _bulk_insert(conn, "enrollments", enr_data,
                         ["enrollment_id", "student_id", "course_id", "enrollment_date",
                          "effective_from", "effective_to", "enrollment_status", "final_grade"],
                         "enrollment_id")

        # 5. Assessments
        ass_rows = _read_csv("assessments.csv")
        if ass_rows:
            ass_data = [{
                "assessment_id": r["assessment_id"], "course_id": r["course_id"],
                "assessment_name": r["assessment_name"], "assessment_type": r["assessment_type"],
                "maximum_marks": _to_float(r["maximum_marks"]) or 100.0,
                "weightage": _to_float(r["weightage"]) or 0.1,
                "assessment_date": _to_date(r.get("assessment_date")),
            } for r in ass_rows]
            _bulk_insert(conn, "assessments", ass_data,
                         ["assessment_id", "course_id", "assessment_name", "assessment_type",
                          "maximum_marks", "weightage", "assessment_date"],
                         "assessment_id")

        # 6. Assessment Results
        res_rows = _read_csv("assessment_results.csv")
        if res_rows:
            res_data = [{
                "result_id": r["result_id"], "assessment_id": r["assessment_id"],
                "enrollment_id": r["enrollment_id"],
                "marks_obtained": _to_float(r.get("marks_obtained")),
                "percentage": _to_float(r.get("percentage")),
                "submission_status": r["submission_status"],
                "evaluated_at": _to_date(r.get("evaluated_at")),
            } for r in res_rows]
            _bulk_insert(conn, "assessment_results", res_data,
                         ["result_id", "assessment_id", "enrollment_id", "marks_obtained",
                          "percentage", "submission_status", "evaluated_at"],
                         "result_id")

        # 7. Support Cases
        sc_rows = _read_csv("support_cases.csv")
        if sc_rows:
            sc_data = [{
                "case_id": r["case_id"], "student_id": r["student_id"],
                "enrollment_id": r.get("enrollment_id") or None,
                "case_type": r["case_type"], "description": r["description"],
                "priority": r["priority"],
                "assigned_staff_id": r.get("assigned_staff_id") or None,
                "case_status": r["case_status"],
                "opened_at": _to_date(r.get("opened_at")),
                "closed_at": _to_date(r.get("closed_at")),
                "resolution_notes": r.get("resolution_notes") or None,
            } for r in sc_rows]
            _bulk_insert(conn, "support_cases", sc_data,
                         ["case_id", "student_id", "enrollment_id", "case_type", "description",
                          "priority", "assigned_staff_id", "case_status", "opened_at", "closed_at", "resolution_notes"],
                         "case_id")

        # 8. Risk Assessments
        ra_rows = _read_csv("risk_assessments.csv")
        if ra_rows:
            ra_data = [{
                "risk_id": r["risk_id"], "student_id": r["student_id"],
                "enrollment_id": r.get("enrollment_id") or None,
                "cutoff_date": _to_date(r.get("cutoff_date")),
                "risk_score": _to_float(r.get("risk_score")),
                "risk_category": r["risk_category"],
                "factor_scores": _to_json_str(r.get("factor_scores")),
                "factor_weights": _to_json_str(r.get("factor_weights")),
                "reasons": _to_json_str(r.get("reasons")),
                "data_completeness": _to_float(r.get("data_completeness")),
                "model_version": r.get("model_version", "v1.0"),
                "is_anomaly": 1 if _to_bool(r.get("is_anomaly", False)) else 0,
            } for r in ra_rows]
            _bulk_insert(conn, "risk_assessments", ra_data,
                         ["risk_id", "student_id", "enrollment_id", "cutoff_date", "risk_score",
                          "risk_category", "factor_scores", "factor_weights", "reasons",
                          "data_completeness", "model_version", "is_anomaly"],
                         "risk_id")

        # 8b. Risk Factors
        if ra_rows:
            rf_data = []
            for r in ra_rows:
                rid = r["risk_id"]
                scores = {}
                weights = {}
                try:
                    scores = json.loads(r.get("factor_scores") or "{}")
                    weights = json.loads(r.get("factor_weights") or "{}")
                except Exception:
                    pass
                for fname, fscore in scores.items():
                    if fscore is not None:
                        w = weights.get(fname, 0.2)
                        sc = _to_float(fscore)
                        rf_data.append({
                            "factor_id": f"{rid}-{fname}",
                            "risk_id": rid,
                            "factor_name": fname,
                            "raw_value": sc,
                            "normalized_score": sc,
                            "weight": w,
                            "contribution": round(sc * w, 2) if sc is not None else None,
                            "explanation": f"{fname.replace('_', ' ').title()} risk score {sc}",
                        })
            if rf_data:
                _bulk_insert(conn, "risk_factors", rf_data,
                             ["factor_id", "risk_id", "factor_name", "raw_value",
                              "normalized_score", "weight", "contribution", "explanation"],
                             "factor_id")

        # 9. Interventions
        int_rows = _read_csv("interventions.csv")
        if int_rows:
            int_data = [{
                "intervention_id": r["intervention_id"], "student_id": r["student_id"],
                "enrollment_id": r.get("enrollment_id") or None,
                "case_id": r.get("case_id") or None,
                "risk_assessment_id": r.get("risk_assessment_id") or None,
                "intervention_type": r["intervention_type"],
                "trigger_date": _to_date(r.get("trigger_date")),
                "assigned_staff_id": r.get("assigned_staff_id") or None,
                "start_date": _to_date(r.get("start_date")),
                "due_date": _to_date(r.get("due_date")),
                "completion_date": _to_date(r.get("completion_date")),
                "intervention_status": r["intervention_status"],
                "expected_outcome": r.get("expected_outcome") or None,
                "actual_outcome": r.get("actual_outcome") or None,
            } for r in int_rows]
            _bulk_insert(conn, "interventions", int_data,
                         ["intervention_id", "student_id", "enrollment_id", "case_id", "risk_assessment_id",
                          "intervention_type", "trigger_date", "assigned_staff_id", "start_date", "due_date",
                          "completion_date", "intervention_status", "expected_outcome", "actual_outcome"],
                         "intervention_id")

        # 10. Outcomes
        out_rows = _read_csv("outcomes.csv")
        if out_rows:
            out_data = [{
                "outcome_id": r["outcome_id"], "student_id": r["student_id"],
                "enrollment_id": r.get("enrollment_id") or None,
                "intervention_id": r.get("intervention_id") or None,
                "evaluation_period_start": _to_date(r.get("evaluation_period_start")),
                "evaluation_period_end": _to_date(r.get("evaluation_period_end")),
                "baseline_risk_score": _to_float(r.get("baseline_risk_score")),
                "future_risk_score": _to_float(r.get("future_risk_score")),
                "academic_performance_change": _to_float(r.get("academic_performance_change")),
                "attendance_change": _to_float(r.get("attendance_change")),
                "engagement_change": _to_float(r.get("engagement_change")),
                "outcome_label": r["outcome_label"],
                "evaluation_date": _to_date(r.get("evaluation_date")),
            } for r in out_rows]
            _bulk_insert(conn, "outcomes", out_data,
                         ["outcome_id", "student_id", "enrollment_id", "intervention_id",
                          "evaluation_period_start", "evaluation_period_end", "baseline_risk_score",
                          "future_risk_score", "academic_performance_change", "attendance_change",
                          "engagement_change", "outcome_label", "evaluation_date"],
                         "outcome_id")

        # 11. Data Quality Issues
        dqi_rows = _read_csv("data_quality_issues.csv")
        if dqi_rows:
            dqi_data = [{
                "issue_id": r["issue_id"], "issue_type": r["issue_type"],
                "affected_entity": r["affected_entity"],
                "affected_record_id": r["affected_record_id"],
                "expected_behavior": r.get("expected_behavior") or None,
                "observed_behavior": r.get("observed_behavior") or None,
                "ground_truth_label": r.get("ground_truth_label") or None,
                "detection_status": r.get("detection_status", "DETECTED"),
                "explanation": r.get("explanation") or None,
                "severity": r.get("severity", "HIGH"),
                "is_injected_anomaly": 1 if _to_bool(r.get("is_injected_anomaly", True)) else 0,
            } for r in dqi_rows]
            _bulk_insert(conn, "data_quality_issues", dqi_data,
                         ["issue_id", "issue_type", "affected_entity", "affected_record_id",
                          "expected_behavior", "observed_behavior", "ground_truth_label",
                          "detection_status", "explanation", "severity", "is_injected_anomaly"],
                         "issue_id")

        # 12. Attendance Events (from CSV or JSON)
        if include_large_tables:
            att_rows = _read_csv("attendance_events.csv")
            if not att_rows:
                att_rows = _read_json("attendance_events.json")
            if att_rows:
                att_data = [{
                    "attendance_id": r["attendance_id"], "enrollment_id": r["enrollment_id"],
                    "attendance_date": _to_date(r.get("attendance_date")),
                    "attendance_status": r["attendance_status"],
                    "session_number": _to_int(r.get("session_number")) or 1,
                    "issue_type": r.get("issue_type") or None,
                } for r in att_rows]
                _bulk_insert(conn, "attendance_events", att_data,
                             ["attendance_id", "enrollment_id", "attendance_date",
                              "attendance_status", "session_number", "issue_type"],
                             "attendance_id")

            # 13. LMS Activities (from CSV or JSON)
            lms_rows = _read_csv("lms_activities.csv")
            if not lms_rows:
                lms_rows = _read_json("lms_activities.json")
            if lms_rows:
                lms_data = [{
                    "activity_id": r["activity_id"], "enrollment_id": r["enrollment_id"],
                    "activity_type": r["activity_type"],
                    "activity_timestamp": r.get("activity_timestamp") or None,
                    "duration_minutes": _to_int(r.get("duration_minutes")) or 0,
                    "resource_id": r.get("resource_id") or None,
                } for r in lms_rows]
                _bulk_insert(conn, "lms_activities", lms_data,
                             ["activity_id", "enrollment_id", "activity_type",
                              "activity_timestamp", "duration_minutes", "resource_id"],
                             "activity_id")

        # Record counts
        for tbl in ["students", "courses", "enrollments", "assessments", "assessment_results",
                    "attendance_events", "lms_activities", "support_cases", "risk_assessments",
                    "interventions", "outcomes", "data_quality_issues"]:
            try:
                cnt = conn.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar()
                counts[tbl] = cnt or 0
            except Exception:
                pass

    logger.info(f"Seeding completed successfully: {counts}")
    return counts
