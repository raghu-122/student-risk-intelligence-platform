#!/usr/bin/env python3
"""
Seed the PostgreSQL database from generated CSV files.
Run generate_data.py first, then this script.
Usage: python scripts/seed_database.py
"""
import csv, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

CSV_DIR = ROOT / "data" / "generated" / "csv"
GT_DIR  = ROOT / "data" / "ground_truth"
VAL_DIR = ROOT / "data" / "validation"

import os
os.chdir(ROOT / "backend")

from app.db.database import SessionLocal, engine
from app.db.init_db import create_tables, seed_default_users
from app.models import *
from app.models.staff import Staff
from app.models.user import User
from app.models.student import Student
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.attendance import AttendanceEvent
from app.models.assessment import Assessment
from app.models.assessment_result import AssessmentResult
from app.models.lms_activity import LMSActivity
from app.models.support_case import SupportCase
from app.models.intervention import Intervention
from app.models.risk_assessment import RiskAssessment
from app.models.outcome import Outcome
from app.models.ground_truth import GroundTruth
from app.models.data_quality_issue import DataQualityIssue
from app.core.security import hash_password
from datetime import date, datetime
import json as _json

def to_date(s):
    return date.fromisoformat(s) if s else None

def to_float(s):
    try: return float(s) if s not in (None, "", "None") else None
    except: return None

def to_bool(s):
    return str(s).lower() in ("true", "1", "yes")

def read_csv(name):
    p = CSV_DIR / name
    if not p.exists():
        print(f"  [SKIP] {name} not found"); return []
    with open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f))

def chunk(lst, n=500):
    for i in range(0, len(lst), n):
        yield lst[i:i+n]

