"""Patient profile model."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, Date, Text, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(20), nullable=True)
    blood_group = Column(String(5), nullable=True)
    medical_history = Column(Text, nullable=True)
    allergies = Column(Text, nullable=True)
    medications = Column(Text, nullable=True)
    emergency_contact_name = Column(String(100), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)

    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    pincode = Column(String(10), nullable=True)
    country = Column(String(100), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="patient")
