#!/usr/bin/env python3
"""
Synthetic Data Generation Engine
YottaFlex Student Risk Intelligence Platform

Usage:
    python scripts/generate_data.py --scale starter --seed 20261022
    python scripts/generate_data.py --scale full    --seed 20261022

Scales:
    starter : 500 students, 50 courses, 2000 enrollments
    full    : 5000 students, 200 courses, 20000 enrollments

Fixed seed 20261022 guarantees identical output on every run.
"""
import argparse
import csv
import hashlib
import json
import os
import random
import sys
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

# ── paths ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CSV_DIR = DATA_DIR / "generated" / "csv"
JSON_DIR = DATA_DIR / "generated" / "json"
GT_DIR = DATA_DIR / "ground_truth"
MAN_DIR = DATA_DIR / "manifests"
VAL_DIR = DATA_DIR / "validation"

# ── constants ────────────────────────────────────────────────────────────────
ACADEMIC_START = date(2026, 1, 15)
ACADEMIC_END   = date(2026, 12, 15)
CUTOFF         = date(2026, 7, 1)
EVAL_START     = date(2026, 7, 2)
EVAL_END       = date(2026, 12, 15)
ACADEMIC_YEAR  = "2026"

DEPARTMENTS = [
    "Computer Science", "Mathematics", "Physics", "Chemistry",
    "Biology", "Engineering", "Business Administration",
    "Economics", "Psychology", "Sociology",
]
PROGRAMS = {
    "Computer Science":       ["B.Sc Computer Science", "B.Sc Software Engineering", "B.Sc Data Science"],
    "Mathematics":            ["B.Sc Mathematics", "B.Sc Applied Mathematics"],
    "Physics":                ["B.Sc Physics", "B.Sc Applied Physics"],
    "Chemistry":              ["B.Sc Chemistry", "B.Sc Biochemistry"],
    "Biology":                ["B.Sc Biology", "B.Sc Microbiology", "B.Sc Biotechnology"],
    "Engineering":            ["B.Eng Electrical", "B.Eng Mechanical", "B.Eng Civil"],
    "Business Administration":["BBA", "B.Com", "BBA Marketing"],
    "Economics":              ["B.Sc Economics", "B.A Economics"],
    "Psychology":             ["B.Sc Psychology", "B.A Psychology"],
    "Sociology":              ["B.A Sociology", "B.A Social Work"],
}
ASSESSMENT_TYPES = ["QUIZ", "ASSIGNMENT", "MIDTERM", "FINAL", "PROJECT", "PRESENTATION"]
LMS_TYPES = ["LOGIN", "VIDEO_WATCH", "RESOURCE_VIEW", "ASSIGNMENT_SUBMISSION",
             "QUIZ_ATTEMPT", "DISCUSSION", "COURSE_ACCESS"]
CASE_TYPES = ["ACADEMIC", "ATTENDANCE", "WELFARE", "BEHAVIORAL", "FINANCIAL"]
STAFF_ROLES = ["INSTRUCTOR", "ACADEMIC_ADMINISTRATOR", "SUPPORT_STAFF"]

SQL_EXPORTS = [
    ("staff", "staff.csv", ("staff_id", "first_name", "last_name", "email", "role", "department", "is_active")),
    ("students", "students.csv", ("student_id", "first_name", "last_name", "email", "enrollment_date", "academic_year", "department", "program", "current_status")),
    ("courses", "courses.csv", ("course_id", "course_name", "course_code", "department", "credits", "semester", "instructor_id")),
    ("enrollments", "enrollments.csv", ("enrollment_id", "student_id", "course_id", "enrollment_date", "effective_from", "effective_to", "enrollment_status", "final_grade")),
    ("assessments", "assessments.csv", ("assessment_id", "course_id", "assessment_name", "assessment_type", "maximum_marks", "weightage", "assessment_date")),
    ("attendance_events", "attendance_events.csv", ("attendance_id", "enrollment_id", "attendance_date", "attendance_status", "session_number", "issue_type")),
    ("assessment_results", "assessment_results.csv", ("result_id", "assessment_id", "enrollment_id", "marks_obtained", "percentage", "submission_status", "evaluated_at")),
    ("lms_activities", "lms_activities.csv", ("activity_id", "enrollment_id", "activity_type", "activity_timestamp", "duration_minutes", "resource_id", "activity_metadata")),
    ("support_cases", "support_cases.csv", ("case_id", "student_id", "enrollment_id", "case_type", "description", "priority", "assigned_staff_id", "case_status", "opened_at", "closed_at", "resolution_notes")),
    ("risk_assessments", "risk_assessments.csv", ("risk_id", "student_id", "enrollment_id", "cutoff_date", "risk_score", "risk_category", "factor_scores", "factor_weights", "reasons", "data_completeness", "model_version", "is_anomaly")),
    ("interventions", "interventions.csv", ("intervention_id", "student_id", "enrollment_id", "case_id", "risk_assessment_id", "intervention_type", "trigger_date", "assigned_staff_id", "start_date", "due_date", "completion_date", "intervention_status", "expected_outcome", "actual_outcome")),
    ("outcomes", "outcomes.csv", ("outcome_id", "student_id", "enrollment_id", "intervention_id", "evaluation_period_start", "evaluation_period_end", "baseline_risk_score", "future_risk_score", "academic_performance_change", "attendance_change", "engagement_change", "outcome_label", "evaluation_date")),
    ("ground_truth", "ground_truth.csv", ("gt_id", "student_id", "risk_id", "expected_risk_category", "expected_outcome_label", "expected_anomaly_detected", "evaluation_reference", "notes")),
    ("data_quality_issues", "data_quality_issues.csv", ("issue_id", "issue_type", "affected_entity", "affected_record_id", "expected_behavior", "observed_behavior", "ground_truth_label", "detection_status", "explanation", "severity", "is_injected_anomaly")),
]
SQL_BOOLEAN_COLUMNS = {"is_active", "is_anomaly", "expected_anomaly_detected", "is_injected_anomaly"}
SQL_NUMERIC_COLUMNS = {
    "credits", "maximum_marks", "weightage", "session_number", "marks_obtained",
    "percentage", "duration_minutes", "risk_score", "data_completeness",
    "final_grade", "baseline_risk_score", "future_risk_score",
    "academic_performance_change", "attendance_change", "engagement_change",
}
SQL_DATE_COLUMNS = {
    "enrollment_date", "effective_from", "effective_to", "assessment_date",
    "attendance_date", "evaluated_at", "cutoff_date", "trigger_date", "start_date",
    "due_date", "completion_date", "evaluation_period_start", "evaluation_period_end",
    "evaluation_date",
}
SQL_DATETIME_COLUMNS = {"activity_timestamp", "opened_at", "closed_at"}
SQL_JSON_COLUMNS = {"factor_scores", "factor_weights", "reasons", "activity_metadata"}


