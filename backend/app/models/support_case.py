from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
from app.models.mixins import TimestampMixin


class SupportCase(Base, TimestampMixin):
    __tablename__ = "support_cases"

    case_id = Column(String(20), primary_key=True)          # CASE-2026-000001
    student_id = Column(String(20), ForeignKey("students.student_id"), nullable=False)
    enrollment_id = Column(String(80), ForeignKey("enrollments.enrollment_id"), nullable=True)
    case_type = Column(String(30), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(String(20), nullable=False, default="MEDIUM")
    assigned_staff_id = Column(String(20), ForeignKey("staff.staff_id"), nullable=True)
    case_status = Column(String(20), nullable=False, default="OPEN")
    opened_at = Column(DateTime(timezone=True), server_default=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    student = relationship("Student", back_populates="support_cases")
    enrollment = relationship("Enrollment", back_populates="support_cases")
    assigned_staff = relationship("Staff", back_populates="support_cases")
    events = relationship("SupportCaseEvent", back_populates="case")
    interventions = relationship("Intervention", back_populates="case")

