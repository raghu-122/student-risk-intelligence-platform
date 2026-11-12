from sqlalchemy import Column, String, Text, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base
from app.models.mixins import TimestampMixin


class Intervention(Base, TimestampMixin):
    __tablename__ = "interventions"

    intervention_id = Column(String(20), primary_key=True)  # INT-2026-000001
    student_id = Column(String(20), ForeignKey("students.student_id"), nullable=False)
    enrollment_id = Column(String(80), ForeignKey("enrollments.enrollment_id"), nullable=True)
    case_id = Column(String(20), ForeignKey("support_cases.case_id"), nullable=True)
    risk_assessment_id = Column(String(60), ForeignKey("risk_assessments.risk_id"), nullable=True)
    intervention_type = Column(String(40), nullable=False)
    trigger_date = Column(Date, nullable=False)
    assigned_staff_id = Column(String(20), ForeignKey("staff.staff_id"), nullable=True)
    start_date = Column(Date, nullable=True)
    due_date = Column(Date, nullable=True)
    completion_date = Column(Date, nullable=True)
    intervention_status = Column(String(20), nullable=False, default="RECOMMENDED")
    expected_outcome = Column(Text, nullable=True)
    actual_outcome = Column(Text, nullable=True)

    student = relationship("Student", back_populates="interventions")
    enrollment = relationship("Enrollment", back_populates="interventions")
    case = relationship("SupportCase", back_populates="interventions")
    assigned_staff = relationship("Staff", back_populates="interventions")
    risk_assessment = relationship("RiskAssessment", back_populates="interventions")
    events = relationship("InterventionEvent", back_populates="intervention")
    outcomes = relationship("Outcome", back_populates="intervention")