# ── helpers ──────────────────────────────────────────────────────────────────
def stu_id(n):  return f"STU-{ACADEMIC_YEAR}-{n:06d}"
def crs_id(n):  return f"CRS-{n:06d}"
def enr_id(s, c): return f"ENR-{s}-{c}"
def asm_id(n):  return f"ASM-{n:06d}"
def res_id(a, e): return f"RES-{a}-{e}"
def att_id(e, d): return f"ATT-{e}-{d.strftime('%Y%m%d')}"
def lms_id(n):  return f"LMS-{ACADEMIC_YEAR}-{n:06d}"
def case_id(n): return f"CASE-{ACADEMIC_YEAR}-{n:06d}"
def int_id(n):  return f"INT-{ACADEMIC_YEAR}-{n:06d}"
def out_id(n):  return f"OUT-{ACADEMIC_YEAR}-{n:06d}"
def stf_id(n):  return f"STF-{n:06d}"
def usr_id(n):  return f"USR-{n:06d}"
def gt_id(n):   return f"GT-{ACADEMIC_YEAR}-{n:06d}"

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def correlated_scores(base_score, n, rng, noise_std=12):
    """Return n scores correlated with base_score, clipped [0,100]."""
    scores = base_score + rng.normal(0, noise_std, n)
    return np.clip(scores, 0, 100)

def weekdays_between(start, end):
    """List of Mon-Fri dates between start and end (inclusive)."""
    days = []
    cur = start
    while cur <= end:
        if cur.weekday() < 5:
            days.append(cur)
        cur += timedelta(days=1)
    return days

def session_dates_weekly(course_start, course_end, sessions_per_week=2):
    """Pick sessions_per_week days per week (Mon=0, Wed=2) between start and end."""
    target_days = [0, 2]  # Monday, Wednesday
    days = []
    cur = course_start
    while cur <= course_end:
        if cur.weekday() in target_days:
            days.append(cur)
        cur += timedelta(days=1)
    return days


