from sqlalchemy import Column, String, Date, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class AttendanceEvent(Base):
    __tablename__ = "attendance_events"

    attendance_id = Column(String(100), primary_key=True)   # ATT-{enrollment_id}-{YYYYMMDD}
    enrollment_id = Column(String(80), ForeignKey("enrollments.enrollment_id"), nullable=False)
    attendance_date = Column(Date, nullable=False)
    attendance_status = Column(String(20), nullable=False)
    session_number = Column(Integer, nullable=False)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
    issue_type = Column(String(50), nullable=True)

    enrollment = relationship("Enrollment", back_populates="attendance_events")

