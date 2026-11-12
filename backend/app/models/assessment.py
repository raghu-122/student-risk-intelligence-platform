from sqlalchemy import Column, String, Float, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base
from app.models.mixins import TimestampMixin


class Assessment(Base, TimestampMixin):
    __tablename__ = "assessments"

    assessment_id = Column(String(15), primary_key=True)    # ASM-000001
    course_id = Column(String(15), ForeignKey("courses.course_id"), nullable=False)
    assessment_name = Column(String(200), nullable=False)
    assessment_type = Column(String(30), nullable=False)
    maximum_marks = Column(Float, nullable=False)
    weightage = Column(Float, nullable=False)               # fraction summing to 1 within course
    assessment_date = Column(Date, nullable=False)

    course = relationship("Course", back_populates="assessments")
    results = relationship("AssessmentResult", back_populates="assessment")

