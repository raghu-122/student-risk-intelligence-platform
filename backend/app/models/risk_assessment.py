from sqlalchemy import Column, String, Float, Date, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    risk_id = Column(String(60), primary_key=True)
    student_id = Column(String(20), ForeignKey("students.student_id"), nullable=False)
    enrollment_id = Column(String(80), ForeignKey("enrollments.enrollment_id"), nullable=True)
    assessment_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    cutoff_date = Column(Date, nullable=False)
    risk_score = Column(Float, nullable=True)
    risk_category = Column(String(20), nullable=False)
    factor_scores = Column(JSON, nullable=True)
    factor_weights = Column(JSON, nullable=True)
    reasons = Column(JSON, nullable=True)
    data_completeness = Column(Float, nullable=True)
    model_version = Column(String(20), nullable=False, default="v1.0")
    is_anomaly = Column(Boolean, default=False)

    student = relationship("Student", back_populates="risk_assessments")
    enrollment = relationship("Enrollment", back_populates="risk_assessments")
    risk_factors = relationship("RiskFactor", back_populates="risk_assessment")
    interventions = relationship("Intervention", back_populates="risk_assessment")
    ground_truth = relationship("GroundTruth", back_populates="risk_assessment", uselist=False)

