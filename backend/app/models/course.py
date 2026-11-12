from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base
from app.models.mixins import TimestampMixin


class Course(Base, TimestampMixin):
    __tablename__ = "courses"

    course_id = Column(String(15), primary_key=True)        # e.g. CRS-000001
    course_name = Column(String(200), nullable=False)
    course_code = Column(String(20), unique=True, nullable=False)
    department = Column(String(100), nullable=False)
    credits = Column(Integer, nullable=False)
    semester = Column(String(20), nullable=False)
    instructor_id = Column(String(20), ForeignKey("staff.staff_id"), nullable=True)

    instructor = relationship("Staff", back_populates="courses")
    enrollments = relationship("Enrollment", back_populates="course")
    assessments = relationship("Assessment", back_populates="course")

