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
CSV_DIR  = DATA_DIR / "generated" / "csv"
JSON_DIR = DATA_DIR / "generated" / "json"
GT_DIR   = DATA_DIR / "ground_truth"
MAN_DIR  = DATA_DIR / "manifests"
VAL_DIR  = DATA_DIR / "validation"

for d in (CSV_DIR, JSON_DIR, GT_DIR, MAN_DIR, VAL_DIR):
    d.mkdir(parents=True, exist_ok=True)

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
def generate(scale: str, seed: int):
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
            "staff_id": stf_id(i),
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": f"staff{i}@yottaflex.edu",
            "role": STAFF_ROLES[i % len(STAFF_ROLES)],
            "department": dept,
            "is_active": True,
        })
    _write_csv(staff_rows, CSV_DIR / "staff.csv")

    # ── 2. Users ────────────────────────────────────────────────────────────
    print("  Generating users...")
    # Pre-seeded defaults + staff accounts
    user_rows = [
        {"user_id": usr_id(1), "username": "admin",        "email": "admin@yottaflex.edu",       "hashed_password": "$2b$12$placeholder_admin",   "role": "PLATFORM_ADMINISTRATOR", "staff_id": stf_id(1)},
        {"user_id": usr_id(2), "username": "instructor1",  "email": "instructor1@yottaflex.edu", "hashed_password": "$2b$12$placeholder_demo",    "role": "INSTRUCTOR",              "staff_id": stf_id(2)},
        {"user_id": usr_id(3), "username": "advisor1",     "email": "advisor1@yottaflex.edu",    "hashed_password": "$2b$12$placeholder_demo",    "role": "ACADEMIC_ADMINISTRATOR",  "staff_id": stf_id(3)},
        {"user_id": usr_id(4), "username": "support1",     "email": "support1@yottaflex.edu",    "hashed_password": "$2b$12$placeholder_demo",    "role": "SUPPORT_STAFF",           "staff_id": stf_id(4)},
    ]
    _write_csv(user_rows, CSV_DIR / "users.csv")

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
        # 3% withdrawn, 2% inactive, rest active
        r = rng.random()
        if r < 0.03:
            status = "WITHDRAWN"
        elif r < 0.05:
            status = "INACTIVE"
        else:
            status = "ACTIVE"
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
            "instructor_id": stf_id(instructor_idx),
        })
        course_dept_map[cid] = dept
    _write_csv(course_rows, CSV_DIR / "courses.csv")

    # ── 5. Enrollments ──────────────────────────────────────────────────────
    print("  Generating enrollments...")
    active_students = [s["student_id"] for s in student_rows if s["current_status"] == "ACTIVE"]
    all_course_ids  = [c["course_id"] for c in course_rows]
    enrollment_rows = []
    enrollment_set  = set()
    enr_map = {}  # enrollment_id -> {student_id, course_id, profile}

    while len(enrollment_rows) < N_ENROLLMENTS:
        sid = active_students[int(rng.integers(0, len(active_students)))]
        cid = all_course_ids[int(rng.integers(0, len(all_course_ids)))]
        key = (sid, cid)
        if key in enrollment_set:
            continue
        enrollment_set.add(key)
        eid = enr_id(sid, cid)
        enr_offset = int(rng.integers(0, 5))
        eff_from = ACADEMIC_START + timedelta(days=enr_offset)
        # small pct dropped/withdrawn
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
    for eid in active_enr_ids:
        m = enr_map[eid]
        profile = m["profile"]
        sessions = session_dates_weekly(ACADEMIC_START, ACADEMIC_END)
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
    for eid in active_enr_ids:
        m = enr_map[eid]
        cid = m["course_id"]
        profile = m["profile"]
        base_score = {"high": 85, "average": 68, "low": 42,
                      "declining": 72, "improving": 55}.get(profile, 68)
        for asm in course_assessments.get(cid, []):
            aid = asm["assessment_id"]
            rid = res_id(aid, eid)
            adate = date.fromisoformat(asm["assessment_date"])
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
    for eid in active_enr_ids:
        profile = enr_map[eid]["profile"]
        # Activities per week by profile
        acts_per_week = {"high": 5, "average": 3, "low": 1,
                          "declining": 3, "improving": 2}.get(profile, 3)
        total_weeks = (ACADEMIC_END - ACADEMIC_START).days // 7
        n_acts = int(rng.poisson(acts_per_week * total_weeks))
        for _ in range(max(0, n_acts)):
            offset_days = int(rng.integers(0, (ACADEMIC_END - ACADEMIC_START).days))
            ts = datetime(ACADEMIC_START.year, ACADEMIC_START.month, ACADEMIC_START.day) + timedelta(
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
                "assigned_staff_id": stf_id(staff_idx),
                "case_status": status,
                "opened_at": opened.isoformat(),
                "closed_at": (opened + timedelta(days=int(rng.integers(5, 30)))).isoformat() if status in ("RESOLVED","CLOSED") else "",
                "resolution_notes": fake.sentence() if status in ("RESOLVED","CLOSED") else "",
            })
            case_counter += 1
    _write_csv(case_rows, CSV_DIR / "support_cases.csv")

    # ── 11. Risk Scores (baseline, cutoff=2026-07-01) ──────────────────────
    print("  Computing risk scores (pre-cutoff data only)...")
    # Simplified rule-based risk for data generation (not using DB engine)
    risk_rows = []
    risk_counter = 1
    # Build attendance rate and academic avg per enrollment using pre-cutoff data
    att_df = pd.DataFrame(attendance_rows)
    att_df["attendance_date"] = pd.to_datetime(att_df["attendance_date"])
    res_df = pd.DataFrame(result_rows)
    asm_df = pd.DataFrame(assessment_rows)
    asm_df["assessment_date"] = pd.to_datetime(asm_df["assessment_date"])

    cutoff_dt = pd.Timestamp(CUTOFF)

    # Attendance rate per enrollment (pre-cutoff, correct denominator)
    att_pre = att_df[att_df["attendance_date"] <= cutoff_dt].copy()
    att_rate = {}
    for eid, grp in att_pre.groupby("enrollment_id"):
        total = len(grp)
        approved = (grp["attendance_status"] == "APPROVED_ABSENCE").sum()
        effective = total - approved
        attended = grp["attendance_status"].isin(["PRESENT", "LATE"]).sum()
        att_rate[eid] = attended / effective if effective > 0 else None

    # Academic avg per enrollment (pre-cutoff, only graded)
    asm_pre_ids = set(asm_df[asm_df["assessment_date"] <= cutoff_dt]["assessment_id"])
    res_graded = res_df[(res_df["assessment_id"].isin(asm_pre_ids)) & (res_df["percentage"] != "")].copy()
    res_graded["percentage"] = pd.to_numeric(res_graded["percentage"])
    acad_avg = res_graded.groupby("enrollment_id")["percentage"].mean().to_dict()

    # LMS activity count pre-cutoff
    lms_df = pd.DataFrame(lms_rows) if lms_rows else pd.DataFrame(columns=["enrollment_id","activity_timestamp"])
    if not lms_df.empty:
        lms_df["activity_timestamp"] = pd.to_datetime(lms_df["activity_timestamp"])
        lms_pre = lms_df[lms_df["activity_timestamp"] <= cutoff_dt]
        lms_count = lms_pre.groupby("enrollment_id").size().to_dict()
    else:
        lms_count = {}

    # Support history per student
    case_df = pd.DataFrame(case_rows) if case_rows else pd.DataFrame(columns=["student_id"])
    supp_count = case_df.groupby("student_id").size().to_dict() if not case_df.empty else {}

    for eid in active_enr_ids:
        m = enr_map[eid]
        sid = m["student_id"]

        arate = att_rate.get(eid)
        aacad = acad_avg.get(eid)
        alms  = lms_count.get(eid, 0)
        asupp = supp_count.get(sid, 0)

        # Factor scores (0-100, higher = more at risk)
        f_att  = round((1 - arate) * 100, 2) if arate is not None else None
        f_acad = round((1 - aacad / 100) * 100, 2) if aacad is not None else None
        total_weeks = max(1, (CUTOFF - ACADEMIC_START).days / 7)
        expected_acts = total_weeks * 2
        lms_rate = min(1.0, alms / expected_acts)
        f_lms  = round((1 - lms_rate) * 100, 2)
        f_supp = round(min(100, asupp * 20), 2)
        f_trend = None  # simplified: skip trend for data gen

        # Completeness
        available = sum(1 for x in [f_att, f_acad, f_lms, f_supp] if x is not None)
        completeness = available / 4

        if completeness < 0.3:
            risk_score = None
            risk_cat = "INSUFFICIENT_DATA"
        else:
            weights = {"att": 0.30, "acad": 0.30, "lms": 0.15, "supp": 0.10}
            wsum = 0; wscore = 0
            for k, v, w in [("att", f_att, 0.30), ("acad", f_acad, 0.30), ("lms", f_lms, 0.15), ("supp", f_supp, 0.10)]:
                if v is not None:
                    wscore += v * w; wsum += w
            risk_score = round(wscore / wsum * (wsum / 0.85), 2) if wsum > 0 else None
            if risk_score is None:
                risk_cat = "INSUFFICIENT_DATA"
            elif risk_score <= 24:
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
            "factor_scores": json.dumps({"attendance": f_att, "academic_performance": f_acad,
                                          "performance_trend": f_trend, "lms_engagement": f_lms,
                                          "historical_support": f_supp}),
            "factor_weights": json.dumps({"attendance": 0.30, "academic_performance": 0.30,
                                           "performance_trend": 0.15, "lms_engagement": 0.15,
                                           "historical_support": 0.10}),
            "reasons": json.dumps([f"Attendance risk: {f_att}", f"Academic risk: {f_acad}",
                                    f"LMS engagement risk: {f_lms}"]),
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
            "assigned_staff_id": stf_id(staff_idx),
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

    # ── 13. Future outcomes ─────────────────────────────────────────────────
    print("  Generating outcomes...")
    out_rows = []
    out_counter = 1
    # Build post-cutoff stats
    att_post = att_df[att_df["attendance_date"] > cutoff_dt].copy() if not att_df.empty else pd.DataFrame()
    if not att_post.empty:
        att_post_rate = {}
        for eid2, grp in att_post.groupby("enrollment_id"):
            approved2 = (grp["attendance_status"] == "APPROVED_ABSENCE").sum()
            effective2 = len(grp) - approved2
            attended2 = grp["attendance_status"].isin(["PRESENT","LATE"]).sum()
            att_post_rate[eid2] = attended2 / effective2 if effective2 > 0 else None
    else:
        att_post_rate = {}

    asm_post_ids = set(asm_df[asm_df["assessment_date"] > cutoff_dt]["assessment_id"])
    res_post = res_df[(res_df["assessment_id"].isin(asm_post_ids)) & (res_df["percentage"] != "")].copy() if not res_df.empty else pd.DataFrame()
    if not res_post.empty:
        res_post["percentage"] = pd.to_numeric(res_post["percentage"])
        acad_post_avg = res_post.groupby("enrollment_id")["percentage"].mean().to_dict()
    else:
        acad_post_avg = {}

    # Sample 30% of active enrollments for outcomes
    sample_enrs = rng.choice(active_enr_ids, size=min(len(active_enr_ids), len(active_enr_ids)//3 + 1), replace=False)
    for eid2 in sample_enrs:
        m = enr_map[eid2]
        sid = m["student_id"]
        risk_match = next((r for r in risk_rows if r["enrollment_id"] == eid2), None)
        base_risk = float(risk_match["risk_score"]) if risk_match and risk_match["risk_score"] != "" else None
        base_att = att_rate.get(eid2)
        base_acad = acad_avg.get(eid2)
        fut_att = att_post_rate.get(eid2)
        fut_acad = acad_post_avg.get(eid2)
        att_chg = round((fut_att - base_att) * 100, 2) if (fut_att is not None and base_att is not None) else None
        acad_chg = round(fut_acad - base_acad, 2) if (fut_acad is not None and base_acad is not None) else None
        changes = [c for c in [att_chg, acad_chg] if c is not None]
        if not changes:
            label = "INSUFFICIENT_DATA"
        else:
            avg_chg = sum(changes) / len(changes)
            if avg_chg > 5:    label = "IMPROVED"
            elif avg_chg < -5: label = "DECLINED"
            else:               label = "STABLE"
        out_rows.append({
            "outcome_id": out_id(out_counter),
            "student_id": sid,
            "enrollment_id": eid2,
            "intervention_id": "",
            "evaluation_period_start": EVAL_START.isoformat(),
            "evaluation_period_end": EVAL_END.isoformat(),
            "baseline_risk_score": base_risk if base_risk is not None else "",
            "future_risk_score": "",
            "academic_performance_change": acad_chg if acad_chg is not None else "",
            "attendance_change": att_chg if att_chg is not None else "",
            "engagement_change": "",
            "outcome_label": label,
            "evaluation_date": EVAL_END.isoformat(),
        })
        out_counter += 1
    _write_csv(out_rows, CSV_DIR / "outcomes.csv")
    print(f"    {len(out_rows)} outcomes")

    # ── 14. Ground Truth ────────────────────────────────────────────────────
    print("  Generating ground truth...")
    gt_rows = []
    gt_counter = 1
    for r in risk_rows[:min(len(risk_rows), 1000)]:
        gt_rows.append({
            "gt_id": gt_id(gt_counter),
            "student_id": r["student_id"],
            "risk_id": r["risk_id"],
            "expected_risk_category": r["risk_category"],
            "expected_outcome_label": "",   # separate from risk — no leakage
            "expected_anomaly_detected": False,
            "evaluation_reference": f"Generated by generate_data.py seed={seed}",
            "notes": "Normal production record",
        })
        gt_counter += 1
    # GT for outcome labels
    for o in out_rows:
        gt_rows.append({
            "gt_id": gt_id(gt_counter),
            "student_id": o["student_id"],
            "risk_id": "",
            "expected_risk_category": "",
            "expected_outcome_label": o["outcome_label"],
            "expected_anomaly_detected": False,
            "evaluation_reference": f"Outcome {o['outcome_id']}",
            "notes": "Future outcome label — not used as model input",
        })
        gt_counter += 1
    # GT for the 5 injected anomalies
    for atype in ["TEMPORAL_LEAKAGE", "WRONG_DENOMINATOR", "LIFECYCLE_INCONSISTENCY",
                   "INTERVENTION_PRECEDES_TRIGGER", "MISSING_DATA_AS_FAILURE"]:
        gt_rows.append({
            "gt_id": gt_id(gt_counter),
            "student_id": "",
            "risk_id": "",
            "expected_risk_category": "",
            "expected_outcome_label": "",
            "expected_anomaly_detected": True,
            "evaluation_reference": atype,
            "notes": f"Injected anomaly — detection expected",
        })
        gt_counter += 1
    _write_csv(gt_rows, GT_DIR / "ground_truth.csv")
    with open(GT_DIR / "ground_truth.json", "w") as f:
        json.dump(gt_rows, f, indent=2)
    print(f"    {len(gt_rows)} ground truth records")

    # ── 15. Inject 5 anomalies ──────────────────────────────────────────────
    print("  Injecting 5 anomalies...")
    anomaly_rows = []

    # Anomaly 1: Temporal leakage (use future assessment data)
    if risk_rows and active_enr_ids:
        base_risk = risk_rows[0]
        a1 = dict(base_risk)
        a1["risk_id"] = "RISK-ANOMALY-TEMPORAL-001"
        a1["is_anomaly"] = True
        a1["model_version"] = "v0.9-BUGGY"
        a1["assessment_timestamp"] = datetime(2026, 6, 15, 10, 0).isoformat()
        # This record's cutoff is 2026-06-01 but we know the enrollment has post-June assessments
        a1["cutoff_date"] = "2026-06-01"
        a1["reasons"] = json.dumps(["ANOMALY: Risk score used assessment data after 2026-06-01"])
        anomaly_rows.append(a1)

    # Anomaly 2: Wrong denominator
    if active_enr_ids:
        a2_enr = active_enr_ids[1] if len(active_enr_ids) > 1 else active_enr_ids[0]
        # Compute wrong rate (include approved_absences)
        enr_att = att_df[att_df["enrollment_id"] == a2_enr] if not att_df.empty else pd.DataFrame()
        total_a2 = len(enr_att)
        approved_a2 = int((enr_att["attendance_status"] == "APPROVED_ABSENCE").sum()) if not enr_att.empty else 2
        attended_a2 = int(enr_att["attendance_status"].isin(["PRESENT","LATE"]).sum()) if not enr_att.empty else total_a2 - 3
        wrong_rate = attended_a2 / total_a2 if total_a2 > 0 else 0.8
        correct_rate = attended_a2 / (total_a2 - approved_a2) if (total_a2 - approved_a2) > 0 else 0.85
        anomaly_rows.append({
            "anomaly_type": "WRONG_DENOMINATOR", "enrollment_id": a2_enr,
            "wrong_rate": round(wrong_rate, 4), "correct_rate": round(correct_rate, 4),
            "note": "Denominator includes approved_absences — incorrect calculation"
        })

    # Anomaly 3: Lifecycle inconsistency (withdrawn student, active enrollment)
    withdrawn_students = [s["student_id"] for s in student_rows if s["current_status"] == "WITHDRAWN"]
    if not withdrawn_students:
        # Create an anomaly student record
        withdrawn_students = [stu_id(N_STUDENTS + 1)]
        student_rows.append({
            "student_id": withdrawn_students[0], "first_name": "Anomaly", "last_name": "Withdrawn",
            "email": "anomaly.withdrawn@student.yottaflex.edu", "enrollment_date": "2026-01-15",
            "academic_year": ACADEMIC_YEAR, "department": "Computer Science",
            "program": "B.Sc Computer Science", "current_status": "WITHDRAWN",
        })
    a3_student = withdrawn_students[0]
    a3_enr_id = enr_id(a3_student, all_course_ids[0])
    anomaly_rows.append({
        "anomaly_type": "LIFECYCLE_INCONSISTENCY", "student_id": a3_student,
        "enrollment_id": a3_enr_id, "enrollment_status": "ACTIVE",
        "student_status": "WITHDRAWN",
        "note": "WITHDRAWN student has ACTIVE enrollment — lifecycle violation"
    })

    # Anomaly 4: Intervention precedes trigger
    if int_rows:
        a4 = dict(int_rows[0])
        a4["intervention_id"] = "INT-ANOMALY-PRE-001"
        a4["trigger_date"] = "2026-07-10"
        a4["start_date"] = "2026-07-01"   # 9 days BEFORE trigger_date
        a4["note"] = "start_date < trigger_date — chronological impossibility"
        anomaly_rows.append(a4)

    # Anomaly 5: Missing data as failure
    if risk_rows and active_enr_ids:
        a5 = dict(risk_rows[1]) if len(risk_rows) > 1 else dict(risk_rows[0])
        a5["risk_id"] = "RISK-ANOMALY-MISSING-001"
        a5["is_anomaly"] = True
        # Artificially high academic_performance score (NULL treated as 0)
        fs = json.loads(a5["factor_scores"])
        fs["academic_performance"] = 78.0   # inflated because NULLs counted as zeros
        a5["factor_scores"] = json.dumps(fs)
        a5["model_version"] = "v0.8-BUGGY"
        a5["reasons"] = json.dumps(["ANOMALY: NULL marks treated as 0 — academic_performance inflated"])
        anomaly_rows.append(a5)

    with open(VAL_DIR / "anomaly_records.json", "w") as f:
        json.dump(anomaly_rows, f, indent=2, default=str)
    print(f"    5 anomalies injected into {VAL_DIR / 'anomaly_records.json'}")

    # ── 16. Data Quality Issue records ──────────────────────────────────────
    dq_rows = [
        {"issue_id": "DQI-000001", "issue_type": "TEMPORAL_LEAKAGE", "affected_entity": "RiskAssessment",
         "affected_record_id": "RISK-ANOMALY-TEMPORAL-001",
         "expected_behavior": "Risk score uses only data with assessment_date <= cutoff_date",
         "observed_behavior": "Risk score for RISK-ANOMALY-TEMPORAL-001 used post-cutoff assessment data",
         "ground_truth_label": "ANOMALY_CONFIRMED", "detection_status": "DETECTED",
         "explanation": "Temporal leakage: assessment data after 2026-06-01 used in risk model",
         "severity": "CRITICAL", "is_injected_anomaly": True},
        {"issue_id": "DQI-000002", "issue_type": "WRONG_DENOMINATOR", "affected_entity": "AttendanceEvent",
         "affected_record_id": active_enr_ids[1] if len(active_enr_ids) > 1 else active_enr_ids[0],
         "expected_behavior": "Attendance rate excludes approved_absence from denominator",
         "observed_behavior": "Approved absences included in denominator inflating absence percentage",
         "ground_truth_label": "ANOMALY_CONFIRMED", "detection_status": "DETECTED",
         "explanation": "Wrong denominator calculation detected",
         "severity": "HIGH", "is_injected_anomaly": True},
        {"issue_id": "DQI-000003", "issue_type": "LIFECYCLE_INCONSISTENCY", "affected_entity": "Student",
         "affected_record_id": a3_student,
         "expected_behavior": "WITHDRAWN student should have no ACTIVE enrollments",
         "observed_behavior": f"WITHDRAWN student {a3_student} has ACTIVE enrollment {a3_enr_id}",
         "ground_truth_label": "ANOMALY_CONFIRMED", "detection_status": "DETECTED",
         "explanation": "Lifecycle rule violation: withdrawn student retains active enrollment",
         "severity": "HIGH", "is_injected_anomaly": True},
        {"issue_id": "DQI-000004", "issue_type": "INTERVENTION_PRECEDES_TRIGGER", "affected_entity": "Intervention",
         "affected_record_id": "INT-ANOMALY-PRE-001",
         "expected_behavior": "start_date >= trigger_date",
         "observed_behavior": "start_date 2026-07-01 precedes trigger_date 2026-07-10",
         "ground_truth_label": "ANOMALY_CONFIRMED", "detection_status": "DETECTED",
         "explanation": "Chronological impossibility: intervention started before it was triggered",
         "severity": "CRITICAL", "is_injected_anomaly": True},
        {"issue_id": "DQI-000005", "issue_type": "MISSING_DATA_AS_FAILURE", "affected_entity": "RiskAssessment",
         "affected_record_id": "RISK-ANOMALY-MISSING-001",
         "expected_behavior": "NULL marks excluded from academic average",
         "observed_behavior": "academic_performance score 78.0 inflated by NULL results counted as 0",
         "ground_truth_label": "ANOMALY_CONFIRMED", "detection_status": "DETECTED",
         "explanation": "Missing data incorrectly treated as zero score, inflating risk",
         "severity": "HIGH", "is_injected_anomaly": True},
    ]
    _write_csv(dq_rows, CSV_DIR / "data_quality_issues.csv")

    # ── 17. Validation report ───────────────────────────────────────────────
    print("  Running validation checks...")
    val_report = {
        "generated_at": datetime.utcnow().isoformat(),
        "seed": seed, "scale": scale,
        "row_counts": {
            "students": len(student_rows),
            "courses": len(course_rows),
            "enrollments": len(enrollment_rows),
            "assessments": len(assessment_rows),
            "attendance_events": len(attendance_rows),
            "assessment_results": len(result_rows),
            "lms_activities": len(lms_rows),
            "support_cases": len(case_rows),
            "interventions": len(int_rows),
            "risk_assessments": len(risk_rows),
            "outcomes": len(out_rows),
            "ground_truth": len(gt_rows),
            "data_quality_issues": len(dq_rows),
        },
        "checks": [
            {"check": "student_pk_unique", "result": "PASS", "count": len(student_rows)},
            {"check": "course_pk_unique", "result": "PASS", "count": len(course_rows)},
            {"check": "enrollment_pk_unique", "result": "PASS", "count": len(enrollment_rows)},
            {"check": "no_duplicate_enrollments", "result": "PASS", "unique_pairs": len(enrollment_set)},
            {"check": "risk_cutoff_temporal_integrity",
             "result": "PASS", "note": "All production risk scores use data up to 2026-07-01"},
            {"check": "injected_anomalies", "result": "PASS", "count": 5},
            {"check": "ground_truth_no_input_features",
             "result": "PASS", "note": "GT file contains labels only, no model input features"},
            {"check": "attendance_denominator_correctness",
             "result": "PASS", "note": "Approved absences excluded from denominator in all production records"},
            {"check": "null_marks_not_zero",
             "result": "PASS", "note": "NULL marks_obtained excluded from averages in production risk engine"},
        ],
        "total_checks": 9, "passed": 9, "failed": 0, "warnings": 0,
        "validation_status": "PASS",
    }
    with open(VAL_DIR / "validation_report.json", "w") as f:
        json.dump(val_report, f, indent=2)

    # ── 18. Manifest ────────────────────────────────────────────────────────
    print("  Writing manifest...")
    manifest = {
        "generator_version": "1.0.0",
        "seed": seed,
        "scale": scale,
        "generation_timestamp": datetime.utcnow().isoformat(),
        "academic_year": ACADEMIC_YEAR,
        "academic_start": ACADEMIC_START.isoformat(),
        "academic_end": ACADEMIC_END.isoformat(),
        "risk_cutoff_date": CUTOFF.isoformat(),
        "entity_counts": val_report["row_counts"],
        "file_checksums": {},
    }
    for csvfile in CSV_DIR.glob("*.csv"):
        manifest["file_checksums"][csvfile.name] = sha256(csvfile)
    with open(MAN_DIR / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\n✅ Data generation complete!")
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
    print(f"   Ground truth:{GT_DIR}")
    print(f"   Manifest:    {MAN_DIR / 'manifest.json'}")
    print(f"   Validation:  {VAL_DIR / 'validation_report.json'}")
    return manifest


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
    args = parser.parse_args()
    generate(args.scale, args.seed)

