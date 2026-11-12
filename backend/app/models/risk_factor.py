from sqlalchemy import Column, String, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base


class RiskFactor(Base):
    __tablename__ = "risk_factors"

    factor_id = Column(String(80), primary_key=True)
    risk_id = Column(String(60), ForeignKey("risk_assessments.risk_id"), nullable=False)
    factor_name = Column(String(50), nullable=False)
    raw_value = Column(Float, nullable=True)
    normalized_score = Column(Float, nullable=True)
    weight = Column(Float, nullable=False)
    contribution = Column(Float, nullable=True)
    explanation = Column(Text, nullable=True)

    risk_assessment = relationship("RiskAssessment", back_populates="risk_factors")

