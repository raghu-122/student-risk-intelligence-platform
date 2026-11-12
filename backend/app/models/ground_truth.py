from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base


class GroundTruth(Base):
    """
    Stores expected outcomes for validation.
    NEVER includes model input features.
    """
    __tablename__ = "ground_truth"

    gt_id = Column(String(60), primary_key=True)
    student_id = Column(String(20), ForeignKey("students.student_id"), nullable=True)
    risk_id = Column(String(60), ForeignKey("risk_assessments.risk_id"), nullable=True, unique=True)
    expected_risk_category = Column(String(20), nullable=True)
    expected_outcome_label = Column(String(20), nullable=True)
    expected_anomaly_detected = Column(Boolean, nullable=True)
    evaluation_reference = Column(String(200), nullable=True)
    notes = Column(String(500), nullable=True)

    student = relationship("Student", back_populates="ground_truths")
    risk_assessment = relationship("RiskAssessment", back_populates="ground_truth")
