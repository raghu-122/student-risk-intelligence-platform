from sqlalchemy import Column, String, Text, DateTime, JSON
from sqlalchemy.sql import func
from app.db.database import Base


class AuditLog(Base):
    """Immutable audit trail for all important business events."""
    __tablename__ = "audit_logs"

    log_id = Column(String(80), primary_key=True)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(100), nullable=False)
    action = Column(String(50), nullable=False)
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    performed_by = Column(String(100), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