def main():
    print("Creating tables...")
    create_tables()
    db = SessionLocal()
    try:
        print("Seeding default users...")
        seed_default_users(db)

        # Staff
        rows = read_csv("staff.csv")
        print(f"  Inserting {len(rows)} staff...")
        for r in rows:
            if not db.query(Staff).filter(Staff.staff_id == r["staff_id"]).first():
                db.add(Staff(staff_id=r["staff_id"], first_name=r["first_name"],
                             last_name=r["last_name"], email=r["email"],
                             role=r["role"], department=r["department"],
                             is_active=to_bool(r.get("is_active", True))))
        db.commit()

        # Students
        rows = read_csv("students.csv")
        print(f"  Inserting {len(rows)} students...")
        for batch in chunk(rows):
            for r in batch:
                if not db.query(Student).filter(Student.student_id == r["student_id"]).first():
                    db.add(Student(student_id=r["student_id"], first_name=r["first_name"],
                                   last_name=r["last_name"], email=r["email"],
                                   enrollment_date=to_date(r["enrollment_date"]),
                                   academic_year=r["academic_year"], department=r["department"],
                                   program=r["program"], current_status=r["current_status"]))
            db.commit()

        # Courses
        rows = read_csv("courses.csv")
        print(f"  Inserting {len(rows)} courses...")
        for r in rows:
            if not db.query(Course).filter(Course.course_id == r["course_id"]).first():
                db.add(Course(course_id=r["course_id"], course_name=r["course_name"],
                              course_code=r["course_code"], department=r["department"],
                              credits=int(r["credits"]), semester=r["semester"],
                              instructor_id=r.get("instructor_id") or None))
        db.commit()

        # Enrollments
        rows = read_csv("enrollments.csv")
        print(f"  Inserting {len(rows)} enrollments...")
        for batch in chunk(rows):
            for r in batch:
                if not db.query(Enrollment).filter(Enrollment.enrollment_id == r["enrollment_id"]).first():
                    db.add(Enrollment(
                        enrollment_id=r["enrollment_id"], student_id=r["student_id"],
                        course_id=r["course_id"], enrollment_date=to_date(r["enrollment_date"]),
                        effective_from=to_date(r["effective_from"]), effective_to=to_date(r.get("effective_to")),
                        enrollment_status=r["enrollment_status"], final_grade=to_float(r.get("final_grade"))))
            db.commit()

        # Assessments
        rows = read_csv("assessments.csv")
        print(f"  Inserting {len(rows)} assessments...")
        for r in rows:
            if not db.query(Assessment).filter(Assessment.assessment_id == r["assessment_id"]).first():
                db.add(Assessment(assessment_id=r["assessment_id"], course_id=r["course_id"],
                                   assessment_name=r["assessment_name"], assessment_type=r["assessment_type"],
                                   maximum_marks=float(r["maximum_marks"]), weightage=float(r["weightage"]),
                                   assessment_date=to_date(r["assessment_date"])))
        db.commit()

        # Attendance
        rows = read_csv("attendance_events.csv")
        print(f"  Inserting {len(rows)} attendance events...")
        for batch in chunk(rows, 1000):
            for r in batch:
                if not db.query(AttendanceEvent).filter(AttendanceEvent.attendance_id == r["attendance_id"]).first():
                    db.add(AttendanceEvent(attendance_id=r["attendance_id"], enrollment_id=r["enrollment_id"],
                                           attendance_date=to_date(r["attendance_date"]),
                                           attendance_status=r["attendance_status"],
                                           session_number=int(r["session_number"]),
                                           issue_type=r.get("issue_type") or None))
            db.commit()

        # Assessment Results
        rows = read_csv("assessment_results.csv")
        print(f"  Inserting {len(rows)} assessment results...")
        for batch in chunk(rows, 1000):
            for r in batch:
                if not db.query(AssessmentResult).filter(AssessmentResult.result_id == r["result_id"]).first():
                    db.add(AssessmentResult(result_id=r["result_id"], assessment_id=r["assessment_id"],
                                             enrollment_id=r["enrollment_id"],
                                             marks_obtained=to_float(r.get("marks_obtained")),
                                             percentage=to_float(r.get("percentage")),
                                             submission_status=r["submission_status"],
                                             evaluated_at=to_date(r.get("evaluated_at"))))
            db.commit()

        # LMS
        rows = read_csv("lms_activities.csv")
        print(f"  Inserting {len(rows)} LMS activities...")
        for batch in chunk(rows, 1000):
            for r in batch:
                if not db.query(LMSActivity).filter(LMSActivity.activity_id == r["activity_id"]).first():
                    ts_str = r.get("activity_timestamp", "")
                    try:
                        ts = datetime.fromisoformat(ts_str) if ts_str else None
                    except:
                        ts = None
                    db.add(LMSActivity(activity_id=r["activity_id"], enrollment_id=r["enrollment_id"],
                                       activity_type=r["activity_type"], activity_timestamp=ts,
                                       duration_minutes=int(r["duration_minutes"]) if r.get("duration_minutes") else None,
                                       resource_id=r.get("resource_id") or None))
            db.commit()

        # Support cases
        rows = read_csv("support_cases.csv")
        print(f"  Inserting {len(rows)} support cases...")
        for r in rows:
            if not db.query(SupportCase).filter(SupportCase.case_id == r["case_id"]).first():
                opened = datetime.fromisoformat(r["opened_at"]) if r.get("opened_at") else None
                closed = datetime.fromisoformat(r["closed_at"]) if r.get("closed_at") else None
                db.add(SupportCase(case_id=r["case_id"], student_id=r["student_id"],
                                    enrollment_id=r.get("enrollment_id") or None,
                                    case_type=r["case_type"], description=r["description"],
                                    priority=r["priority"],
                                    assigned_staff_id=r.get("assigned_staff_id") or None,
                                    case_status=r["case_status"], opened_at=opened, closed_at=closed,
                                    resolution_notes=r.get("resolution_notes") or None))
        db.commit()

        # Risk assessments
        rows = read_csv("risk_assessments.csv")
        print(f"  Inserting {len(rows)} risk assessments...")
        for batch in chunk(rows, 500):
            for r in batch:
                if not db.query(RiskAssessment).filter(RiskAssessment.risk_id == r["risk_id"]).first():
                    db.add(RiskAssessment(
                        risk_id=r["risk_id"], student_id=r["student_id"],
                        enrollment_id=r.get("enrollment_id") or None,
                        cutoff_date=to_date(r["cutoff_date"]),
                        risk_score=to_float(r.get("risk_score")),
                        risk_category=r["risk_category"],
                        factor_scores=_json.loads(r["factor_scores"]) if r.get("factor_scores") else None,
                        factor_weights=_json.loads(r["factor_weights"]) if r.get("factor_weights") else None,
                        reasons=_json.loads(r["reasons"]) if r.get("reasons") else None,
                        data_completeness=to_float(r.get("data_completeness")),
                        model_version=r.get("model_version", "v1.0"),
                        is_anomaly=to_bool(r.get("is_anomaly", False))))
            db.commit()

        rows = []
        ground_truth_path = GT_DIR / "ground_truth.csv"
        if ground_truth_path.exists():
            with open(ground_truth_path, encoding="utf-8") as source:
                rows = list(csv.DictReader(source))
        print(f"  Inserting {len(rows)} ground-truth labels...")
        for r in rows:
            if not db.query(GroundTruth).filter(GroundTruth.gt_id == r["gt_id"]).first():
                db.add(GroundTruth(
                    gt_id=r["gt_id"], student_id=r.get("student_id") or None,
                    risk_id=r.get("risk_id") or None,
                    expected_risk_category=r.get("expected_risk_category") or None,
                    expected_outcome_label=r.get("expected_outcome_label") or None,
                    expected_anomaly_detected=(
                        to_bool(r["expected_anomaly_detected"])
                        if r.get("expected_anomaly_detected") else None
                    ),
                    evaluation_reference=r.get("evaluation_reference") or None,
                    notes=r.get("notes") or None,
                ))
        db.commit()

        # Interventions
        rows = read_csv("interventions.csv")
        print(f"  Inserting {len(rows)} interventions...")
        for r in rows:
            if not db.query(Intervention).filter(Intervention.intervention_id == r["intervention_id"]).first():
                db.add(Intervention(
                    intervention_id=r["intervention_id"], student_id=r["student_id"],
                    enrollment_id=r.get("enrollment_id") or None,
                    case_id=r.get("case_id") or None,
                    risk_assessment_id=r.get("risk_assessment_id") or None,
                    intervention_type=r["intervention_type"],
                    trigger_date=to_date(r["trigger_date"]),
                    assigned_staff_id=r.get("assigned_staff_id") or None,
                    start_date=to_date(r.get("start_date")),
                    due_date=to_date(r.get("due_date")),
                    completion_date=to_date(r.get("completion_date")),
                    intervention_status=r["intervention_status"],
                    expected_outcome=r.get("expected_outcome") or None,
                    actual_outcome=r.get("actual_outcome") or None))
        db.commit()

        # Outcomes
        rows = read_csv("outcomes.csv")
        print(f"  Inserting {len(rows)} outcomes...")
        for r in rows:
            if not db.query(Outcome).filter(Outcome.outcome_id == r["outcome_id"]).first():
                db.add(Outcome(
                    outcome_id=r["outcome_id"], student_id=r["student_id"],
                    enrollment_id=r.get("enrollment_id") or None,
                    intervention_id=r.get("intervention_id") or None,
                    evaluation_period_start=to_date(r["evaluation_period_start"]),
                    evaluation_period_end=to_date(r["evaluation_period_end"]),
                    baseline_risk_score=to_float(r.get("baseline_risk_score")),
                    future_risk_score=to_float(r.get("future_risk_score")),
                    academic_performance_change=to_float(r.get("academic_performance_change")),
                    attendance_change=to_float(r.get("attendance_change")),
                    engagement_change=to_float(r.get("engagement_change")),
                    outcome_label=r["outcome_label"],
                    evaluation_date=to_date(r["evaluation_date"])))
        db.commit()

        # Data quality issues
        rows = read_csv("data_quality_issues.csv")
        print(f"  Inserting {len(rows)} data quality issues...")
        for r in rows:
            if not db.query(DataQualityIssue).filter(DataQualityIssue.issue_id == r["issue_id"]).first():
                db.add(DataQualityIssue(
                    issue_id=r["issue_id"], issue_type=r["issue_type"],
                    affected_entity=r["affected_entity"], affected_record_id=r["affected_record_id"],
                    expected_behavior=r.get("expected_behavior"),
                    observed_behavior=r.get("observed_behavior"),
                    ground_truth_label=r.get("ground_truth_label"),
                    detection_status=r.get("detection_status", "DETECTED"),
                    explanation=r.get("explanation"),
                    severity=r.get("severity", "HIGH"),
                    is_injected_anomaly=to_bool(r.get("is_injected_anomaly", True))))
        db.commit()

        print("\n✅ Database seeded successfully!")
        from sqlalchemy import func
        counts = {
            "students":           db.query(func.count(Student.student_id)).scalar(),
            "courses":            db.query(func.count(Course.course_id)).scalar(),
            "enrollments":        db.query(func.count(Enrollment.enrollment_id)).scalar(),
            "risk_assessments":   db.query(func.count(RiskAssessment.risk_id)).scalar(),
            "interventions":      db.query(func.count(Intervention.intervention_id)).scalar(),
            "data_quality_issues":db.query(func.count(DataQualityIssue.issue_id)).scalar(),
        }
        for k, v in counts.items():
            print(f"   {k}: {v}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
