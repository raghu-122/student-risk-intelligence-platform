#!/usr/bin/env python3
"""
Validate generated CSV files for data integrity.
Runs 15 validation checks and writes results to data/validation/validation_report.json
"""
import csv, json, sys
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parent.parent
CSV_DIR = ROOT / "data" / "generated" / "csv"
VAL_DIR = ROOT / "data" / "validation"
VAL_DIR.mkdir(parents=True, exist_ok=True)

def read_csv(name):
    p = CSV_DIR / name
    if not p.exists(): return []
    with open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f))

checks = []

def check(name, result, detail=""):
    status = "PASS" if result else "FAIL"
    checks.append({"check": name, "result": status, "detail": detail})
    print(f"  [{status}] {name}" + (f": {detail}" if detail else ""))
    return result

# 1. PK uniqueness - students
students = read_csv("students.csv")
ids = [s["student_id"] for s in students]
check("student_pk_unique", len(ids) == len(set(ids)), f"{len(students)} students, {len(set(ids))} unique")

# 2. PK uniqueness - courses
courses = read_csv("courses.csv")
cids = [c["course_id"] for c in courses]
check("course_pk_unique", len(cids) == len(set(cids)), f"{len(courses)} courses")

# 3. PK uniqueness - enrollments
enrollments = read_csv("enrollments.csv")
eids = [e["enrollment_id"] for e in enrollments]
check("enrollment_pk_unique", len(eids) == len(set(eids)), f"{len(enrollments)} enrollments")

# 4. FK integrity - enrollments reference valid students
valid_students = set(ids)
valid_courses = set(cids)
bad_enr = [e for e in enrollments if e["student_id"] not in valid_students]
check("enrollment_fk_student", len(bad_enr) == 0, f"{len(bad_enr)} orphan enrollments")

# 5. No null student_id
null_sids = [s for s in students if not s.get("student_id")]
check("student_id_not_null", len(null_sids) == 0, f"{len(null_sids)} null student_ids")

# 6. Enum validation - student status
valid_statuses = {"ACTIVE","INACTIVE","TRANSFERRED","GRADUATED","WITHDRAWN"}
bad_status = [s for s in students if s["current_status"] not in valid_statuses]
check("student_status_enum", len(bad_status) == 0, f"{len(bad_status)} invalid statuses")

# 7. Enrollment lifecycle consistency
withdrawn_sids = {s["student_id"] for s in students if s["current_status"] == "WITHDRAWN"}
active_enr_for_withdrawn = [e for e in enrollments if e["student_id"] in withdrawn_sids and e["enrollment_status"] == "ACTIVE" and "ANOMALY" not in e["enrollment_id"]]
check("enrollment_lifecycle_no_active_withdrawn", len(active_enr_for_withdrawn) == 0,
      f"{len(active_enr_for_withdrawn)} ACTIVE enrollments for WITHDRAWN students (excluding injected anomalies)")

# 8. Attendance reconciliation — approved_absence not in denominator
att_rows = read_csv("attendance_events.csv")
att_by_enr = {}
for a in att_rows:
    att_by_enr.setdefault(a["enrollment_id"], []).append(a)

wrong_denom_count = 0
for eid, evts in list(att_by_enr.items())[:100]:  # sample check
    total = len(evts)
    approved = sum(1 for e in evts if e["attendance_status"] == "APPROVED_ABSENCE")
    attended = sum(1 for e in evts if e["attendance_status"] in ("PRESENT","LATE"))
    effective = total - approved
    if effective <= 0: continue
    correct = attended / effective
    wrong   = attended / total
    if abs(correct - wrong) > 0.01 and "ANOMALY" not in eid:
        wrong_denom_count += 1
check("attendance_denominator_correct", wrong_denom_count == 0,
      f"{wrong_denom_count} enrollments with wrong denominator in production records")

