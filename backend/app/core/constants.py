# Student Risk Intelligence Platform - Core Constants & Enums
from enum import Enum


class StudentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    TRANSFERRED = "TRANSFERRED"
    GRADUATED = "GRADUATED"
    WITHDRAWN = "WITHDRAWN"


class EnrollmentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    DROPPED = "DROPPED"
    TRANSFERRED = "TRANSFERRED"
    WITHDRAWN = "WITHDRAWN"


class AttendanceStatus(str, Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    APPROVED_ABSENCE = "APPROVED_ABSENCE"
    LATE = "LATE"
    NOT_RECORDED = "NOT_RECORDED"


class AssessmentType(str, Enum):
    QUIZ = "QUIZ"
    ASSIGNMENT = "ASSIGNMENT"
    MIDTERM = "MIDTERM"
    FINAL = "FINAL"
    PROJECT = "PROJECT"
    PRESENTATION = "PRESENTATION"


class SubmissionStatus(str, Enum):
    SUBMITTED = "SUBMITTED"
    LATE_SUBMISSION = "LATE_SUBMISSION"
    MISSING = "MISSING"
    EXCUSED = "EXCUSED"


class LMSActivityType(str, Enum):
    LOGIN = "LOGIN"
    VIDEO_WATCH = "VIDEO_WATCH"
    RESOURCE_VIEW = "RESOURCE_VIEW"
    ASSIGNMENT_SUBMISSION = "ASSIGNMENT_SUBMISSION"
    QUIZ_ATTEMPT = "QUIZ_ATTEMPT"
    DISCUSSION = "DISCUSSION"
    COURSE_ACCESS = "COURSE_ACCESS"


class CaseType(str, Enum):
    ACADEMIC = "ACADEMIC"
    ATTENDANCE = "ATTENDANCE"
    WELFARE = "WELFARE"
    BEHAVIORAL = "BEHAVIORAL"
    FINANCIAL = "FINANCIAL"


class CaseStatus(str, Enum):
    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class CasePriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class InterventionType(str, Enum):
    ATTENDANCE_COUNSELLING = "ATTENDANCE_COUNSELLING"
    ACADEMIC_TUTORING = "ACADEMIC_TUTORING"
    INSTRUCTOR_MEETING = "INSTRUCTOR_MEETING"
    ENGAGEMENT_SUPPORT = "ENGAGEMENT_SUPPORT"
    ADVISOR_REVIEW = "ADVISOR_REVIEW"
    WELFARE_ASSESSMENT = "WELFARE_ASSESSMENT"
    PERSONALIZED_PLAN = "PERSONALIZED_PLAN"


class InterventionStatus(str, Enum):
    RECOMMENDED = "RECOMMENDED"
    APPROVED = "APPROVED"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class RiskCategory(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class OutcomeLabel(str, Enum):
    IMPROVED = "IMPROVED"
    STABLE = "STABLE"
    DECLINED = "DECLINED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class AnomalyType(str, Enum):
    TEMPORAL_LEAKAGE = "TEMPORAL_LEAKAGE"
    WRONG_DENOMINATOR = "WRONG_DENOMINATOR"
    LIFECYCLE_INCONSISTENCY = "LIFECYCLE_INCONSISTENCY"
    INTERVENTION_PRECEDES_TRIGGER = "INTERVENTION_PRECEDES_TRIGGER"
    MISSING_DATA_AS_FAILURE = "MISSING_DATA_AS_FAILURE"


class UserRole(str, Enum):
    LEARNER = "LEARNER"
    INSTRUCTOR = "INSTRUCTOR"
    ACADEMIC_ADMINISTRATOR = "ACADEMIC_ADMINISTRATOR"
    SUPPORT_STAFF = "SUPPORT_STAFF"
    PLATFORM_ADMINISTRATOR = "PLATFORM_ADMINISTRATOR"


# Risk score thresholds (inclusive ranges)
RISK_THRESHOLDS = {
    "LOW": (0, 24),
    "MEDIUM": (25, 49),
    "HIGH": (50, 74),
    "CRITICAL": (75, 100),
}

# Risk factor weights (must sum to 1.0)
RISK_WEIGHTS = {
    "attendance": 0.30,
    "academic_performance": 0.30,
    "performance_trend": 0.15,
    "lms_engagement": 0.15,
    "historical_support": 0.10,
}

# Minimum fraction of factors that must have data to produce a classification
MIN_DATA_COMPLETENESS = 0.30

ACADEMIC_YEAR = "2026"
ACADEMIC_START = "2026-01-15"
ACADEMIC_END = "2026-12-15"
RISK_CUTOFF_DATE = "2026-07-01"
EVAL_START = "2026-07-02"
EVAL_END = "2026-12-15"

DEPARTMENTS = [
    "Computer Science",
    "Mathematics",
    "Physics",
    "Chemistry",
    "Biology",
    "Engineering",
    "Business Administration",
    "Economics",
    "Psychology",
    "Sociology",
]

PROGRAMS = {
    "Computer Science": ["B.Sc Computer Science", "B.Sc Software Engineering", "B.Sc Data Science"],
    "Mathematics": ["B.Sc Mathematics", "B.Sc Applied Mathematics"],
    "Physics": ["B.Sc Physics", "B.Sc Applied Physics"],
    "Chemistry": ["B.Sc Chemistry", "B.Sc Biochemistry"],
    "Biology": ["B.Sc Biology", "B.Sc Microbiology", "B.Sc Biotechnology"],
    "Engineering": ["B.Eng Electrical", "B.Eng Mechanical", "B.Eng Civil"],
    "Business Administration": ["BBA", "B.Com", "BBA Marketing"],
    "Economics": ["B.Sc Economics", "B.A Economics"],
    "Psychology": ["B.Sc Psychology", "B.A Psychology"],
    "Sociology": ["B.A Sociology", "B.A Social Work"],
}

