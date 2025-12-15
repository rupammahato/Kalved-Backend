from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Date,
    ForeignKey,
    DECIMAL,
)
from sqlalchemy.dialects.postgresql import JSONB, INET
from datetime import datetime
from app.core.database import Base


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    event_type = Column(String(100), nullable=False)  # appointment_booked, chat_opened, etc.
    event_data = Column(JSONB, nullable=True)
    session_id = Column(String(255), nullable=True)
    ip_address = Column(INET, nullable=True)
    user_agent = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class DoctorPerformanceMetrics(Base):
    __tablename__ = "doctor_performance_metrics"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    metric_date = Column(Date, nullable=False, index=True)

    total_appointments = Column(Integer, default=0)
    completed_appointments = Column(Integer, default=0)
    no_show_count = Column(Integer, default=0)
    cancellation_count = Column(Integer, default=0)

    average_rating = Column(DECIMAL(3, 2), nullable=True)
    total_reviews = Column(Integer, default=0)

    avg_response_time_minutes = Column(Integer, nullable=True)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