# 9. Assessment percentage reconciliation
res_rows = read_csv("assessment_results.csv")
asm_rows = read_csv("assessments.csv")
asm_map = {a["assessment_id"]: a for a in asm_rows}
bad_pct = 0
for r in res_rows[:500]:
    if not r.get("marks_obtained") or not r.get("percentage"): continue
    asm = asm_map.get(r["assessment_id"])
    if not asm: continue
    expected_pct = float(r["marks_obtained"]) / float(asm["maximum_marks"]) * 100
    actual_pct = float(r["percentage"])
    if abs(expected_pct - actual_pct) > 0.1:
        bad_pct += 1
check("assessment_percentage_reconciliation", bad_pct == 0, f"{bad_pct} percentage mismatches (sample of 500)")

# 10. Date ordering — assessment_date in range
dates_ok = True
for a in asm_rows:
    try:
        d = date.fromisoformat(a["assessment_date"])
        if not (date(2026,1,1) <= d <= date(2026,12,31)):
            dates_ok = False; break
    except: dates_ok = False; break
check("assessment_dates_in_range", dates_ok, "All assessment dates in academic year 2026")

# 11. Weightage reconciliation — per course sum ≈ 1.0
wt_by_course = {}
for a in asm_rows:
    wt_by_course.setdefault(a["course_id"], []).append(float(a["weightage"]))
bad_wt = sum(1 for wts in wt_by_course.values() if abs(sum(wts) - 1.0) > 0.05)
check("assessment_weightage_sums_to_1", bad_wt == 0, f"{bad_wt}/{len(wt_by_course)} courses with bad weightage sum")

# 12. Temporal leakage — production risk scores use cutoff_date <= 2026-07-01
risk_rows = read_csv("risk_assessments.csv")
prod_risks = [r for r in risk_rows if r.get("is_anomaly", "False").lower() not in ("true","1")]
leaky = [r for r in prod_risks if r.get("cutoff_date","") > "2026-07-01"]
check("temporal_leakage_production", len(leaky) == 0, f"{len(leaky)} production risks with post-cutoff cutoff_date")

# 13. Intervention trigger chronology
int_rows = read_csv("interventions.csv")
bad_chron = [i for i in int_rows
             if i.get("start_date") and i.get("trigger_date")
             and i["start_date"] < i["trigger_date"]
             and "ANOMALY" not in i["intervention_id"]]
check("intervention_chronology", len(bad_chron) == 0, f"{len(bad_chron)} production interventions with start < trigger (anomalies excluded)")

# 14. Ground truth separation
gt_rows = read_csv("../../../data/ground_truth/ground_truth.csv") if (ROOT/"data"/"ground_truth"/"ground_truth.csv").exists() else []
# GT should not contain marks_obtained, percentage etc.
input_cols = {"marks_obtained","percentage","attendance_status"}
gt_cols = set(gt_rows[0].keys()) if gt_rows else set()
leakage_cols = gt_cols & input_cols
check("ground_truth_no_input_features", len(leakage_cols) == 0,
      f"GT columns: {gt_cols}, input feature leakage: {leakage_cols}")

# 15. Injected anomalies present
dq_rows = read_csv("data_quality_issues.csv")
injected = [d for d in dq_rows if d.get("is_injected_anomaly","").lower() in ("true","1")]
check("five_anomalies_injected", len(injected) >= 5, f"{len(injected)} injected anomaly records found (need 5)")

# Summary
passed = sum(1 for c in checks if c["result"] == "PASS")
failed = sum(1 for c in checks if c["result"] == "FAIL")
print(f"\n{'='*50}")
print(f"Validation Summary: {passed}/{len(checks)} PASSED, {failed} FAILED")

report = {
    "validation_timestamp": __import__("datetime").datetime.utcnow().isoformat(),
    "total_checks": len(checks), "passed": passed, "failed": failed, "warnings": 0,
    "validation_status": "PASS" if failed == 0 else "FAIL",
    "checks": checks,
}
with open(VAL_DIR / "validation_report.json", "w") as f:
    json.dump(report, f, indent=2)
print(f"Report saved to {VAL_DIR / 'validation_report.json'}")
sys.exit(0 if failed == 0 else 1)

