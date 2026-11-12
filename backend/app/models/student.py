from sqlalchemy import Column, String, Date
from sqlalchemy.orm import relationship
from app.db.database import Base
from app.models.mixins import TimestampMixin


class Student(Base, TimestampMixin):
    __tablename__ = "students"

    student_id = Column(String(20), primary_key=True)        # e.g. STU-2026-000001
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    enrollment_date = Column(Date, nullable=False)
    academic_year = Column(String(10), nullable=False)
    department = Column(String(100), nullable=False)
    program = Column(String(200), nullable=False)
    current_status = Column(String(20), nullable=False, default="ACTIVE")

    enrollments = relationship("Enrollment", back_populates="student")
    support_cases = relationship("SupportCase", back_populates="student")
    interventions = relationship("Intervention", back_populates="student")
    risk_assessments = relationship("RiskAssessment", back_populates="student")
    outcomes = relationship("Outcome", back_populates="student")
    status_history = relationship("StudentStatusHistory", back_populates="student")
    ground_truths = relationship("GroundTruth", back_populates="student")

