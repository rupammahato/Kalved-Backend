"""Audit and admin activity log models."""
from sqlalchemy import Column, String, DateTime, Integer
from app.core.database import Base
from datetime import datetime


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    actor_id = Column(String, nullable=True)
    action = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class AdminActivityLog(Base):
    __tablename__ = "admin_activity_logs"

    id = Column(Integer, primary_key=True)
    admin_id = Column(String, nullable=False)
    activity = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
