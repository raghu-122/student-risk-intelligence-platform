# Data Dictionary

The generated CSV and JSON files use the columns below. Empty CSV fields represent missing or nullable values; they are not zero. JSON exports preserve the CSV values as strings, including empty strings. Database import converts empty optional values to SQL `NULL`.

## Entity exports

| File / entity | Primary key | Fields |
|---|---|---|
| `staff.csv` / Staff | `staff_id` | `first_name`, `last_name`, `email`, `role`, `department`, `is_active` |
| `students.csv` / Student | `student_id` | `first_name`, `last_name`, `email`, `enrollment_date`, `academic_year`, `department`, `program`, `current_status` |
| `courses.csv` / Course | `course_id` | `course_name`, `course_code`, `department`, `credits`, `semester`, `instructor_id` |
| `enrollments.csv` / Enrollment | `enrollment_id` | `student_id`, `course_id`, `enrollment_date`, `effective_from`, `effective_to`, `enrollment_status`, `final_grade` |
| `assessments.csv` / Assessment | `assessment_id` | `course_id`, `assessment_name`, `assessment_type`, `maximum_marks`, `weightage`, `assessment_date` |
| `attendance_events.csv` / AttendanceEvent | `attendance_id` | `enrollment_id`, `attendance_date`, `attendance_status`, `session_number`, `issue_type` |
| `assessment_results.csv` / AssessmentResult | `result_id` | `assessment_id`, `enrollment_id`, `marks_obtained`, `percentage`, `submission_status`, `evaluated_at` |
| `lms_activities.csv` / LMSActivity | `activity_id` | `enrollment_id`, `activity_type`, `activity_timestamp`, `duration_minutes`, `resource_id`, `activity_metadata` |
| `support_cases.csv` / SupportCase | `case_id` | `student_id`, optional `enrollment_id`, `case_type`, `description`, `priority`, optional `assigned_staff_id`, `case_status`, `opened_at`, optional `closed_at`, `resolution_notes` |
| `risk_assessments.csv` / RiskAssessment | `risk_id` | `student_id`, optional `enrollment_id`, `assessment_timestamp`, `cutoff_date`, `risk_score`, `risk_category`, JSON `factor_scores`, JSON `factor_weights`, JSON `reasons`, `data_completeness`, `model_version`, `is_anomaly` |
| `interventions.csv` / Intervention | `intervention_id` | `student_id`, optional `enrollment_id`, `case_id`, `risk_assessment_id`, `intervention_type`, `trigger_date`, `assigned_staff_id`, `start_date`, `due_date`, `completion_date`, `intervention_status`, `expected_outcome`, `actual_outcome` |
| `outcomes.csv` / Outcome | `outcome_id` | `student_id`, optional `enrollment_id`, optional `intervention_id`, `evaluation_period_start`, `evaluation_period_end`, `baseline_risk_score`, `future_risk_score`, `academic_performance_change`, `attendance_change`, `engagement_change`, `outcome_label`, `evaluation_date` |
| `data_quality_issues.csv` / DataQualityIssue | `issue_id` | `issue_type`, `affected_entity`, `affected_record_id`, `expected_behavior`, `observed_behavior`, `ground_truth_label`, `detection_status`, `explanation`, `severity`, `is_injected_anomaly` |
| `ground_truth.csv` / GroundTruth | `gt_id` | optional `student_id`, optional `risk_id`, `expected_risk_category`, `expected_outcome_label`, `expected_anomaly_detected`, `evaluation_reference`, `notes` |

`data/generated/json/` contains one JSON array for each generated CSV export. `data/ground_truth/ground_truth.json` is the JSON counterpart of the ground-truth CSV. The independent anomaly fixture file, `data/validation/anomaly_records.json`, contains references to the labelled source records.

## Key meanings

- `effective_from` / `effective_to`: dates during which an enrollment is in effect; a blank `effective_to` means no recorded end date.
- `attendance_status`: `PRESENT`, `ABSENT`, `APPROVED_ABSENCE`, `LATE`, or `NOT_RECORDED`. Approved absences do not count in the risk engine's attendance denominator.
- `marks_obtained` and `percentage`: both are blank when no mark was recorded. Missing marks are not imputed as zero.
- `weightage`: assessment contribution weight within a course; generated weights sum to approximately 1.0 per course.
- `cutoff_date`: last date from which data can contribute to a risk assessment.
- `factor_scores`: JSON map of normalized 0-100 risk factors. A higher value indicates higher risk; a `null` value means the factor lacks enough source data.
- `factor_weights`: the configured contribution weight for each risk factor. The composite score renormalizes across available factors.
- `data_completeness`: fraction of the five risk factors that had usable data.
- `is_anomaly`: true only for explicitly injected risk-assessment fixtures. Normal production-style rows remain separately labelled.
- `expected_anomaly_detected`: evaluation label kept in ground truth, not a feature supplied to the model.
- `*_change`: change between the baseline and evaluation windows, expressed in percentage points for attendance and academic performance; engagement change is the engine's scaled activity-rate difference.

## Identifier conventions

Identifiers are stable for a given seed and generated in deterministic entity order:

| Entity | Pattern |
|---|---|
| Student | `STU-2026-000001` |
| Course | `CRS-000001` |
| Enrollment | `ENR-{student_id}-{course_id}` |
| Assessment | `ASM-000001` |
| Result | `RES-{assessment_id}-{enrollment_id}` |
| Attendance event | `ATT-{enrollment_id}-{YYYYMMDD}` |
| LMS activity | `LMS-2026-000001` |
| Support case | `CASE-2026-000001` |
| Intervention | `INT-2026-000001` |
| Outcome | `OUT-2026-000001` |
| Risk assessment | `RISK-{enrollment_id}-{sequence}`; injected risks use `RISK-2026-ANOM-{sequence}` |
| Ground truth | `GT-2026-000001` |

