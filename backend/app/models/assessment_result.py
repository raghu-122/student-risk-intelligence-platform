from sqlalchemy import Column, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
from app.models.mixins import TimestampMixin


class AssessmentResult(Base, TimestampMixin):
    __tablename__ = "assessment_results"

    result_id = Column(String(100), primary_key=True)       # RES-{assessment_id}-{enrollment_id}
    assessment_id = Column(String(15), ForeignKey("assessments.assessment_id"), nullable=False)
    enrollment_id = Column(String(80), ForeignKey("enrollments.enrollment_id"), nullable=False)
    marks_obtained = Column(Float, nullable=True)           # NULL = not yet submitted
    percentage = Column(Float, nullable=True)
    submission_status = Column(String(20), nullable=False)
    evaluated_at = Column(DateTime(timezone=True), nullable=True)

    assessment = relationship("Assessment", back_populates="results")
    enrollment = relationship("Enrollment", back_populates="assessment_results")

