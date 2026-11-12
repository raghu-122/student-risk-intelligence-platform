from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import relationship
from app.db.database import Base
from app.models.mixins import TimestampMixin


class Staff(Base, TimestampMixin):
    __tablename__ = "staff"

    staff_id = Column(String(20), primary_key=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    role = Column(String(50), nullable=False)
    department = Column(String(100))
    is_active = Column(Boolean, default=True)

    user = relationship("User", back_populates="staff", uselist=False)
    courses = relationship("Course", back_populates="instructor")
    support_cases = relationship("SupportCase", back_populates="assigned_staff")
    interventions = relationship("Intervention", back_populates="assigned_staff")

