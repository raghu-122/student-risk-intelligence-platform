from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class StudentStatusHistory(Base):
    __tablename__ = "student_status_history"

    history_id = Column(String(60), primary_key=True)
    student_id = Column(String(20), ForeignKey("students.student_id"), nullable=False)
    from_status = Column(String(20), nullable=True)
    to_status = Column(String(20), nullable=False)
    changed_at = Column(DateTime(timezone=True), server_default=func.now())
    reason = Column(Text, nullable=True)
    performed_by = Column(String(100), nullable=True)

    student = relationship("Student", back_populates="status_history")

