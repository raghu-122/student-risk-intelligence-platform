from sqlalchemy import Column, String, Text, Boolean, DateTime
from sqlalchemy.sql import func
from app.db.database import Base


class DataQualityIssue(Base):
    """Records detected anomalies and data quality violations."""
    __tablename__ = "data_quality_issues"

    issue_id = Column(String(60), primary_key=True)
    issue_type = Column(String(50), nullable=False)
    affected_entity = Column(String(50), nullable=False)
    affected_record_id = Column(String(100), nullable=False)
    expected_behavior = Column(Text, nullable=True)
    observed_behavior = Column(Text, nullable=True)
    ground_truth_label = Column(String(50), nullable=True)
    detection_status = Column(String(20), nullable=False, default="DETECTED")
    explanation = Column(Text, nullable=True)
    severity = Column(String(20), nullable=False, default="HIGH")
    is_injected_anomaly = Column(Boolean, default=False)
    detected_at = Column(DateTime(timezone=True), server_default=func.now())

