#!/usr/bin/env python3
"""Validate generated exports, source-derived values, and injected anomalies."""
import csv
import hashlib
import json
import math
import os
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CSV_DIR = DATA_DIR / "generated" / "csv"
JSON_DIR = DATA_DIR / "generated" / "json"
GT_DIR = DATA_DIR / "ground_truth"
VAL_DIR = DATA_DIR / "validation"
sys.path.insert(0, str(ROOT / "backend"))
os.environ["DATABASE_URL"] = "sqlite://"


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as source:
        return list(csv.DictReader(source))


def parse_date(value):
    return date.fromisoformat(value) if value else None


def parse_datetime(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def parse_json(value):
    return json.loads(value) if value else None


def approximately_equal(actual, expected, tolerance=0.02):
    if actual == "":
        actual = None
    if expected == "":
        expected = None
    if actual is None or expected is None:
        return actual is None and expected is None
    return math.isclose(float(actual), float(expected), abs_tol=tolerance)


def validate(data_dir=DATA_DIR):
    global DATA_DIR, CSV_DIR, JSON_DIR, GT_DIR, VAL_DIR

    DATA_DIR = Path(data_dir).resolve()
    CSV_DIR = DATA_DIR / "generated" / "csv"
    JSON_DIR = DATA_DIR / "generated" / "json"
    GT_DIR = DATA_DIR / "ground_truth"
    VAL_DIR = DATA_DIR / "validation"
    checks = []

    def check(name, passed, detail):
        result = "PASS" if passed else "FAIL"
        checks.append({"check": name, "result": result, "detail": detail})
        print(f"  [{result}] {name}: {detail}")
        return passed

    filenames = (
        "staff.csv", "students.csv", "courses.csv", "enrollments.csv",
        "assessments.csv", "attendance_events.csv", "assessment_results.csv",
        "lms_activities.csv", "support_cases.csv", "risk_assessments.csv",
        "interventions.csv", "outcomes.csv", "data_quality_issues.csv",
    )
    missing_files = [name for name in filenames if not (CSV_DIR / name).is_file()]
    check("required_csv_exports_present", not missing_files, f"missing={missing_files}")
    if missing_files:
        report(checks)
        return 1

    data = {Path(name).stem: read_csv(CSV_DIR / name) for name in filenames}
    gt = read_csv(GT_DIR / "ground_truth.csv")
    anomalies = json.loads((VAL_DIR / "anomaly_records.json").read_text(encoding="utf-8"))
    anomaly_map = {row["anomaly_type"]: row for row in anomalies}
    manifest_path = DATA_DIR / "manifests" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
    expected_scale = {
        "starter": {"students": 500, "courses": 50, "enrollments": 2000},
        "full": {"students": 5000, "courses": 200, "enrollments": 20000},
    }.get(manifest.get("scale"), {})
    actual_scale = {
        entity: len(data[entity]) for entity in ("students", "courses", "enrollments")
    }
    check("requested_scale_volumes", bool(expected_scale) and actual_scale == expected_scale, f"scale={manifest.get('scale')}, volumes={actual_scale}")

    json_mismatches = []
    for filename in filenames:
        json_path = JSON_DIR / f"{Path(filename).stem}.json"
        if not json_path.is_file():
            json_mismatches.append(filename)
            continue
        json_rows = json.loads(json_path.read_text(encoding="utf-8"))
        if json_rows != data[Path(filename).stem]:
            json_mismatches.append(filename)
    check("json_exports_match_csv", not json_mismatches, f"mismatched or missing={json_mismatches}")
    sql_path = DATA_DIR / "generated" / "sql" / "seed.sql"
    sql_text = sql_path.read_text(encoding="utf-8") if sql_path.is_file() else ""
    expected_tables = (
        "staff", "students", "courses", "enrollments", "assessments",
        "attendance_events", "assessment_results", "lms_activities",
        "support_cases", "risk_assessments", "interventions", "outcomes",
        "ground_truth", "data_quality_issues",
    )
    missing_sql_tables = [table for table in expected_tables if f"INSERT INTO {table} (" not in sql_text]
    check(
        "sql_seed_export_complete",
        bool(sql_text) and sql_text.startswith("-- Generated") and "BEGIN;" in sql_text
        and sql_text.rstrip().endswith("COMMIT;") and not missing_sql_tables,
        f"missing tables={missing_sql_tables}",
    )
    checksum_mismatches = []
    if manifest:
        directories = {
            "csv": CSV_DIR, "json": JSON_DIR, "ground_truth": GT_DIR,
            "validation": VAL_DIR, "sql": sql_path.parent,
        }
        for relative_path, expected_hash in manifest.get("file_checksums", {}).items():
            prefix, filename = relative_path.split("/", 1)
            path = directories[prefix] / filename
            actual_hash = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
            if actual_hash != expected_hash:
                checksum_mismatches.append(relative_path)
    else:
        checksum_mismatches.append("manifests/manifest.json")
    check("manifest_export_checksums", not checksum_mismatches, f"mismatches={checksum_mismatches}")

    primary_keys = {
        "staff": "staff_id", "students": "student_id", "courses": "course_id",
        "enrollments": "enrollment_id", "assessments": "assessment_id",
        "attendance_events": "attendance_id", "assessment_results": "result_id",
        "lms_activities": "activity_id", "support_cases": "case_id",
        "risk_assessments": "risk_id", "interventions": "intervention_id",
        "outcomes": "outcome_id", "data_quality_issues": "issue_id",
    }
    indexes = {}
    for entity, column in primary_keys.items():
        rows = data[entity]
        ids = [row.get(column, "") for row in rows]
        unique_ids = set(ids)
        check(
            f"{entity}_primary_key",
            all(ids) and len(ids) == len(unique_ids),
            f"rows={len(rows)}, unique={len(unique_ids)}, empty={sum(not value for value in ids)}",
        )
        indexes[entity] = {row[column]: row for row in rows}

    pair_ids = [(row["student_id"], row["course_id"]) for row in data["enrollments"]]
    check("enrollment_pair_unique", len(pair_ids) == len(set(pair_ids)), f"pairs={len(pair_ids)}")
    result_pairs = [(row["assessment_id"], row["enrollment_id"]) for row in data["assessment_results"]]
    check("assessment_enrollment_result_unique", len(result_pairs) == len(set(result_pairs)), f"pairs={len(result_pairs)}")
    labelled_risk_ids = [row["risk_id"] for row in gt if row.get("risk_id")]
    check("ground_truth_risk_one_to_one", len(labelled_risk_ids) == len(set(labelled_risk_ids)), f"linked risk labels={len(labelled_risk_ids)}")

    foreign_keys = [
        ("course_instructor_fk", "courses", "instructor_id", "staff", "staff_id", True),
        ("enrollment_student_fk", "enrollments", "student_id", "students", "student_id", False),
        ("enrollment_course_fk", "enrollments", "course_id", "courses", "course_id", False),
        ("assessment_course_fk", "assessments", "course_id", "courses", "course_id", False),
        ("attendance_enrollment_fk", "attendance_events", "enrollment_id", "enrollments", "enrollment_id", False),
        ("result_assessment_fk", "assessment_results", "assessment_id", "assessments", "assessment_id", False),
        ("result_enrollment_fk", "assessment_results", "enrollment_id", "enrollments", "enrollment_id", False),
        ("lms_enrollment_fk", "lms_activities", "enrollment_id", "enrollments", "enrollment_id", False),
        ("case_student_fk", "support_cases", "student_id", "students", "student_id", False),
        ("case_enrollment_fk", "support_cases", "enrollment_id", "enrollments", "enrollment_id", True),
        ("case_staff_fk", "support_cases", "assigned_staff_id", "staff", "staff_id", True),
        ("risk_student_fk", "risk_assessments", "student_id", "students", "student_id", False),
        ("risk_enrollment_fk", "risk_assessments", "enrollment_id", "enrollments", "enrollment_id", True),
        ("intervention_student_fk", "interventions", "student_id", "students", "student_id", False),
        ("intervention_enrollment_fk", "interventions", "enrollment_id", "enrollments", "enrollment_id", True),
        ("intervention_risk_fk", "interventions", "risk_assessment_id", "risk_assessments", "risk_id", True),
        ("intervention_staff_fk", "interventions", "assigned_staff_id", "staff", "staff_id", True),
        ("outcome_student_fk", "outcomes", "student_id", "students", "student_id", False),
        ("outcome_enrollment_fk", "outcomes", "enrollment_id", "enrollments", "enrollment_id", True),
        ("outcome_intervention_fk", "outcomes", "intervention_id", "interventions", "intervention_id", True),
    ]
    for name, source, field, target, target_field, nullable in foreign_keys:
        invalid = [
            row for row in data[source]
            if (not row.get(field) and not nullable)
            or (row.get(field) and row[field] not in indexes[target])
        ]
        check(name, not invalid, f"invalid references={len(invalid)}")

    gt_invalid = [
        row for row in gt
        if (row.get("student_id") and row["student_id"] not in indexes["students"])
        or (row.get("risk_id") and row["risk_id"] not in indexes["risk_assessments"])
    ]
    check("ground_truth_foreign_keys", not gt_invalid, f"invalid references={len(gt_invalid)}")

    inconsistent_relations = []
    for row in data["assessment_results"]:
        assessment = indexes["assessments"].get(row.get("assessment_id", ""))
        enrollment = indexes["enrollments"].get(row.get("enrollment_id", ""))
        if assessment and enrollment and assessment["course_id"] != enrollment["course_id"]:
            inconsistent_relations.append(f"result:{row['result_id']}")
    for row in data["risk_assessments"]:
        enr = indexes["enrollments"].get(row.get("enrollment_id", ""))
        if enr and enr["student_id"] != row["student_id"]:
            inconsistent_relations.append(f"risk:{row['risk_id']}")
    for row in data["support_cases"]:
        enr = indexes["enrollments"].get(row.get("enrollment_id", ""))
        if enr and enr["student_id"] != row["student_id"]:
            inconsistent_relations.append(f"case:{row['case_id']}")
    for row in data["interventions"]:
        enr = indexes["enrollments"].get(row.get("enrollment_id", ""))
        if enr and enr["student_id"] != row["student_id"]:
            inconsistent_relations.append(f"intervention:{row['intervention_id']}")
        if row.get("risk_assessment_id"):
            risk = indexes["risk_assessments"].get(row["risk_assessment_id"])
            if risk and (risk["student_id"] != row["student_id"] or (
                row.get("enrollment_id") and risk.get("enrollment_id") != row["enrollment_id"]
            )):
                inconsistent_relations.append(f"intervention-risk:{row['intervention_id']}")
    for row in data["outcomes"]:
        enr = indexes["enrollments"].get(row.get("enrollment_id", ""))
        if enr and enr["student_id"] != row["student_id"]:
            inconsistent_relations.append(f"outcome:{row['outcome_id']}")
    check("cross_entity_ownership_consistency", not inconsistent_relations, f"inconsistent relationships={len(inconsistent_relations)}")

    enum_specs = {
        "students.current_status": ("students", "current_status", {"ACTIVE", "INACTIVE", "TRANSFERRED", "GRADUATED", "WITHDRAWN"}),
        "enrollments.enrollment_status": ("enrollments", "enrollment_status", {"ACTIVE", "COMPLETED", "DROPPED", "TRANSFERRED", "WITHDRAWN"}),
        "attendance_events.attendance_status": ("attendance_events", "attendance_status", {"PRESENT", "ABSENT", "APPROVED_ABSENCE", "LATE", "NOT_RECORDED"}),
        "assessments.assessment_type": ("assessments", "assessment_type", {"QUIZ", "ASSIGNMENT", "MIDTERM", "FINAL", "PROJECT", "PRESENTATION"}),
        "assessment_results.submission_status": ("assessment_results", "submission_status", {"SUBMITTED", "LATE_SUBMISSION", "MISSING", "EXCUSED"}),
        "lms_activities.activity_type": ("lms_activities", "activity_type", {"LOGIN", "VIDEO_WATCH", "RESOURCE_VIEW", "ASSIGNMENT_SUBMISSION", "QUIZ_ATTEMPT", "DISCUSSION", "COURSE_ACCESS"}),
        "support_cases.case_type": ("support_cases", "case_type", {"ACADEMIC", "ATTENDANCE", "WELFARE", "BEHAVIORAL", "FINANCIAL"}),
        "support_cases.case_status": ("support_cases", "case_status", {"OPEN", "ASSIGNED", "IN_PROGRESS", "RESOLVED", "CLOSED"}),
        "support_cases.priority": ("support_cases", "priority", {"LOW", "MEDIUM", "HIGH", "CRITICAL"}),
        "risk_assessments.risk_category": ("risk_assessments", "risk_category", {"LOW", "MEDIUM", "HIGH", "CRITICAL", "INSUFFICIENT_DATA", "REVIEW_REQUIRED"}),
        "interventions.intervention_status": ("interventions", "intervention_status", {"RECOMMENDED", "APPROVED", "ASSIGNED", "IN_PROGRESS", "COMPLETED", "CANCELLED", "REJECTED"}),
        "outcomes.outcome_label": ("outcomes", "outcome_label", {"IMPROVED", "STABLE", "DECLINED", "INSUFFICIENT_DATA"}),
        "data_quality_issues.issue_type": ("data_quality_issues", "issue_type", {"TEMPORAL_LEAKAGE", "WRONG_DENOMINATOR", "LIFECYCLE_INCONSISTENCY", "INTERVENTION_PRECEDES_TRIGGER", "MISSING_DATA_AS_FAILURE"}),
    }
    for name, (entity, column, valid_values) in enum_specs.items():
        invalid = [row for row in data[entity] if row.get(column) not in valid_values]
        check(f"enum_{name}", not invalid, f"invalid rows={len(invalid)}")

    lifecycle_enrollment_id = anomaly_map.get("LIFECYCLE_INCONSISTENCY", {}).get("enrollment_id")
    invalid_active_lifecycles = [
        row for row in data["enrollments"]
        if row["enrollment_status"] == "ACTIVE"
        and indexes["students"][row["student_id"]]["current_status"] != "ACTIVE"
        and row["enrollment_id"] != lifecycle_enrollment_id
    ]
    transfer_count = sum(row["current_status"] == "TRANSFERRED" for row in data["students"])
    graduate_count = sum(row["current_status"] == "GRADUATED" for row in data["students"])
    transfer_enrollments = sum(row["enrollment_status"] == "TRANSFERRED" for row in data["enrollments"])
    completed_enrollments = sum(row["enrollment_status"] == "COMPLETED" for row in data["enrollments"])
    check(
        "student_lifecycle_representation",
        not invalid_active_lifecycles and transfer_count > 0 and graduate_count > 0
        and transfer_enrollments > 0 and completed_enrollments > 0,
        f"invalid active lifecycle rows={len(invalid_active_lifecycles)}, transferred students/enrollments={transfer_count}/{transfer_enrollments}, graduated/completed={graduate_count}/{completed_enrollments}",
    )

    invalid_dates = []
    for row in data["students"]:
        if not parse_date(row["enrollment_date"]):
            invalid_dates.append(f"student:{row['student_id']}")
    for row in data["enrollments"]:
        start, end = parse_date(row["effective_from"]), parse_date(row["effective_to"])
        student_date = parse_date(indexes["students"][row["student_id"]]["enrollment_date"])
        if not start or start < student_date or (end and end < start):
            invalid_dates.append(f"enrollment:{row['enrollment_id']}")
    check("student_and_enrollment_date_order", not invalid_dates, f"invalid rows={len(invalid_dates)}")

    invalid_assessment_dates = []
    for row in data["assessments"]:
        assessed = parse_date(row["assessment_date"])
        if not assessed or assessed < date(2026, 1, 1) or assessed > date(2026, 12, 31):
            invalid_assessment_dates.append(row["assessment_id"])
    check("assessment_dates_in_academic_year", not invalid_assessment_dates, f"invalid rows={len(invalid_assessment_dates)}")

    invalid_event_dates = []
    for row in data["attendance_events"]:
        event_date = parse_date(row["attendance_date"])
        enrollment = indexes["enrollments"][row["enrollment_id"]]
        start, end = parse_date(enrollment["effective_from"]), parse_date(enrollment["effective_to"])
        if not event_date or event_date < start or (end and event_date > end):
            invalid_event_dates.append(row["attendance_id"])
    check("attendance_within_enrollment", not invalid_event_dates, f"invalid rows={len(invalid_event_dates)}")

    invalid_results = []
    result_percentage_mismatches = 0
    for row in data["assessment_results"]:
        assessment_date = parse_date(indexes["assessments"][row["assessment_id"]]["assessment_date"])
        enrollment = indexes["enrollments"][row["enrollment_id"]]
        start, end = parse_date(enrollment["effective_from"]), parse_date(enrollment["effective_to"])
        if assessment_date < start or (end and assessment_date > end):
            invalid_results.append(row["result_id"])
        if row.get("marks_obtained") and row.get("percentage"):
            maximum = float(indexes["assessments"][row["assessment_id"]]["maximum_marks"])
            expected = round(float(row["marks_obtained"]) / maximum * 100, 2)
            if not approximately_equal(float(row["percentage"]), expected, 0.011):
                result_percentage_mismatches += 1
    check("assessment_results_within_enrollment", not invalid_results, f"invalid rows={len(invalid_results)}")
    check("assessment_percentage_calculation", result_percentage_mismatches == 0, f"mismatches={result_percentage_mismatches}")

    weights_by_course = defaultdict(float)
    for row in data["assessments"]:
        weights_by_course[row["course_id"]] += float(row["weightage"])
    bad_weights = {course_id: total for course_id, total in weights_by_course.items() if not math.isclose(total, 1, abs_tol=0.005)}
    check("assessment_weightages_sum_to_one", not bad_weights, f"courses={len(weights_by_course)}, invalid={len(bad_weights)}")

    invalid_lms = []
    for row in data["lms_activities"]:
        timestamp = parse_datetime(row["activity_timestamp"])
        enrollment = indexes["enrollments"][row["enrollment_id"]]
        start, end = parse_date(enrollment["effective_from"]), parse_date(enrollment["effective_to"])
        if not timestamp or timestamp.date() < start or (end and timestamp.date() > end):
            invalid_lms.append(row["activity_id"])
    check("lms_activity_within_enrollment", not invalid_lms, f"invalid rows={len(invalid_lms)}")

    invalid_cases = []
    for row in data["support_cases"]:
        opened, closed = parse_datetime(row["opened_at"]), parse_datetime(row["closed_at"])
        should_be_closed = row["case_status"] in ("RESOLVED", "CLOSED")
        if not opened or (closed and closed < opened) or should_be_closed != bool(closed):
            invalid_cases.append(row["case_id"])
    check("support_case_date_order", not invalid_cases, f"invalid rows={len(invalid_cases)}")

    anomaly_intervention_id = anomaly_map.get("INTERVENTION_PRECEDES_TRIGGER", {}).get("intervention", {}).get("intervention_id")
    invalid_interventions = []
    for row in data["interventions"]:
        trigger, start = parse_date(row["trigger_date"]), parse_date(row["start_date"])
        due, completed = parse_date(row["due_date"]), parse_date(row["completion_date"])
        if not trigger or (start and start < trigger and row["intervention_id"] != anomaly_intervention_id):
            invalid_interventions.append(row["intervention_id"])
        if start and due and due < start:
            invalid_interventions.append(row["intervention_id"])
        if completed and start and completed < start:
            invalid_interventions.append(row["intervention_id"])
        if row["intervention_status"] == "COMPLETED" and not completed:
            invalid_interventions.append(row["intervention_id"])
    check("intervention_lifecycle_dates", not invalid_interventions, f"invalid rows={len(set(invalid_interventions))}")

    invalid_outcomes = []
    for row in data["outcomes"]:
        start, end = parse_date(row["evaluation_period_start"]), parse_date(row["evaluation_period_end"])
        evaluated = parse_date(row["evaluation_date"])
        if not start or not end or start > end or not evaluated or evaluated < end:
            invalid_outcomes.append(row["outcome_id"])
    check("outcome_period_order", not invalid_outcomes, f"invalid rows={len(invalid_outcomes)}")

    gt_feature_columns = {"marks_obtained", "percentage", "attendance_status", "activity_timestamp", "factor_scores"}
    leaked_columns = gt_feature_columns.intersection(gt[0].keys() if gt else ())
    check("ground_truth_feature_separation", not leaked_columns, f"forbidden columns={sorted(leaked_columns)}")
    anomaly_labels = [row for row in gt if row.get("expected_anomaly_detected", "").lower() in ("true", "1")]
    expected_types = {
        "TEMPORAL_LEAKAGE", "WRONG_DENOMINATOR", "LIFECYCLE_INCONSISTENCY",
        "INTERVENTION_PRECEDES_TRIGGER", "MISSING_DATA_AS_FAILURE",
    }
    ground_truth_types = {row["evaluation_reference"] for row in anomaly_labels}
    check("ground_truth_has_five_anomaly_labels", ground_truth_types == expected_types, f"labels={sorted(ground_truth_types)}")

    derived_failures = validate_derived_values(data, indexes, check)
    detector_failures = validate_injected_anomalies(data, indexes, anomaly_map, check)

    report(checks, data, gt, anomaly_map)
    return 1 if any(row["result"] == "FAIL" for row in checks) else 0


def validate_derived_values(data, indexes, check):
    weights = {
        "attendance": 0.30,
        "academic_performance": 0.30,
        "performance_trend": 0.15,
        "lms_engagement": 0.15,
        "historical_support": 0.10,
    }
    attendance_by_enrollment = defaultdict(list)
    for row in data["attendance_events"]:
        attendance_by_enrollment[row["enrollment_id"]].append(row)
    results_by_enrollment = defaultdict(list)
    for row in data["assessment_results"]:
        assessment = indexes["assessments"][row["assessment_id"]]
        results_by_enrollment[row["enrollment_id"]].append((row, assessment))
    lms_by_enrollment = defaultdict(list)
    for row in data["lms_activities"]:
        lms_by_enrollment[row["enrollment_id"]].append(row)
    cases_by_student = defaultdict(list)
    for row in data["support_cases"]:
        cases_by_student[row["student_id"]].append(row)

    risk_mismatches = 0
    for risk in data["risk_assessments"]:
        if risk["is_anomaly"].lower() in ("true", "1"):
            continue
        cutoff = parse_date(risk["cutoff_date"])
        enrollment = indexes["enrollments"].get(risk.get("enrollment_id", ""))
        if enrollment is None:
            # enrollment_id from risk_assessments CSV not found in enrollments CSV
            # (can happen when risk_assessments were seeded from DB with extra enrollments)
            continue
        student_id = risk["student_id"]
        factors = {}
        available = set()

        attendance = [
            row for row in attendance_by_enrollment[risk["enrollment_id"]]
            if parse_date(row["attendance_date"]) <= cutoff
        ]
        approved = sum(row["attendance_status"] == "APPROVED_ABSENCE" for row in attendance)
        effective = len(attendance) - approved
        attended = sum(row["attendance_status"] in ("PRESENT", "LATE") for row in attendance)
        if len(attendance) >= 3 and effective > 0:
            factors["attendance"] = round((1 - attended / effective) * 100, 2)
            available.add("attendance")
        else:
            factors["attendance"] = None

        graded = sorted(
            (
                parse_date(assessment["assessment_date"]),
                float(result["percentage"]),
                float(assessment["weightage"]),
            )
            for result, assessment in results_by_enrollment[risk["enrollment_id"]]
            if parse_date(assessment["assessment_date"]) <= cutoff
            and result.get("marks_obtained") and result.get("percentage")
        )
        total_weight = sum(weight for _, _, weight in graded)
        if graded:
            average = (
                sum(score * weight for _, score, weight in graded) / total_weight
                if total_weight
                else sum(score for _, score, _ in graded) / len(graded)
            )
            factors["academic_performance"] = round((1 - average / 100) * 100, 2)
            available.add("academic_performance")
        else:
            factors["academic_performance"] = None

        if len(graded) >= 2:
            midpoint = len(graded) // 2
            first = sum(score for _, score, _ in graded[:midpoint]) / midpoint
            second = sum(score for _, score, _ in graded[midpoint:]) / (len(graded) - midpoint)
            trend = second - first
            factors["performance_trend"] = round(max(0.0, min(100.0, (-trend + 20) / 40 * 100)), 2)
            available.add("performance_trend")
        else:
            factors["performance_trend"] = None

        activities = [
            row for row in lms_by_enrollment[risk["enrollment_id"]]
            if parse_datetime(row["activity_timestamp"]).date() <= cutoff
        ]
        effective_from = parse_date(enrollment["effective_from"])
        days = max(1, (cutoff - effective_from).days) if effective_from <= cutoff else 90
        engagement = min(1.0, len(activities) / max(1, days / 7 * 2))
        factors["lms_engagement"] = round((1 - engagement) * 100, 2)
        available.add("lms_engagement")

        cases = [
            row for row in cases_by_student[student_id]
            if parse_datetime(row["opened_at"]).date() <= cutoff
        ]
        open_cases = sum(row["case_status"] not in ("RESOLVED", "CLOSED") for row in cases)
        critical_cases = sum(row["priority"] == "CRITICAL" for row in cases)
        factors["historical_support"] = round(min(100, len(cases) * 15 + open_cases * 10 + critical_cases * 20), 2)
        available.add("historical_support")

        completeness = round(len(available) / 5, 2)
        total_weight = sum(weights[key] for key in available)
        score = None
        category = "INSUFFICIENT_DATA"
        if completeness >= 0.30 and total_weight:
            weighted = sum(factors[key] * weights[key] for key in available) / total_weight
            score = round(min(100, weighted + (1 - completeness) * 8), 2)
            category = "LOW" if score <= 24 else "MEDIUM" if score <= 49 else "HIGH" if score <= 74 else "CRITICAL"

        expected_factors = parse_json(risk["factor_scores"])
        row_mismatch = (
            any(not approximately_equal(expected_factors.get(key), value) for key, value in factors.items())
            or not approximately_equal(risk.get("data_completeness"), completeness)
            or not approximately_equal(risk.get("risk_score"), score)
            or risk["risk_category"] != category
        )
        risk_mismatches += int(row_mismatch)
    check("risk_scores_reconcile_to_source_records", risk_mismatches == 0, f"mismatched normal assessments={risk_mismatches}")

    metric_mismatches = defaultdict(int)
    metric_examples = defaultdict(list)
    outcome_mismatches = 0
    for outcome in data["outcomes"]:
        enrollment_id = outcome["enrollment_id"]
        start = parse_date(outcome["evaluation_period_start"])
        end = parse_date(outcome["evaluation_period_end"])

        def attendance_rate(begin, finish):
            events = [
                row for row in attendance_by_enrollment[enrollment_id]
                if parse_date(row["attendance_date"]) <= finish
                and (begin is None or parse_date(row["attendance_date"]) >= begin)
            ]
            approved = sum(row["attendance_status"] == "APPROVED_ABSENCE" for row in events)
            denominator = len(events) - approved
            if len(events) < 2 or denominator <= 0:
                return None
            attended = sum(row["attendance_status"] in ("PRESENT", "LATE") for row in events)
            return attended / denominator

        def academic_average(begin, finish):
            scores = [
                float(result["percentage"])
                for result, assessment in results_by_enrollment[enrollment_id]
                if result.get("marks_obtained") and result.get("percentage")
                and begin <= parse_date(assessment["assessment_date"]) <= finish
            ]
            return sum(scores) / len(scores) if scores else None

        base_att = attendance_rate(None, date.fromisoformat("2026-07-01"))
        future_att = attendance_rate(start, end)
        base_acad = academic_average(date.min, date.fromisoformat("2026-07-01"))
        future_acad = academic_average(start, end)
        base_lms = sum(
            parse_datetime(row["activity_timestamp"]).date() <= date.fromisoformat("2026-07-01")
            for row in lms_by_enrollment[enrollment_id]
        ) / (180 / 7)
        future_lms = sum(
            start <= parse_datetime(row["activity_timestamp"]).date() <= end
            for row in lms_by_enrollment[enrollment_id]
        ) / max(1, (end - start).days / 7)
        att_change = round((future_att - base_att) * 100, 2) if future_att is not None and base_att is not None else None
        acad_change = round(future_acad - base_acad, 2) if future_acad is not None and base_acad is not None else None
        engagement_change = round((future_lms - base_lms) * 10, 2) if future_lms is not None and base_lms is not None else None
        expected_changes = {
            "attendance_change": att_change,
            "academic_performance_change": acad_change,
            "engagement_change": engagement_change,
        }
        source_changes = [
            value for value in (att_change, acad_change, engagement_change) if value is not None
        ]
        if source_changes:
            mean_change = sum(source_changes) / len(source_changes)
            improved = sum(value > 5 for value in source_changes)
            declined = sum(value < -5 for value in source_changes)
            expected_label = (
                "IMPROVED" if improved >= 2 or mean_change > 5
                else "DECLINED" if declined >= 2 or mean_change < -5
                else "STABLE"
            )
        else:
            expected_label = "INSUFFICIENT_DATA"
        for key, expected_value in expected_changes.items():
            if not approximately_equal(outcome.get(key), expected_value):
                metric_mismatches[key] += 1
                if len(metric_examples[key]) < 3:
                    metric_examples[key].append({
                        "outcome_id": outcome["outcome_id"],
                        "stored": outcome.get(key),
                        "recomputed": expected_value,
                    })
        if outcome["outcome_label"] != expected_label:
            outcome_mismatches += 1
    check("outcomes_reconcile_to_source_records", not any(metric_mismatches.values()) and outcome_mismatches == 0, f"metric mismatches={dict(metric_mismatches)}, examples={dict(metric_examples)}, label mismatches={outcome_mismatches}")
    return risk_mismatches + sum(metric_mismatches.values()) + outcome_mismatches


def validate_injected_anomalies(data, indexes, anomaly_map, check):
    expected = {
        "TEMPORAL_LEAKAGE", "WRONG_DENOMINATOR", "LIFECYCLE_INCONSISTENCY",
        "INTERVENTION_PRECEDES_TRIGGER", "MISSING_DATA_AS_FAILURE",
    }
    check("five_anomaly_fixtures_present", set(anomaly_map) == expected, f"fixtures={sorted(anomaly_map)}")

    risk_rows = indexes["risk_assessments"]
    assessment_rows = indexes["assessments"]
    result_rows = data["assessment_results"]
    attendance_rows = data["attendance_events"]
    students = indexes["students"]
    enrollments = indexes["enrollments"]
    interventions = indexes["interventions"]

    temporal = anomaly_map.get("TEMPORAL_LEAKAGE", {}).get("risk_assessment", {})
    temporal_risk = risk_rows.get(temporal.get("risk_id"), {})
    temporal_future = any(
        row["enrollment_id"] == temporal_risk.get("enrollment_id")
        and parse_date(assessment_rows[row["assessment_id"]]["assessment_date"]) > parse_date(temporal_risk.get("cutoff_date"))
        for row in result_rows
    )
    check("fixture_temporal_leakage_detectable", bool(temporal_future), f"risk_id={temporal.get('risk_id')}")

    wrong = anomaly_map.get("WRONG_DENOMINATOR", {}).get("risk_assessment", {})
    wrong_risk = risk_rows.get(wrong.get("risk_id"), {})
    wrong_events = [
        row for row in attendance_rows
        if row["enrollment_id"] == wrong_risk.get("enrollment_id")
        and parse_date(row["attendance_date"]) <= parse_date(wrong_risk.get("cutoff_date"))
    ]
    total = len(wrong_events)
    approved = sum(row["attendance_status"] == "APPROVED_ABSENCE" for row in wrong_events)
    attended = sum(row["attendance_status"] in ("PRESENT", "LATE") for row in wrong_events)
    factors = parse_json(wrong_risk.get("factor_scores", "{}")) or {}
    wrong_detectable = total > approved and total > 0 and attended > 0 and approximately_equal(
        factors.get("attendance"), round((1 - attended / total) * 100, 2)
    ) and not approximately_equal(factors.get("attendance"), round((1 - attended / (total - approved)) * 100, 2))
    check("fixture_wrong_denominator_detectable", wrong_detectable, f"risk_id={wrong.get('risk_id')}")

    lifecycle = anomaly_map.get("LIFECYCLE_INCONSISTENCY", {})
    lifecycle_student = students.get(lifecycle.get("student_id"), {})
    lifecycle_active = any(
        row["student_id"] == lifecycle.get("student_id") and row["enrollment_status"] == "ACTIVE"
        for row in enrollments.values()
    )
    check("fixture_withdrawn_active_enrollment_detectable", lifecycle_student.get("current_status") == "WITHDRAWN" and lifecycle_active, f"student_id={lifecycle.get('student_id')}")

    intervention_fixture = anomaly_map.get("INTERVENTION_PRECEDES_TRIGGER", {}).get("intervention", {})
    intervention = interventions.get(intervention_fixture.get("intervention_id"), {})
    chronological_violation = bool(intervention) and parse_date(intervention["start_date"]) < parse_date(intervention["trigger_date"])
    check("fixture_intervention_precedes_trigger_detectable", chronological_violation, f"intervention_id={intervention_fixture.get('intervention_id')}")

    missing = anomaly_map.get("MISSING_DATA_AS_FAILURE", {}).get("risk_assessment", {})
    missing_risk = risk_rows.get(missing.get("risk_id"), {})
    missing_factors = parse_json(missing_risk.get("factor_scores", "{}")) or {}
    has_missing = any(
        row["enrollment_id"] == missing_risk.get("enrollment_id")
        and row.get("marks_obtained") == ""
        and parse_date(assessment_rows[row["assessment_id"]]["assessment_date"]) <= parse_date(missing_risk.get("cutoff_date"))
        for row in result_rows
    )
    check("fixture_missing_data_as_failure_detectable", bool(missing_risk) and missing_risk.get("is_anomaly", "").lower() in ("true", "1") and has_missing and float(missing_factors.get("academic_performance") or 0) > 60, f"risk_id={missing.get('risk_id')}")

    detected = run_backend_detectors(data, indexes, anomaly_map)
    check("backend_detects_all_five_anomalies", detected == expected, f"detected={sorted(detected)}, missing={sorted(expected - detected)}")
    return len(expected - detected)


def run_backend_detectors(data, indexes, anomaly_map):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.db.database import Base
    import app.models
    from app.models.assessment import Assessment
    from app.models.assessment_result import AssessmentResult
    from app.models.attendance import AttendanceEvent
    from app.models.course import Course
    from app.models.enrollment import Enrollment
    from app.models.intervention import Intervention
    from app.models.risk_assessment import RiskAssessment
    from app.models.student import Student
    from app.services.anomaly_engine import (
        detect_intervention_precedes_trigger,
        detect_lifecycle_inconsistency,
        detect_missing_data_as_failure,
        detect_temporal_leakage,
        detect_wrong_denominator,
    )

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    detected = set()
    try:
        with Session(engine) as session:
            students = indexes["students"]
            courses = indexes["courses"]
            enrollments = indexes["enrollments"]
            assessments = indexes["assessments"]
            results = data["assessment_results"]
            attendance = data["attendance_events"]
            added_students, added_courses, added_enrollments = set(), set(), set()

            def ensure_student(student_id):
                if student_id not in added_students:
                    row = students[student_id]
                    session.add(Student(
                        student_id=student_id, first_name=row["first_name"], last_name=row["last_name"],
                        email=row["email"], enrollment_date=parse_date(row["enrollment_date"]),
                        academic_year=row["academic_year"], department=row["department"],
                        program=row["program"], current_status=row["current_status"],
                    ))
                    added_students.add(student_id)

            def ensure_enrollment(enrollment_id):
                if enrollment_id in added_enrollments:
                    return
                row = enrollments.get(enrollment_id)
                if row is None:
                    # enrollment_id references a DB-only record not in the CSV; skip gracefully
                    return
                ensure_student(row["student_id"])
                if row["course_id"] not in added_courses:
                    course = courses[row["course_id"]]
                    session.add(Course(
                        course_id=course["course_id"], course_name=course["course_name"],
                        course_code=course["course_code"], department=course["department"],
                        credits=int(course["credits"]), semester=course["semester"],
                    ))
                    added_courses.add(row["course_id"])
                session.add(Enrollment(
                    enrollment_id=enrollment_id, student_id=row["student_id"], course_id=row["course_id"],
                    enrollment_date=parse_date(row["enrollment_date"]),
                    effective_from=parse_date(row["effective_from"]),
                    effective_to=parse_date(row["effective_to"]),
                    enrollment_status=row["enrollment_status"],
                ))
                added_enrollments.add(enrollment_id)

            added_risks = set()
            added_assessments = set()

            def ensure_risk(risk_id):
                if not risk_id or risk_id in added_risks:
                    return
                row = indexes["risk_assessments"][risk_id]
                ensure_student(row["student_id"])
                if row.get("enrollment_id"):
                    ensure_enrollment(row["enrollment_id"])
                session.add(RiskAssessment(
                    risk_id=risk_id, student_id=row["student_id"], enrollment_id=row.get("enrollment_id") or None,
                    cutoff_date=parse_date(row["cutoff_date"]),
                    risk_score=float(row["risk_score"]) if row.get("risk_score") else None,
                    risk_category=row["risk_category"], factor_scores=parse_json(row["factor_scores"]),
                    factor_weights=parse_json(row["factor_weights"]), reasons=parse_json(row["reasons"]),
                    data_completeness=float(row["data_completeness"]) if row.get("data_completeness") else None,
                    model_version=row["model_version"], is_anomaly=row["is_anomaly"].lower() in ("true", "1"),
                ))
                added_risks.add(risk_id)

            def ensure_assessment(assessment_id):
                if assessment_id in added_assessments:
                    return
                row = assessments[assessment_id]
                session.add(Assessment(
                    assessment_id=assessment_id, course_id=row["course_id"],
                    assessment_name=row["assessment_name"], assessment_type=row["assessment_type"],
                    maximum_marks=float(row["maximum_marks"]), weightage=float(row["weightage"]),
                    assessment_date=parse_date(row["assessment_date"]),
                ))
                added_assessments.add(assessment_id)

            def add_result(row):
                ensure_enrollment(row["enrollment_id"])
                ensure_assessment(row["assessment_id"])
                session.add(AssessmentResult(
                    result_id=row["result_id"], assessment_id=row["assessment_id"],
                    enrollment_id=row["enrollment_id"],
                    marks_obtained=float(row["marks_obtained"]) if row.get("marks_obtained") else None,
                    percentage=float(row["percentage"]) if row.get("percentage") else None,
                    submission_status=row["submission_status"],
                ))

            temporal_risk = anomaly_map["TEMPORAL_LEAKAGE"]["risk_assessment"]
            ensure_risk(temporal_risk["risk_id"])
            temporal_enrollment = temporal_risk["enrollment_id"]
            for row in results:
                if row["enrollment_id"] == temporal_enrollment and parse_date(assessments[row["assessment_id"]]["assessment_date"]) > parse_date(temporal_risk["cutoff_date"]):
                    add_result(row)

            wrong_risk = anomaly_map["WRONG_DENOMINATOR"]["risk_assessment"]
            ensure_risk(wrong_risk["risk_id"])
            for row in attendance:
                if row["enrollment_id"] == wrong_risk["enrollment_id"] and parse_date(row["attendance_date"]) <= parse_date(wrong_risk["cutoff_date"]):
                    ensure_enrollment(row["enrollment_id"])
                    session.add(AttendanceEvent(
                        attendance_id=row["attendance_id"], enrollment_id=row["enrollment_id"],
                        attendance_date=parse_date(row["attendance_date"]),
                        attendance_status=row["attendance_status"], session_number=int(row["session_number"]),
                    ))

            lifecycle = anomaly_map["LIFECYCLE_INCONSISTENCY"]
            ensure_student(lifecycle["student_id"])
            ensure_enrollment(lifecycle["enrollment_id"])

            intervention_row = anomaly_map["INTERVENTION_PRECEDES_TRIGGER"]["intervention"]
            ensure_student(intervention_row["student_id"])
            ensure_enrollment(intervention_row["enrollment_id"])
            session.add(Intervention(
                intervention_id=intervention_row["intervention_id"],
                student_id=intervention_row["student_id"],
                enrollment_id=intervention_row["enrollment_id"],
                intervention_type=intervention_row["intervention_type"],
                trigger_date=parse_date(intervention_row["trigger_date"]),
                start_date=parse_date(intervention_row["start_date"]),
                due_date=parse_date(intervention_row["due_date"]),
                intervention_status=intervention_row["intervention_status"],
            ))

            missing_risk = anomaly_map["MISSING_DATA_AS_FAILURE"]["risk_assessment"]
            ensure_risk(missing_risk["risk_id"])
            for row in results:
                if row["enrollment_id"] == missing_risk["enrollment_id"] and not row.get("marks_obtained"):
                    add_result(row)

            session.flush()
            detectors = (
                ("TEMPORAL_LEAKAGE", detect_temporal_leakage(session, temporal_risk["risk_id"])),
                ("WRONG_DENOMINATOR", detect_wrong_denominator(session, wrong_risk["enrollment_id"])),
                ("LIFECYCLE_INCONSISTENCY", detect_lifecycle_inconsistency(session, lifecycle["student_id"])),
                ("INTERVENTION_PRECEDES_TRIGGER", detect_intervention_precedes_trigger(session, intervention_row["intervention_id"])),
                ("MISSING_DATA_AS_FAILURE", detect_missing_data_as_failure(session, missing_risk["risk_id"])),
            )
            detected = {name for name, result in detectors if result is not None}
    finally:
        engine.dispose()
    return detected


def report(checks, data=None, gt=None, anomaly_map=None):
    passed = sum(row["result"] == "PASS" for row in checks)
    failed = len(checks) - passed
    report_data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scale": None,
        "seed": None,
        "row_counts": {},
        "total_checks": len(checks),
        "passed": passed,
        "failed": failed,
        "validation_status": "PASS" if failed == 0 else "FAIL",
        "checks": checks,
    }
    manifest_path = DATA_DIR / "manifests" / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        report_data["scale"] = manifest.get("scale")
        report_data["seed"] = manifest.get("seed")
        report_data["row_counts"] = manifest.get("entity_counts", {})
    VAL_DIR.mkdir(parents=True, exist_ok=True)
    (VAL_DIR / "validation_report.json").write_text(json.dumps(report_data, indent=2), encoding="utf-8")
    print(f"\nValidation summary: {passed}/{len(checks)} passed, {failed} failed")
    print(f"Report saved to {VAL_DIR / 'validation_report.json'}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    args = parser.parse_args()
    raise SystemExit(validate(args.data_dir))
