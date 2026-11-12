# Business Rules

## Risk assessment

Risk factors are normalized to 0-100, where higher means greater risk:

| Factor | Weight | Source and calculation |
|---|---:|---|
| Attendance | 0.30 | `1 - (PRESENT + LATE) / (sessions - APPROVED_ABSENCE)`, multiplied by 100. At least three pre-cutoff attendance events are required. |
| Academic performance | 0.30 | Weighted average of graded assessment percentages whose `assessment_date <= cutoff_date`, mapped to `100 - average`. Null marks are excluded. |
| Performance trend | 0.15 | First-half versus second-half average among graded pre-cutoff assessments; a declining trend increases risk. At least two graded assessments are required. |
| LMS engagement | 0.15 | Activity frequency compared with two activities per week over the enrollment-to-cutoff period, capped at the expected rate. |
| Historical support | 0.10 | `15 * cases + 10 * open_cases + 20 * critical_cases`, capped at 100; only cases opened on or before the cutoff count. |

Completeness is the share of the five factors with sufficient data. Available-factor weights are renormalized for the composite score, then an eight-point-per-missing-factor completeness penalty is applied. If completeness is below 0.30, the result is `INSUFFICIENT_DATA`.

| Category | Score |
|---|---|
| `LOW` | 0-24 |
| `MEDIUM` | >24-49 |
| `HIGH` | >49-74 |
| `CRITICAL` | >74-100 |

Risk reasons and factor values must be derived from source records. Data after the cutoff must not affect a risk assessment. A missing mark is missing data, not a zero.

## Attendance and assessments

- Approved absences are removed from the attendance denominator; they are neither attended sessions nor unexcused absences.
- `PRESENT` and `LATE` count as attended.
- Assessment percentage is `marks_obtained / maximum_marks * 100`.
- Assessment weights for a course sum to approximately 1.0.
- Results must belong to an enrollment in the same course as the assessment.

## Lifecycle rules

- A withdrawn student must not have active enrollments or in-flight interventions, except for the explicitly labelled lifecycle anomaly fixture.
- Transferred enrollments end on or before their transfer date; generated graduated students have completed enrollments.
- `effective_to` cannot precede `effective_from`.
- An intervention's `start_date` must not precede its `trigger_date`, and its due/completion dates must not precede its start.
- A completed intervention records a completion date. Reopening a support case clears its prior `closed_at` timestamp.

## Outcome evaluation

Outcomes compare a baseline ending at the cutoff with a later evaluation window. Attendance and academic changes are measured in percentage points; engagement compares activity rates. A change greater than 5 points contributes to improvement and a change below -5 contributes to decline. The result is `IMPROVED` if at least two measures improve or the average change exceeds 5, `DECLINED` under the corresponding negative rule, otherwise `STABLE`. Missing future evidence yields `INSUFFICIENT_DATA`.

Outcome labels describe observed association, not causal impact by an intervention.

## Injected anomaly scenarios

Normal production-style rows remain valid. Anomaly fixtures are separate records linked to their source entities and explicitly marked in risk records, ground truth, and data-quality issues:

1. A risk assessment's cutoff precedes an assessment result available on its enrollment.
2. An anomalous risk assessment's attendance factor matches the all-sessions denominator rather than excluding approved absences.
3. A `WITHDRAWN` student has one `ACTIVE` enrollment.
4. An intervention starts before its trigger date.
5. A risk assessment has an inflated academic risk factor despite a pre-cutoff missing assessment result.

