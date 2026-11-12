from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class SupportCaseEvent(Base):
    __tablename__ = "support_case_events"

    event_id = Column(String(60), primary_key=True)
    case_id = Column(String(20), ForeignKey("support_cases.case_id"), nullable=False)
    event_type = Column(String(50), nullable=False)
    from_status = Column(String(20), nullable=True)
    to_status = Column(String(20), nullable=True)
    performed_by = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    event_timestamp = Column(DateTime(timezone=True), server_default=func.now())

    case = relationship("SupportCase", back_populates="events")

