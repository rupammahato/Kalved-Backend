from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    Text,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class ChatRoom(Base):
    __tablename__ = "chat_rooms"

    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id", ondelete="CASCADE"), nullable=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)

    room_type = Column(String(50), default="appointment")   # appointment, followup, support
    room_status = Column(String(50), default="active")       # active, closed, archived

    last_message_at = Column(DateTime, nullable=True)
    last_message_preview = Column(Text, nullable=True)
    unread_count_doctor = Column(Integer, default=0)
    unread_count_patient = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)

    doctor = relationship("Doctor")
    patient = relationship("Patient")
    appointment = relationship("Appointment")
    messages = relationship("ChatMessage", back_populates="chat_room", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_room_id = Column(Integer, ForeignKey("chat_rooms.id", ondelete="CASCADE"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    message_text = Column(Text, nullable=False)
    message_type = Column(String(50), default="text")  # text, image, file, system

    attachment_url = Column(Text, nullable=True)
    attachment_type = Column(String(50), nullable=True)  # image, pdf, etc.

    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    is_edited = Column(Boolean, default=False)
    edited_at = Column(DateTime, nullable=True)

    is_deleted = Column(Boolean, default=False)  # soft delete
    deleted_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    replied_to_message_id = Column(Integer, ForeignKey("chat_messages.id"), nullable=True)

    chat_room = relationship("ChatRoom", back_populates="messages")
    sender = relationship("User")
    replied_to_message = relationship("ChatMessage", remote_side=[id])
