"""All SQLAlchemy ORM models — imported here so Alembic and init_db can see them."""
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
from app.models.support_case_event import SupportCaseEvent
from app.models.intervention import Intervention
from app.models.intervention_event import InterventionEvent
from app.models.risk_assessment import RiskAssessment
from app.models.risk_factor import RiskFactor
from app.models.outcome import Outcome
from app.models.student_status_history import StudentStatusHistory
from app.models.ground_truth import GroundTruth
from app.models.data_quality_issue import DataQualityIssue
from app.models.audit_log import AuditLog

__all__ = [
    "Staff", "User", "Student", "Course", "Enrollment",
    "AttendanceEvent", "Assessment", "AssessmentResult",
    "LMSActivity", "SupportCase", "SupportCaseEvent",
    "Intervention", "InterventionEvent", "RiskAssessment",
    "RiskFactor", "Outcome", "StudentStatusHistory",
    "GroundTruth", "DataQualityIssue", "AuditLog",
]

