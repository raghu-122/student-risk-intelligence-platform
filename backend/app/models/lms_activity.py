from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class LMSActivity(Base):
    __tablename__ = "lms_activities"

    activity_id = Column(String(20), primary_key=True)      # LMS-2026-000001
    enrollment_id = Column(String(80), ForeignKey("enrollments.enrollment_id"), nullable=False)
    activity_type = Column(String(30), nullable=False)
    activity_timestamp = Column(DateTime(timezone=True), nullable=False)
    duration_minutes = Column(Integer, nullable=True)
    resource_id = Column(String(50), nullable=True)
    activity_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    enrollment = relationship("Enrollment", back_populates="lms_activities")

