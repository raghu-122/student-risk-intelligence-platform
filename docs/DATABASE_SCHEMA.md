# Database Schema

The backend uses SQLAlchemy models in `backend/app/models/`. Foreign keys are explicit in those models; application workflows also validate ownership across related student, enrollment, and risk records. The API creates missing tables at startup. `create_all()` does not alter an existing table, so deployments that already have a database must apply equivalent schema changes before using the new unique constraints.

## Core tables and relationships

| Table | Primary key | Foreign keys and relationships |
|---|---|---|
| `students` | `student_id` | One student has many enrollments, support cases, risk assessments, interventions, outcomes, status-history rows, and ground-truth labels. Email is unique. |
| `courses` | `course_id` | Optional `instructor_id` references `staff.staff_id`. A course has many enrollments and assessments. `course_code` is unique. |
| `enrollments` | `enrollment_id` | Required `student_id` and `course_id` reference their parent tables. An enrollment has attendance, assessment results, LMS activity, cases, risk assessments, interventions, and outcomes. `(student_id, course_id)` is unique. |
| `assessments` | `assessment_id` | Required `course_id` references `courses.course_id`. An assessment has many results. |
| `assessment_results` | `result_id` | Required `assessment_id` and `enrollment_id` reference their parents. `(assessment_id, enrollment_id)` is unique. |
| `attendance_events` | `attendance_id` | Required `enrollment_id` references `enrollments.enrollment_id`. |
| `lms_activities` | `activity_id` | Required `enrollment_id` references `enrollments.enrollment_id`. |
| `risk_assessments` | `risk_id` | Required `student_id`, optional `enrollment_id`; has factor rows, interventions, and ground-truth evaluation. |
| `risk_factors` | `factor_id` | Required `risk_id` references `risk_assessments.risk_id`; `(risk_id, factor_name)` is unique. |
| `support_cases` | `case_id` | Required `student_id`, optional `enrollment_id` and `assigned_staff_id`; has status-event history and interventions. |
| `interventions` | `intervention_id` | Required `student_id`; optional `enrollment_id`, `case_id`, `risk_assessment_id`, and `assigned_staff_id`; has status-event history and outcomes. |
| `outcomes` | `outcome_id` | Required `student_id`, optional `enrollment_id` and `intervention_id`. |
| `ground_truth` | `gt_id` | Optional `student_id` and `risk_id`; `risk_id` is unique when present, implementing an optional one-to-one expected-risk label. |
| `staff` | `staff_id` | One staff member can instruct many courses, own cases, and be assigned interventions. Email is unique. |
| `users` | `user_id` | Optional unique `staff_id` references `staff.staff_id`; the relationship is one-to-one. |
| `data_quality_issues` | `issue_id` | Stores detected issue metadata and a reference to the affected entity/record; the affected-record reference is polymorphic, not a database foreign key. |
| `student_status_history`, `support_case_events`, `intervention_events`, `audit_logs` | Entity-specific event IDs | History/audit rows reference their owning entity and preserve lifecycle events. |

The principal many-to-many relationship is Student-to-Course through Enrollment. Its database unique constraint prevents duplicate enrollment of the same student in the same course. Other one-to-many relationships use their owning entity's foreign key. The `risk_assessments.ground_truth` ORM relationship is one-to-one and `ground_truth.risk_id` is unique.

## Lifecycle states

| Entity | States |
|---|---|
| Student | `ACTIVE`, `INACTIVE`, `TRANSFERRED`, `GRADUATED`, `WITHDRAWN` |
| Enrollment | `ACTIVE`, `COMPLETED`, `DROPPED`, `TRANSFERRED`, `WITHDRAWN` |
| Attendance event | `PRESENT`, `ABSENT`, `APPROVED_ABSENCE`, `LATE`, `NOT_RECORDED` |
| Assessment result | `SUBMITTED`, `LATE_SUBMISSION`, `MISSING`, `EXCUSED` |
| Support case | `OPEN`, `ASSIGNED`, `IN_PROGRESS`, `RESOLVED`, `CLOSED` |
| Intervention | `RECOMMENDED`, `APPROVED`, `ASSIGNED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`, `REJECTED` |
| Risk assessment | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`, `INSUFFICIENT_DATA`, `REVIEW_REQUIRED` |
| Outcome | `IMPROVED`, `STABLE`, `DECLINED`, `INSUFFICIENT_DATA` |

Generated lifecycle fixtures include transferred enrollments and completed enrollments for graduated students. One withdrawn-student active enrollment is deliberately marked as a lifecycle anomaly; all other generated student/enrollment states obey the lifecycle checks.

## Existing-database upgrade notes

The application currently bootstraps missing tables with SQLAlchemy `create_all()` and has no Alembic revision chain. Before running the updated application against an existing PostgreSQL database, check for duplicates and apply these indexes if they are clean:

```sql
CREATE UNIQUE INDEX IF NOT EXISTS uq_enrollment_student_course
    ON enrollments (student_id, course_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_result_assessment_enrollment
    ON assessment_results (assessment_id, enrollment_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_risk_factor_name
    ON risk_factors (risk_id, factor_name);
CREATE UNIQUE INDEX IF NOT EXISTS ix_ground_truth_risk_id
    ON ground_truth (risk_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_staff_id
    ON users (staff_id);
```

Do not apply these indexes if duplicate non-null values exist; resolve the duplicates intentionally first. The regular synthetic seed data has unique pairs and labels.

