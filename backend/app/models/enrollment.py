from sqlalchemy import Column, String, Date, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.database import Base
from app.models.mixins import TimestampMixin


class Enrollment(Base, TimestampMixin):
    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("student_id", "course_id", name="uq_enrollment_student_course"),
    )

    enrollment_id = Column(String(80), primary_key=True)    # ENR-{student_id}-{course_id}
    student_id = Column(String(20), ForeignKey("students.student_id"), nullable=False)
    course_id = Column(String(15), ForeignKey("courses.course_id"), nullable=False)
    enrollment_date = Column(Date, nullable=False)
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)
    enrollment_status = Column(String(20), nullable=False, default="ACTIVE")
    final_grade = Column(Float, nullable=True)

    student = relationship("Student", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")
    attendance_events = relationship("AttendanceEvent", back_populates="enrollment")
    assessment_results = relationship("AssessmentResult", back_populates="enrollment")
    lms_activities = relationship("LMSActivity", back_populates="enrollment")
    support_cases = relationship("SupportCase", back_populates="enrollment")
    interventions = relationship("Intervention", back_populates="enrollment")
    risk_assessments = relationship("RiskAssessment", back_populates="enrollment")
    outcomes = relationship("Outcome", back_populates="enrollment")
