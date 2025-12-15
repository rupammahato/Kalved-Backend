from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    notification_type = Column(String(100), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    
    related_entity_type = Column(String(100), nullable=True)
    related_entity_id = Column(Integer, nullable=True)
    
    is_email_sent = Column(Boolean, default=False)
    email_sent_at = Column(DateTime, nullable=True)
    is_sms_sent = Column(Boolean, default=False)
    sms_sent_at = Column(DateTime, nullable=True)
    is_push_sent = Column(Boolean, default=False)
    push_sent_at = Column(DateTime, nullable=True)
    is_in_app = Column(Boolean, default=True)
    
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    
    scheduled_for = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User")

class NotificationPreferences(Base):
    __tablename__ = "notification_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    appointment_reminders = Column(Boolean, default=True)
    appointment_reminder_hours = Column(Integer, default=24)
    
    prescription_notifications = Column(Boolean, default=True)
    review_request_notifications = Column(Boolean, default=True)
    message_notifications = Column(Boolean, default=True)
    
    email_enabled = Column(Boolean, default=True)
    sms_enabled = Column(Boolean, default=True)
    push_enabled = Column(Boolean, default=True)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
