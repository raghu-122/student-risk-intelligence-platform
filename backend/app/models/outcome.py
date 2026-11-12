from sqlalchemy import Column, String, Float, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base
from app.models.mixins import TimestampMixin


class Outcome(Base, TimestampMixin):
    __tablename__ = "outcomes"

    outcome_id = Column(String(20), primary_key=True)       # OUT-2026-000001
    student_id = Column(String(20), ForeignKey("students.student_id"), nullable=False)
    enrollment_id = Column(String(80), ForeignKey("enrollments.enrollment_id"), nullable=True)
    intervention_id = Column(String(20), ForeignKey("interventions.intervention_id"), nullable=True)
    evaluation_period_start = Column(Date, nullable=False)
    evaluation_period_end = Column(Date, nullable=False)
    baseline_risk_score = Column(Float, nullable=True)
    future_risk_score = Column(Float, nullable=True)
    academic_performance_change = Column(Float, nullable=True)
    attendance_change = Column(Float, nullable=True)
    engagement_change = Column(Float, nullable=True)
    outcome_label = Column(String(20), nullable=False)
    evaluation_date = Column(Date, nullable=False)

    student = relationship("Student", back_populates="outcomes")
    enrollment = relationship("Enrollment", back_populates="outcomes")
    intervention = relationship("Intervention", back_populates="outcomes")

