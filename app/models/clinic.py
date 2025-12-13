"""Clinic and timing models."""
from datetime import datetime
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Time, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class Clinic(Base):
    __tablename__ = "clinics"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    pincode = Column(String(10), nullable=True)
    country = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    latitude = Column(String(32), nullable=True)
    longitude = Column(String(32), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    doctor = relationship("Doctor", back_populates="clinics")
    timings = relationship("ClinicTiming", back_populates="clinic", cascade="all, delete-orphan")


class ClinicTiming(Base):
    __tablename__ = "clinic_timings"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False, index=True)
    day = Column(String(10), nullable=False)  # e.g., MON, TUE
    open_time = Column(Time, nullable=True)
    close_time = Column(Time, nullable=True)
    notes = Column(Text, nullable=True)

    clinic = relationship("Clinic", back_populates="timings")