# ── main generator ───────────────────────────────────────────────────────────
def generate(scale: str, seed: int, output_dir: Path | None = None):
    global DATA_DIR, CSV_DIR, JSON_DIR, GT_DIR, MAN_DIR, VAL_DIR

    DATA_DIR = Path(output_dir).resolve() if output_dir else ROOT / "data"
    CSV_DIR = DATA_DIR / "generated" / "csv"
    JSON_DIR = DATA_DIR / "generated" / "json"
    GT_DIR = DATA_DIR / "ground_truth"
    MAN_DIR = DATA_DIR / "manifests"
    VAL_DIR = DATA_DIR / "validation"
    for directory in (CSV_DIR, JSON_DIR, GT_DIR, MAN_DIR, VAL_DIR):
        directory.mkdir(parents=True, exist_ok=True)
    for stale_user_export in (CSV_DIR / "users.csv", JSON_DIR / "users.json"):
        if stale_user_export.exists():
            stale_user_export.unlink()

    rng = np.random.default_rng(seed)
    random.seed(seed)
    fake = Faker()
    Faker.seed(seed)

    if scale == "starter":
        N_STUDENTS = 500; N_COURSES = 50; N_ENROLLMENTS = 2000; N_STAFF = 10
    else:
        N_STUDENTS = 5000; N_COURSES = 200; N_ENROLLMENTS = 20000; N_STAFF = 20

    print(f"[generate_data] scale={scale} seed={seed} students={N_STUDENTS} courses={N_COURSES}")

    # ── 1. Staff ────────────────────────────────────────────────────────────
    print("  Generating staff...")
    staff_rows = []
    for i in range(1, N_STAFF + 1):
        dept = DEPARTMENTS[i % len(DEPARTMENTS)]
        staff_rows.append({
            "staff_id": stf_id(i + 4),
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": f"staff{i}@yottaflex.edu",
            "role": STAFF_ROLES[i % len(STAFF_ROLES)],
            "department": dept,
            "is_active": True,
        })
    _write_csv(staff_rows, CSV_DIR / "staff.csv")

    # ── 3. Students ─────────────────────────────────────────────────────────
    print("  Generating students...")
    # Assign performance profiles correlated to demographics
    profiles = rng.choice(["high", "average", "low", "declining", "improving"],
                           p=[0.20, 0.50, 0.20, 0.05, 0.05], size=N_STUDENTS)
    student_rows = []
    student_profiles = {}
    used_emails = set()
    for i in range(1, N_STUDENTS + 1):
        dept = DEPARTMENTS[int(rng.integers(0, len(DEPARTMENTS)))]
        prog = PROGRAMS[dept][int(rng.integers(0, len(PROGRAMS[dept])))]
        enroll_offset = int(rng.integers(0, 10))
        enroll_dt = ACADEMIC_START + timedelta(days=enroll_offset)
        status = str(rng.choice(
            ["ACTIVE", "INACTIVE", "TRANSFERRED", "GRADUATED", "WITHDRAWN"],
            p=[0.90, 0.02, 0.03, 0.02, 0.03],
        ))
        # Unique email
        base = f"{fake.user_name()}{i}"
        email = f"{base}@student.yottaflex.edu"
        while email in used_emails:
            email = f"{base}{int(rng.integers(10,999))}@student.yottaflex.edu"
        used_emails.add(email)
        sid = stu_id(i)
        student_rows.append({
            "student_id": sid,
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": email,
            "enrollment_date": enroll_dt.isoformat(),
            "academic_year": ACADEMIC_YEAR,
            "department": dept,
            "program": prog,
            "current_status": status,
        })
        student_profiles[sid] = profiles[i - 1]
    if not any(s["current_status"] == "WITHDRAWN" for s in student_rows):
        student_rows[-1]["current_status"] = "WITHDRAWN"
    _write_csv(student_rows, CSV_DIR / "students.csv")

    # ── 4. Courses ──────────────────────────────────────────────────────────
    print("  Generating courses...")
    course_rows = []
    course_dept_map = {}
    used_codes = set()
    for i in range(1, N_COURSES + 1):
        dept = DEPARTMENTS[i % len(DEPARTMENTS)]
        code_base = dept.split()[0][:3].upper()
        code = f"{code_base}{100 + i}"
        while code in used_codes:
            code = f"{code_base}{100 + i + int(rng.integers(1,50))}"
        used_codes.add(code)
        instructor_idx = int(rng.integers(1, N_STAFF + 1))
        cid = crs_id(i)
        course_rows.append({
            "course_id": cid,
            "course_name": f"{dept} {fake.word().capitalize()} {['I','II','III'][i%3]}",
            "course_code": code,
            "department": dept,
            "credits": int(rng.choice([2, 3, 4])),
            "semester": "2026-S1",
            "instructor_id": stf_id(instructor_idx + 4),
        })
        course_dept_map[cid] = dept
    _write_csv(course_rows, CSV_DIR / "courses.csv")

    # ── 5. Enrollments ──────────────────────────────────────────────────────
    print("  Generating enrollments...")
    active_students = [s["student_id"] for s in student_rows if s["current_status"] == "ACTIVE"]
    all_course_ids  = [c["course_id"] for c in course_rows]
    student_statuses = {s["student_id"]: s["current_status"] for s in student_rows}
    student_enrollment_dates = {
        s["student_id"]: date.fromisoformat(s["enrollment_date"]) for s in student_rows
    }
    lifecycle_anomaly_student = next(
        s["student_id"] for s in student_rows if s["current_status"] == "WITHDRAWN"
    )
    enrollment_rows = []
    enrollment_set  = set()
    enr_map = {}  # enrollment_id -> {student_id, course_id, profile}
    enrollment_candidates = [
        s["student_id"] for s in student_rows
        if s["student_id"] != lifecycle_anomaly_student
    ]

    lifecycle_course_id = all_course_ids[0]
    lifecycle_enrollment_id = enr_id(lifecycle_anomaly_student, lifecycle_course_id)
    lifecycle_effective_from = student_enrollment_dates[lifecycle_anomaly_student]
    enrollment_rows.append({
        "enrollment_id": lifecycle_enrollment_id,
        "student_id": lifecycle_anomaly_student,
        "course_id": lifecycle_course_id,
        "enrollment_date": lifecycle_effective_from.isoformat(),
        "effective_from": lifecycle_effective_from.isoformat(),
        "effective_to": "",
        "enrollment_status": "ACTIVE",
        "final_grade": "",
    })
    enrollment_set.add((lifecycle_anomaly_student, lifecycle_course_id))
    enr_map[lifecycle_enrollment_id] = {
        "student_id": lifecycle_anomaly_student,
        "course_id": lifecycle_course_id,
        "profile": student_profiles[lifecycle_anomaly_student],
        "status": "ACTIVE",
        "eff_from": lifecycle_effective_from,
        "eff_to": None,
    }

    while len(enrollment_rows) < N_ENROLLMENTS:
        sid = enrollment_candidates[int(rng.integers(0, len(enrollment_candidates)))]
        cid = all_course_ids[int(rng.integers(0, len(all_course_ids)))]
        key = (sid, cid)
        if key in enrollment_set:
            continue
        enrollment_set.add(key)
        eid = enr_id(sid, cid)
        enr_offset = int(rng.integers(0, 5))
        eff_from = max(
            ACADEMIC_START + timedelta(days=enr_offset),
            student_enrollment_dates[sid],
        )
        student_status = student_statuses[sid]
        if student_status == "TRANSFERRED":
            enr_status = "TRANSFERRED"
            eff_to = ACADEMIC_START + timedelta(days=int(rng.integers(45, 150)))
        elif student_status == "GRADUATED":
            enr_status = "COMPLETED"
            eff_to = ACADEMIC_END
        elif student_status == "INACTIVE":
            enr_status = "DROPPED"
            eff_to = CUTOFF - timedelta(days=int(rng.integers(10, 60)))
        elif student_status == "WITHDRAWN":
            enr_status = "WITHDRAWN"
            eff_to = CUTOFF - timedelta(days=int(rng.integers(5, 30)))
        else:
            r = rng.random()
            if r < 0.03:
                enr_status = "DROPPED"
                eff_to = CUTOFF - timedelta(days=int(rng.integers(10, 60)))
            elif r < 0.04:
                enr_status = "WITHDRAWN"
                eff_to = CUTOFF - timedelta(days=int(rng.integers(5, 30)))
            else:
                enr_status = "ACTIVE"
                eff_to = None
        enrollment_rows.append({
            "enrollment_id": eid,
            "student_id": sid,
            "course_id": cid,
            "enrollment_date": eff_from.isoformat(),
            "effective_from": eff_from.isoformat(),
            "effective_to": eff_to.isoformat() if eff_to else "",
            "enrollment_status": enr_status,
            "final_grade": "",
        })
        enr_map[eid] = {"student_id": sid, "course_id": cid,
                         "profile": student_profiles.get(sid, "average"),
                         "status": enr_status, "eff_from": eff_from, "eff_to": eff_to}
    _write_csv(enrollment_rows, CSV_DIR / "enrollments.csv")
    active_enr_ids = [eid for eid, m in enr_map.items() if m["status"] == "ACTIVE"]

    # ── 6. Assessments ──────────────────────────────────────────────────────
    print("  Generating assessments...")
    assessment_rows = []
    course_assessments = {}  # crs_id -> [asm_row]
    asm_counter = 1
    for crs in course_rows:
        cid = crs["course_id"]
        n_asm = int(rng.integers(3, 7))
        weightages = rng.dirichlet(np.ones(n_asm))
        types = rng.choice(ASSESSMENT_TYPES, size=n_asm)
        days_range = (ACADEMIC_END - ACADEMIC_START).days
        dates_offset = sorted(rng.integers(10, days_range, size=n_asm))
        cutoff_offset = (CUTOFF - ACADEMIC_START).days
        dates_offset[0] = int(rng.integers(10, cutoff_offset))
        dates_offset[-1] = int(rng.integers(cutoff_offset + 1, days_range))
        dates_offset.sort()
        course_assessments[cid] = []
        for j in range(n_asm):
            adate = ACADEMIC_START + timedelta(days=int(dates_offset[j]))
            aid = asm_id(asm_counter)
            row = {
                "assessment_id": aid,
                "course_id": cid,
                "assessment_name": f"{types[j].capitalize()} {j+1}",
                "assessment_type": types[j],
                "maximum_marks": float(rng.choice([50.0, 100.0])),
                "weightage": round(float(weightages[j]), 4),
                "assessment_date": adate.isoformat(),
            }
            assessment_rows.append(row)
            course_assessments[cid].append(row)
            asm_counter += 1
    _write_csv(assessment_rows, CSV_DIR / "assessments.csv")

    # ── 7. Attendance ───────────────────────────────────────────────────────
    print("  Generating attendance events...")
    attendance_rows = []
    for eid in enr_map:
        m = enr_map[eid]
        profile = m["profile"]
        end_date = min(m["eff_to"] or ACADEMIC_END, ACADEMIC_END)
        sessions = session_dates_weekly(m["eff_from"], end_date)
        # Base attendance probability by profile
        base_prob = {"high": 0.95, "average": 0.82, "low": 0.65,
                     "declining": 0.75, "improving": 0.72}.get(profile, 0.82)
        approved_prob = 0.05
        for sess_num, sdate in enumerate(sessions, 1):
            r = rng.random()
            if r < approved_prob:
                status = "APPROVED_ABSENCE"
            elif r < approved_prob + (1 - base_prob):
                # For declining profile, increase absence rate after CUTOFF
                if profile == "declining" and sdate > CUTOFF:
                    status = "ABSENT" if rng.random() < 0.4 else "PRESENT"
                elif profile == "improving" and sdate > CUTOFF:
                    status = "PRESENT"
                else:
                    status = "ABSENT"
            elif r < approved_prob + (1 - base_prob) + 0.05:
                status = "LATE"
            else:
                status = "PRESENT"
            attendance_rows.append({
                "attendance_id": att_id(eid, sdate),
                "enrollment_id": eid,
                "attendance_date": sdate.isoformat(),
                "attendance_status": status,
                "session_number": sess_num,
                "issue_type": "",
            })
    _write_csv(attendance_rows, CSV_DIR / "attendance_events.csv")
    print(f"    {len(attendance_rows)} attendance records")

    # ── 8. Assessment Results ───────────────────────────────────────────────
    print("  Generating assessment results...")
    result_rows = []
    enrollment_to_course = {eid: m["course_id"] for eid, m in enr_map.items()}
    missing_data_enrollment = next(
        eid for eid in active_enr_ids if student_statuses[enr_map[eid]["student_id"]] == "ACTIVE"
    )
    missing_data_assessment = next(
        row["assessment_id"]
        for row in course_assessments[enr_map[missing_data_enrollment]["course_id"]]
        if date.fromisoformat(row["assessment_date"]) <= CUTOFF
    )
    for eid, m in enr_map.items():
        cid = m["course_id"]
        profile = m["profile"]
        base_score = {"high": 85, "average": 68, "low": 42,
                      "declining": 72, "improving": 55}.get(profile, 68)
        for asm in course_assessments.get(cid, []):
            aid = asm["assessment_id"]
            rid = res_id(aid, eid)
            adate = date.fromisoformat(asm["assessment_date"])
            if adate < m["eff_from"] or (m["eff_to"] and adate > m["eff_to"]):
                continue
            if eid == missing_data_enrollment and aid == missing_data_assessment:
                result_rows.append({
                    "result_id": rid, "assessment_id": aid, "enrollment_id": eid,
                    "marks_obtained": "", "percentage": "",
                    "submission_status": "MISSING", "evaluated_at": "",
                })
                continue
            # 8% missing submission
            if rng.random() < 0.08:
                result_rows.append({
                    "result_id": rid, "assessment_id": aid, "enrollment_id": eid,
                    "marks_obtained": "", "percentage": "",
                    "submission_status": "MISSING", "evaluated_at": "",
                })
                continue
            # Declining profile gets worse over time
            if profile == "declining" and adate > CUTOFF:
                adj_base = max(20, base_score - 20)
            elif profile == "improving" and adate > CUTOFF:
                adj_base = min(90, base_score + 20)
            else:
                adj_base = base_score
            raw = float(np.clip(rng.normal(adj_base, 12), 0, asm["maximum_marks"]))
            pct = round(raw / asm["maximum_marks"] * 100, 2)
            late = rng.random() < 0.05
            result_rows.append({
                "result_id": rid, "assessment_id": aid, "enrollment_id": eid,
                "marks_obtained": round(raw, 2),
                "percentage": pct,
                "submission_status": "LATE_SUBMISSION" if late else "SUBMITTED",
                "evaluated_at": (adate + timedelta(days=int(rng.integers(1, 7)))).isoformat(),
            })
    _write_csv(result_rows, CSV_DIR / "assessment_results.csv")
    print(f"    {len(result_rows)} assessment results")

    # ── 9. LMS Activity ─────────────────────────────────────────────────────
    print("  Generating LMS activity...")
    lms_rows = []
    lms_counter = 1
    for eid, m in enr_map.items():
        profile = m["profile"]
        # Activities per week by profile
        acts_per_week = {"high": 5, "average": 3, "low": 1,
                          "declining": 3, "improving": 2}.get(profile, 3)
        end_date = min(m["eff_to"] or ACADEMIC_END, ACADEMIC_END)
        duration_days = max(1, (end_date - m["eff_from"]).days + 1)
        total_weeks = max(1, duration_days // 7)
        n_acts = int(rng.poisson(acts_per_week * total_weeks))
        for _ in range(max(0, n_acts)):
            offset_days = int(rng.integers(0, duration_days))
            ts = datetime(m["eff_from"].year, m["eff_from"].month, m["eff_from"].day) + timedelta(
                days=offset_days, hours=int(rng.integers(8, 22)), minutes=int(rng.integers(0, 59))
            )
            atype = LMS_TYPES[int(rng.integers(0, len(LMS_TYPES)))]
            dur = int(rng.integers(2, 90)) if atype in ("VIDEO_WATCH", "RESOURCE_VIEW", "DISCUSSION") else int(rng.integers(1, 15))
            lms_rows.append({
                "activity_id": lms_id(lms_counter),
                "enrollment_id": eid,
                "activity_type": atype,
                "activity_timestamp": ts.isoformat(),
                "duration_minutes": dur,
                "resource_id": f"RES-{int(rng.integers(1, 500)):04d}",
                "activity_metadata": "",
            })
            lms_counter += 1
    _write_csv(lms_rows, CSV_DIR / "lms_activities.csv")
    print(f"    {len(lms_rows)} LMS activities")

    # ── 10. Support Cases (historical) ─────────────────────────────────────
    print("  Generating support cases...")
    case_rows = []
    case_counter = 1
    # ~8% of students get historical support cases
    students_with_cases = rng.choice(active_students,
                                      size=max(1, int(len(active_students) * 0.08)), replace=False)
    for sid in students_with_cases:
        n_cases = int(rng.integers(1, 4))
        for _ in range(n_cases):
            ctype = CASE_TYPES[int(rng.integers(0, len(CASE_TYPES)))]
            priority = rng.choice(["LOW","MEDIUM","HIGH","CRITICAL"], p=[0.2,0.5,0.2,0.1])
            days_ago = int(rng.integers(10, 150))
            opened = datetime(2026, 1, 15) + timedelta(days=days_ago)
            if opened.date() > CUTOFF:
                opened = datetime(2026, 3, 1)
            status = rng.choice(["OPEN","RESOLVED","CLOSED","IN_PROGRESS"], p=[0.2,0.4,0.3,0.1])
            staff_idx = int(rng.integers(1, N_STAFF + 1))
            cid = case_id(case_counter)
            case_rows.append({
                "case_id": cid,
                "student_id": sid,
                "enrollment_id": "",
                "case_type": ctype,
                "description": fake.sentence(nb_words=12),
                "priority": priority,
                "assigned_staff_id": stf_id(staff_idx + 4),
                "case_status": status,
                "opened_at": opened.isoformat(),
                "closed_at": (opened + timedelta(days=int(rng.integers(5, 30)))).isoformat() if status in ("RESOLVED","CLOSED") else "",
                "resolution_notes": fake.sentence() if status in ("RESOLVED","CLOSED") else "",
            })
            case_counter += 1
    _write_csv(case_rows, CSV_DIR / "support_cases.csv")

    # ── 11. Risk Scores (baseline, cutoff=2026-07-01) ──────────────────────
    print("  Computing risk scores (pre-cutoff data only)...")
    risk_rows = []
    risk_counter = 1
    att_df = pd.DataFrame(attendance_rows)
    att_df["attendance_date"] = pd.to_datetime(att_df["attendance_date"])
    asm_df = pd.DataFrame(assessment_rows)
    asm_df["assessment_date"] = pd.to_datetime(asm_df["assessment_date"])

    cutoff_dt = pd.Timestamp(CUTOFF)
    risk_weights = {
        "attendance": 0.30,
        "academic_performance": 0.30,
        "performance_trend": 0.15,
        "lms_engagement": 0.15,
        "historical_support": 0.10,
    }

    att_pre = att_df[att_df["attendance_date"] <= cutoff_dt].copy()
    asm_pre_ids = set(asm_df[asm_df["assessment_date"] <= cutoff_dt]["assessment_id"])
    asm_by_id = {a["assessment_id"]: a for a in assessment_rows}
    graded_by_enrollment = {}
    graded_all_by_enrollment = {}
    for result in result_rows:
        assessment = asm_by_id[result["assessment_id"]]
        if result["marks_obtained"] != "" and result["percentage"] != "":
            graded_record = (
                date.fromisoformat(assessment["assessment_date"]),
                float(result["percentage"]),
                float(assessment["weightage"]),
            )
            graded_all_by_enrollment.setdefault(result["enrollment_id"], []).append(graded_record)
            if assessment["assessment_id"] in asm_pre_ids:
                graded_by_enrollment.setdefault(result["enrollment_id"], []).append(graded_record)

    lms_df = pd.DataFrame(lms_rows) if lms_rows else pd.DataFrame(columns=["enrollment_id","activity_timestamp"])
    if not lms_df.empty:
        lms_df["activity_timestamp"] = pd.to_datetime(lms_df["activity_timestamp"])
        lms_pre = lms_df[lms_df["activity_timestamp"] < cutoff_dt + pd.Timedelta(days=1)]
        lms_count = lms_pre.groupby("enrollment_id").size().to_dict()
    else:
        lms_count = {}

    cases_by_student = {}
    for case in case_rows:
        if datetime.fromisoformat(case["opened_at"]).date() <= CUTOFF:
            cases_by_student.setdefault(case["student_id"], []).append(case)

    for eid in active_enr_ids:
        m = enr_map[eid]
        sid = m["student_id"]

        events = att_pre[att_pre["enrollment_id"] == eid]
        approved = int((events["attendance_status"] == "APPROVED_ABSENCE").sum())
        effective = len(events) - approved
        attended = int(events["attendance_status"].isin(["PRESENT", "LATE"]).sum())
        attendance_available = len(events) >= 3 and effective > 0
        f_att = round((1 - attended / effective) * 100, 2) if attendance_available else None

        graded = sorted(graded_by_enrollment.get(eid, []))
        total_weight = sum(item[2] for item in graded)
        if graded:
            average = (
                sum(score * weight for _, score, weight in graded) / total_weight
                if total_weight
                else sum(score for _, score, _ in graded) / len(graded)
            )
            f_acad = round((1 - average / 100) * 100, 2)
        else:
            f_acad = None

        f_trend = None
        if len(graded) >= 2:
            midpoint = len(graded) // 2
            first_average = sum(score for _, score, _ in graded[:midpoint]) / midpoint
            second_average = sum(score for _, score, _ in graded[midpoint:]) / (len(graded) - midpoint)
            trend = second_average - first_average
            f_trend = round(max(0.0, min(100.0, (-trend + 20) / 40 * 100)), 2)

        days = max(1, (CUTOFF - m["eff_from"]).days) if m["eff_from"] <= CUTOFF else 90
        expected_acts = max(1, days / 7) * 2
        engagement_rate = min(1.0, lms_count.get(eid, 0) / expected_acts)
        f_lms = round(max(0.0, min(100.0, (1 - engagement_rate) * 100)), 2)

        cases = cases_by_student.get(sid, [])
        open_cases = sum(1 for case in cases if case["case_status"] not in ("RESOLVED", "CLOSED"))
        critical_cases = sum(1 for case in cases if case["priority"] == "CRITICAL")
        f_supp = round(min(100.0, len(cases) * 15 + open_cases * 10 + critical_cases * 20), 2)

        factor_scores = {
            "attendance": f_att,
            "academic_performance": f_acad,
            "performance_trend": f_trend,
            "lms_engagement": f_lms,
            "historical_support": f_supp,
        }
        available_factors = [
            key for key, available in (
                ("attendance", attendance_available),
                ("academic_performance", bool(graded)),
                ("performance_trend", len(graded) >= 2),
                ("lms_engagement", True),
                ("historical_support", True),
            ) if available
        ]
        completeness = round(len(available_factors) / len(risk_weights), 2)
        total_weight = sum(risk_weights[key] for key in available_factors)
        if completeness < 0.30 or not total_weight:
            risk_score = None
            risk_cat = "INSUFFICIENT_DATA"
        else:
            weighted_score = sum(
                factor_scores[key] * risk_weights[key] for key in available_factors
            ) / total_weight
            risk_score = round(min(100.0, weighted_score + (1 - completeness) * 8), 2)
            if risk_score <= 24:
                risk_cat = "LOW"
            elif risk_score <= 49:
                risk_cat = "MEDIUM"
            elif risk_score <= 74:
                risk_cat = "HIGH"
            else:
                risk_cat = "CRITICAL"

        risk_id = f"RISK-{eid}-{risk_counter:06d}"
        risk_rows.append({
            "risk_id": risk_id,
            "student_id": sid,
            "enrollment_id": eid,
            "assessment_timestamp": datetime(2026, 7, 1, 10, 0, 0).isoformat(),
            "cutoff_date": CUTOFF.isoformat(),
            "risk_score": risk_score if risk_score is not None else "",
            "risk_category": risk_cat,
            "factor_scores": json.dumps(factor_scores),
            "factor_weights": json.dumps(risk_weights),
            "reasons": json.dumps([
                f"Attendance: {attended}/{effective} sessions attended; {approved} approved absences excluded",
                f"Academic: {len(graded)} graded assessment(s), risk factor {f_acad}",
                f"Performance trend risk factor: {f_trend}",
                f"LMS engagement risk factor: {f_lms}",
                f"Support history: {len(cases)} case(s), {open_cases} open, {critical_cases} critical",
            ]),
            "data_completeness": round(completeness, 2),
            "model_version": "v1.0",
            "is_anomaly": False,
        })
        risk_counter += 1
    _write_csv(risk_rows, CSV_DIR / "risk_assessments.csv")
    print(f"    {len(risk_rows)} risk assessments")

    # ── 12. Interventions (triggered by HIGH/CRITICAL risk) ─────────────────
    print("  Generating interventions...")
    int_rows = []
    int_counter = 1
    high_risk_enrs = [(r["risk_id"], r["student_id"], r["enrollment_id"])
                       for r in risk_rows if r["risk_category"] in ("HIGH", "CRITICAL")]
    for risk_id_val, sid, eid in high_risk_enrs[:min(len(high_risk_enrs), N_ENROLLMENTS // 5)]:
        itype = rng.choice(["ATTENDANCE_COUNSELLING", "ACADEMIC_TUTORING",
                             "INSTRUCTOR_MEETING", "ENGAGEMENT_SUPPORT",
                             "ADVISOR_REVIEW", "PERSONALIZED_PLAN"])
        staff_idx = int(rng.integers(1, N_STAFF + 1))
        trigger = CUTOFF
        start = trigger + timedelta(days=int(rng.integers(1, 10)))
        due   = start + timedelta(days=int(rng.integers(14, 42)))
        status = rng.choice(["RECOMMENDED","APPROVED","ASSIGNED","IN_PROGRESS","COMPLETED","CANCELLED"],
                              p=[0.1, 0.1, 0.15, 0.25, 0.30, 0.10])
        comp_date = ""
        if status == "COMPLETED":
            comp_date = (start + timedelta(days=int(rng.integers(10, 30)))).isoformat()
        int_rows.append({
            "intervention_id": int_id(int_counter),
            "student_id": sid,
            "enrollment_id": eid,
            "case_id": "",
            "risk_assessment_id": risk_id_val,
            "intervention_type": itype,
            "trigger_date": trigger.isoformat(),
            "assigned_staff_id": stf_id(staff_idx + 4),
            "start_date": start.isoformat(),
            "due_date": due.isoformat(),
            "completion_date": comp_date,
            "intervention_status": status,
            "expected_outcome": "Improvement in academic performance or attendance",
            "actual_outcome": "Student showed improvement" if status == "COMPLETED" else "",
        })
        int_counter += 1
    _write_csv(int_rows, CSV_DIR / "interventions.csv")
    print(f"    {len(int_rows)} interventions")
    normal_risk_by_enrollment = {risk["enrollment_id"]: risk for risk in risk_rows}

    # ── 13. Future outcomes ─────────────────────────────────────────────────
    print("  Generating outcomes...")
    out_rows = []
    out_counter = 1
    attendance_by_enrollment = {}
    for event in attendance_rows:
        attendance_by_enrollment.setdefault(event["enrollment_id"], []).append(event)
    lms_by_enrollment = {}
    for activity in lms_rows:
        lms_by_enrollment.setdefault(activity["enrollment_id"], []).append(
            datetime.fromisoformat(activity["activity_timestamp"])
        )
    intervention_by_enrollment = {
        row["enrollment_id"]: row["intervention_id"]
        for row in int_rows if row["enrollment_id"]
    }

    def attendance_rates(start_date, end_date):
        rates = {}
        for enrollment_id, records in attendance_by_enrollment.items():
            events = [
                event for event in records
                if date.fromisoformat(event["attendance_date"]) <= end_date
                and (start_date is None or date.fromisoformat(event["attendance_date"]) >= start_date)
            ]
            approved_count = sum(event["attendance_status"] == "APPROVED_ABSENCE" for event in events)
            effective_count = len(events) - approved_count
            if len(events) >= 2 and effective_count:
                attended_count = sum(
                    event["attendance_status"] in ("PRESENT", "LATE") for event in events
                )
                rates[enrollment_id] = attended_count / effective_count
        return rates

    def academic_averages(start_date, end_date):
        averages = {}
        for enrollment_id, records in graded_all_by_enrollment.items():
            scores = [
                score for assessment_date, score, _ in records
                if assessment_date <= end_date
                and (start_date is None or assessment_date >= start_date)
            ]
            if scores:
                averages[enrollment_id] = sum(scores) / len(scores)
        return averages

    def engagement_rates(start_date, end_date):
        rates = {enrollment_id: 0.0 for enrollment_id in enr_map}
        days = max(1, (end_date - start_date).days) if start_date else 180
        weeks = max(1, days / 7)
        for enrollment_id, timestamps in lms_by_enrollment.items():
            count = sum(
                timestamp.date() <= end_date
                and (start_date is None or timestamp.date() >= start_date)
                for timestamp in timestamps
            )
            rates[enrollment_id] = count / weeks
        return rates

    baseline_attendance = attendance_rates(None, CUTOFF)
    future_attendance = attendance_rates(EVAL_START, EVAL_END)
    baseline_academic = academic_averages(None, CUTOFF)
    future_academic = academic_averages(EVAL_START, EVAL_END)
    baseline_engagement = engagement_rates(None, CUTOFF)
    future_engagement = engagement_rates(EVAL_START, EVAL_END)

    # Sample 30% of active enrollments for outcomes
    sample_enrs = rng.choice(active_enr_ids, size=min(len(active_enr_ids), len(active_enr_ids)//3 + 1), replace=False)
    for eid2 in sample_enrs:
        m = enr_map[eid2]
        sid = m["student_id"]
        risk_match = normal_risk_by_enrollment.get(eid2)
        base_risk = float(risk_match["risk_score"]) if risk_match and risk_match["risk_score"] != "" else None
        base_att = baseline_attendance.get(eid2)
        base_acad = baseline_academic.get(eid2)
        base_lms = baseline_engagement.get(eid2)
        fut_att = future_attendance.get(eid2)
        fut_acad = future_academic.get(eid2)
        fut_lms = future_engagement.get(eid2)
        att_chg = round((fut_att - base_att) * 100, 2) if (fut_att is not None and base_att is not None) else None
        acad_chg = round(fut_acad - base_acad, 2) if (fut_acad is not None and base_acad is not None) else None
        lms_chg = round((fut_lms - base_lms) * 10, 2) if (fut_lms is not None and base_lms is not None) else None
        changes = [c for c in (att_chg, acad_chg, lms_chg) if c is not None]
        if not changes:
            label = "INSUFFICIENT_DATA"
        else:
            avg_chg = sum(changes) / len(changes)
            improved = sum(change > 5 for change in changes)
            declined = sum(change < -5 for change in changes)
            if improved >= 2 or avg_chg > 5:
                label = "IMPROVED"
            elif declined >= 2 or avg_chg < -5:
                label = "DECLINED"
            else:
                label = "STABLE"
        out_rows.append({
            "outcome_id": out_id(out_counter),
            "student_id": sid,
            "enrollment_id": eid2,
            "intervention_id": intervention_by_enrollment.get(eid2, ""),
            "evaluation_period_start": EVAL_START.isoformat(),
            "evaluation_period_end": EVAL_END.isoformat(),
            "baseline_risk_score": base_risk if base_risk is not None else "",
            "future_risk_score": "",
            "academic_performance_change": acad_chg if acad_chg is not None else "",
            "attendance_change": att_chg if att_chg is not None else "",
            "engagement_change": lms_chg if lms_chg is not None else "",
            "outcome_label": label,
            "evaluation_date": EVAL_END.isoformat(),
        })
        out_counter += 1
    _write_csv(out_rows, CSV_DIR / "outcomes.csv")
    print(f"    {len(out_rows)} outcomes")

    # ── 14. Ground Truth and injected anomalies ────────────────────────────
    print("  Generating ground truth and injecting labelled anomalies...")
    gt_rows = []
    gt_counter = 1
    for risk in risk_rows[:min(len(risk_rows), 1000)]:
        gt_rows.append({
            "gt_id": gt_id(gt_counter), "student_id": risk["student_id"],
            "risk_id": risk["risk_id"], "expected_risk_category": risk["risk_category"],
            "expected_outcome_label": "", "expected_anomaly_detected": False,
            "evaluation_reference": f"Generated by generate_data.py seed={seed}",
            "notes": "Normal production record",
        })
        gt_counter += 1
    for outcome in out_rows:
        gt_rows.append({
            "gt_id": gt_id(gt_counter), "student_id": outcome["student_id"],
            "risk_id": "", "expected_risk_category": "",
            "expected_outcome_label": outcome["outcome_label"],
            "expected_anomaly_detected": False,
            "evaluation_reference": f"Outcome {outcome['outcome_id']}",
            "notes": "Future outcome label — not used as model input",
        })
        gt_counter += 1

    risk_by_enrollment = normal_risk_by_enrollment
    assessment_dates = {
        assessment["assessment_id"]: date.fromisoformat(assessment["assessment_date"])
        for assessment in assessment_rows
    }
    future_result_enrollments = {
        result["enrollment_id"] for result in result_rows
        if assessment_dates[result["assessment_id"]] > date(2026, 6, 1)
    }
    temporal_base = next(
        risk for risk in risk_rows if risk["enrollment_id"] in future_result_enrollments
    )
    temporal_anomaly = dict(temporal_base)
    temporal_anomaly.update({
        "risk_id": "RISK-2026-ANOM-000001",
        "is_anomaly": True,
        "model_version": "v0.9-BUGGY",
        "assessment_timestamp": datetime(2026, 6, 15, 10, 0).isoformat(),
        "cutoff_date": "2026-06-01",
        "reasons": json.dumps(["Used assessment data dated after the risk cutoff"]),
    })
    risk_rows.append(temporal_anomaly)

    wrong_denominator_base = None
    for enrollment_id, records in attendance_by_enrollment.items():
        risk = normal_risk_by_enrollment.get(enrollment_id)
        if not risk:
            continue
        eligible_records = [
            event for event in records
            if date.fromisoformat(event["attendance_date"]) <= CUTOFF
        ]
        if (
            any(event["attendance_status"] == "APPROVED_ABSENCE" for event in eligible_records)
            and any(event["attendance_status"] in ("PRESENT", "LATE") for event in eligible_records)
        ):
            wrong_denominator_base = risk
            break
    if wrong_denominator_base is None:
        raise RuntimeError("Unable to create the approved-absence denominator anomaly")
    wrong_enrollment_id = wrong_denominator_base["enrollment_id"]
    wrong_events = [
        event for event in attendance_by_enrollment[wrong_enrollment_id]
        if date.fromisoformat(event["attendance_date"]) <= CUTOFF
    ]
    wrong_total = len(wrong_events)
    wrong_approved = sum(event["attendance_status"] == "APPROVED_ABSENCE" for event in wrong_events)
    wrong_attended = sum(event["attendance_status"] in ("PRESENT", "LATE") for event in wrong_events)
    wrong_denominator_anomaly = dict(wrong_denominator_base)
    wrong_scores = json.loads(wrong_denominator_anomaly["factor_scores"])
    wrong_scores["attendance"] = round((1 - wrong_attended / wrong_total) * 100, 2)
    wrong_denominator_anomaly.update({
        "risk_id": "RISK-2026-ANOM-000002",
        "is_anomaly": True,
        "model_version": "v0.9-BUGGY",
        "factor_scores": json.dumps(wrong_scores),
        "reasons": json.dumps(["Attendance denominator incorrectly included approved absences"]),
    })
    risk_rows.append(wrong_denominator_anomaly)

    lifecycle_anomaly = {
        "anomaly_type": "LIFECYCLE_INCONSISTENCY",
        "student_id": lifecycle_anomaly_student,
        "enrollment_id": lifecycle_enrollment_id,
        "enrollment_status": "ACTIVE",
        "student_status": "WITHDRAWN",
    }

    intervention_risk = risk_by_enrollment[lifecycle_enrollment_id]
    intervention_anomaly = {
        "intervention_id": "INT-2026-ANOM-000001",
        "student_id": lifecycle_anomaly_student,
        "enrollment_id": lifecycle_enrollment_id,
        "case_id": "",
        "risk_assessment_id": intervention_risk["risk_id"],
        "intervention_type": "ADVISOR_REVIEW",
        "trigger_date": CUTOFF.isoformat(),
        "assigned_staff_id": stf_id(5),
        "start_date": (CUTOFF - timedelta(days=9)).isoformat(),
        "due_date": (CUTOFF + timedelta(days=30)).isoformat(),
        "completion_date": "",
        "intervention_status": "IN_PROGRESS",
        "expected_outcome": "Chronology anomaly fixture",
        "actual_outcome": "",
    }
    int_rows.append(intervention_anomaly)

    missing_base = risk_by_enrollment[missing_data_enrollment]
    missing_anomaly = dict(missing_base)
    missing_scores = json.loads(missing_anomaly["factor_scores"])
    missing_scores["academic_performance"] = 78.0
    missing_anomaly.update({
        "risk_id": "RISK-2026-ANOM-000003",
        "is_anomaly": True,
        "model_version": "v0.8-BUGGY",
        "factor_scores": json.dumps(missing_scores),
        "reasons": json.dumps(["Missing assessment result was incorrectly treated as a failed score"]),
    })
    risk_rows.append(missing_anomaly)

    anomaly_rows = [
        {"anomaly_type": "TEMPORAL_LEAKAGE", "risk_assessment": temporal_anomaly},
        {"anomaly_type": "WRONG_DENOMINATOR", "risk_assessment": wrong_denominator_anomaly},
        lifecycle_anomaly,
        {"anomaly_type": "INTERVENTION_PRECEDES_TRIGGER", "intervention": intervention_anomaly},
        {"anomaly_type": "MISSING_DATA_AS_FAILURE", "risk_assessment": missing_anomaly},
    ]
    anomaly_labels = [
        ("TEMPORAL_LEAKAGE", temporal_anomaly["student_id"], temporal_anomaly["risk_id"]),
        ("WRONG_DENOMINATOR", wrong_denominator_anomaly["student_id"], wrong_denominator_anomaly["risk_id"]),
        ("LIFECYCLE_INCONSISTENCY", lifecycle_anomaly_student, ""),
        ("INTERVENTION_PRECEDES_TRIGGER", intervention_anomaly["student_id"], ""),
        ("MISSING_DATA_AS_FAILURE", missing_anomaly["student_id"], missing_anomaly["risk_id"]),
    ]
    for anomaly_type, student_id, risk_id in anomaly_labels:
        gt_rows.append({
            "gt_id": gt_id(gt_counter), "student_id": student_id, "risk_id": risk_id,
            "expected_risk_category": "", "expected_outcome_label": "",
            "expected_anomaly_detected": True,
            "evaluation_reference": anomaly_type,
            "notes": "Injected anomaly is labelled ground truth and excluded from model inputs",
        })
        gt_counter += 1

    _write_csv(risk_rows, CSV_DIR / "risk_assessments.csv")
    _write_csv(int_rows, CSV_DIR / "interventions.csv")
    _write_csv(gt_rows, GT_DIR / "ground_truth.csv")
    with open(GT_DIR / "ground_truth.json", "w", encoding="utf-8") as f:
        json.dump(gt_rows, f, indent=2)
    with open(VAL_DIR / "anomaly_records.json", "w", encoding="utf-8") as f:
        json.dump(anomaly_rows, f, indent=2)
    print(f"    {len(anomaly_rows)} labelled anomaly records included in source exports")

    # ── 16. Data Quality Issue records ──────────────────────────────────────
    dq_rows = [
        {"issue_id": "DQI-000001", "issue_type": "TEMPORAL_LEAKAGE", "affected_entity": "RiskAssessment",
         "affected_record_id": temporal_anomaly["risk_id"],
         "expected_behavior": "Risk score uses only data with assessment_date <= cutoff_date",
         "observed_behavior": f"Risk score {temporal_anomaly['risk_id']} used post-cutoff assessment data",
         "ground_truth_label": "ANOMALY_CONFIRMED", "detection_status": "DETECTED",
         "explanation": f"Temporal leakage: assessment data after 2026-06-01 used by {temporal_anomaly['risk_id']}",
         "severity": "CRITICAL", "is_injected_anomaly": True},
        {"issue_id": "DQI-000002", "issue_type": "WRONG_DENOMINATOR", "affected_entity": "RiskAssessment",
         "affected_record_id": wrong_denominator_anomaly["risk_id"],
         "expected_behavior": "Attendance rate excludes approved_absence from denominator",
         "observed_behavior": f"Recorded attendance factor uses {wrong_attended}/{wrong_total} rather than {wrong_attended}/{wrong_total - wrong_approved}",
         "ground_truth_label": "ANOMALY_CONFIRMED", "detection_status": "DETECTED",
         "explanation": "Attendance risk incorrectly includes approved absences in its denominator",
         "severity": "HIGH", "is_injected_anomaly": True},
        {"issue_id": "DQI-000003", "issue_type": "LIFECYCLE_INCONSISTENCY", "affected_entity": "Student",
         "affected_record_id": lifecycle_anomaly_student,
         "expected_behavior": "WITHDRAWN student should have no ACTIVE enrollments",
         "observed_behavior": f"WITHDRAWN student {lifecycle_anomaly_student} has ACTIVE enrollment {lifecycle_enrollment_id}",
         "ground_truth_label": "ANOMALY_CONFIRMED", "detection_status": "DETECTED",
         "explanation": "Lifecycle rule violation: withdrawn student retains active enrollment",
         "severity": "HIGH", "is_injected_anomaly": True},
        {"issue_id": "DQI-000004", "issue_type": "INTERVENTION_PRECEDES_TRIGGER", "affected_entity": "Intervention",
         "affected_record_id": intervention_anomaly["intervention_id"],
         "expected_behavior": "start_date >= trigger_date",
         "observed_behavior": f"start_date {intervention_anomaly['start_date']} precedes trigger_date {intervention_anomaly['trigger_date']}",
         "ground_truth_label": "ANOMALY_CONFIRMED", "detection_status": "DETECTED",
         "explanation": "Chronological impossibility: intervention started before it was triggered",
         "severity": "CRITICAL", "is_injected_anomaly": True},
        {"issue_id": "DQI-000005", "issue_type": "MISSING_DATA_AS_FAILURE", "affected_entity": "RiskAssessment",
         "affected_record_id": missing_anomaly["risk_id"],
         "expected_behavior": "NULL marks excluded from academic average",
         "observed_behavior": f"academic_performance score 78.0 on {missing_anomaly['risk_id']} despite a missing pre-cutoff result",
         "ground_truth_label": "ANOMALY_CONFIRMED", "detection_status": "DETECTED",
         "explanation": "Missing data incorrectly treated as zero score, inflating risk",
         "severity": "HIGH", "is_injected_anomaly": True},
    ]
    _write_csv(dq_rows, CSV_DIR / "data_quality_issues.csv")

    row_counts = {
        "staff": len(staff_rows),
        "students": len(student_rows), "courses": len(course_rows),
        "enrollments": len(enrollment_rows), "assessments": len(assessment_rows),
        "attendance_events": len(attendance_rows), "assessment_results": len(result_rows),
        "lms_activities": len(lms_rows), "support_cases": len(case_rows),
        "interventions": len(int_rows), "risk_assessments": len(risk_rows),
        "outcomes": len(out_rows), "ground_truth": len(gt_rows),
        "data_quality_issues": len(dq_rows),
    }

    for csvfile in sorted(CSV_DIR.glob("*.csv")):
        with open(csvfile, newline="", encoding="utf-8") as source:
            rows = list(csv.DictReader(source))
        json_path = JSON_DIR / f"{csvfile.stem}.json"
        with open(json_path, "w", encoding="utf-8") as destination:
            json.dump(rows, destination, indent=2, ensure_ascii=False)
    _write_sql_seed()

    # ── 17. Manifest ────────────────────────────────────────────────────────
    print("  Writing manifest...")
    manifest = {
        "generator_version": "1.1.0",
        "seed": seed,
        "scale": scale,
        "generation_timestamp": datetime.utcnow().isoformat(),
        "academic_year": ACADEMIC_YEAR,
        "academic_start": ACADEMIC_START.isoformat(),
        "academic_end": ACADEMIC_END.isoformat(),
        "risk_cutoff_date": CUTOFF.isoformat(),
        "entity_counts": row_counts,
        "file_checksums": {},
    }
    for directory, prefix in ((CSV_DIR, "csv"), (JSON_DIR, "json")):
        for path in sorted(directory.glob("*")):
            if path.is_file():
                manifest["file_checksums"][f"{prefix}/{path.name}"] = sha256(path)
    for path, prefix in (
        (GT_DIR / "ground_truth.csv", "ground_truth"),
        (GT_DIR / "ground_truth.json", "ground_truth"),
        (VAL_DIR / "anomaly_records.json", "validation"),
        (DATA_DIR / "generated" / "sql" / "seed.sql", "sql"),
    ):
        manifest["file_checksums"][f"{prefix}/{path.name}"] = sha256(path)
    with open(MAN_DIR / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    print("\nData generation complete.")
    print(f"   Students:          {len(student_rows)}")
    print(f"   Courses:           {len(course_rows)}")
    print(f"   Enrollments:       {len(enrollment_rows)}")
    print(f"   Attendance events: {len(attendance_rows)}")
    print(f"   Assessment results:{len(result_rows)}")
    print(f"   LMS activities:    {len(lms_rows)}")
    print(f"   Risk assessments:  {len(risk_rows)}")
    print(f"   Interventions:     {len(int_rows)}")
    print(f"   Outcomes:          {len(out_rows)}")
    print(f"   Ground truth:      {len(gt_rows)}")
    print(f"   Anomalies injected: 5")
    print(f"\n   CSV files:   {CSV_DIR}")
    print(f"   JSON files:  {JSON_DIR}")
    print(f"   SQL seed:    {DATA_DIR / 'generated' / 'sql' / 'seed.sql'}")
    print(f"   Ground truth:{GT_DIR}")
    print(f"   Manifest:    {MAN_DIR / 'manifest.json'}")
    return manifest


def _write_sql_seed():
    sql_dir = DATA_DIR / "generated" / "sql"
    sql_dir.mkdir(parents=True, exist_ok=True)
    path = sql_dir / "seed.sql"
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        output.write("-- Generated synthetic seed data; apply after creating the database schema.\n")
        output.write("BEGIN;\n")
        for table, filename, columns in SQL_EXPORTS:
            source_path = GT_DIR / filename if table == "ground_truth" else CSV_DIR / filename
            with open(source_path, newline="", encoding="utf-8") as source:
                rows = csv.DictReader(source)
                batch = []
                for row in rows:
                    values = ", ".join(_sql_literal(column, row.get(column, "")) for column in columns)
                    batch.append(f"({values})")
                    if len(batch) == 500:
                        output.write(
                            f"INSERT INTO {table} ({', '.join(columns)}) VALUES\n"
                            + ",\n".join(batch) + ";\n"
                        )
                        batch.clear()
                if batch:
                    output.write(
                        f"INSERT INTO {table} ({', '.join(columns)}) VALUES\n"
                        + ",\n".join(batch) + ";\n"
                    )
        output.write("COMMIT;\n")


def _sql_literal(column, value):
    if value in (None, ""):
        return "NULL"
    if column in SQL_BOOLEAN_COLUMNS:
        return "TRUE" if str(value).lower() in ("true", "1", "yes") else "FALSE"
    if column in SQL_NUMERIC_COLUMNS:
        return str(float(value)) if "." in str(value) else str(int(value))
    if column in SQL_DATE_COLUMNS:
        return f"DATE '{value}'"
    if column in SQL_DATETIME_COLUMNS:
        timestamp = str(value).replace("T", " ", 1)
        return f"TIMESTAMP '{timestamp}'"
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def _write_csv(rows, path):
    if not rows:
        return
    path = Path(path)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic academic data")
    parser.add_argument("--scale", choices=["starter", "full"], default="starter")
    parser.add_argument("--seed",  type=int, default=20261022)
    parser.add_argument("--output-dir", type=Path, help="write all data under this directory")
    args = parser.parse_args()
    generate(args.scale, args.seed, args.output_dir)
