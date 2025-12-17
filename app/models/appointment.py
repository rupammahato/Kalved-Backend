from sqlalchemy import Column, Integer, String, DateTime, Date, Time, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class ClinicAvailabilityTemplate(Base):
    __tablename__ = "clinic_availability_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    day_of_week = Column(String(20), nullable=False)
    opening_time = Column(Time, nullable=False)
    closing_time = Column(Time, nullable=False)
    break_start = Column(Time, nullable=True)
    break_end = Column(Time, nullable=True)
    slot_duration_minutes = Column(Integer, default=30)
    max_patients_per_slot = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    clinic = relationship("Clinic")
    doctor = relationship("Doctor")

class AppointmentSlot(Base):
    __tablename__ = "appointment_slots"
    
    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    slot_start = Column(DateTime, nullable=False)
    slot_end = Column(DateTime, nullable=False)
    slot_date = Column(Date, nullable=False, index=True)
    slot_status = Column(String(50), default="available", index=True)
    consultation_type = Column(String(50), default="in-person")
    max_patients = Column(Integer, default=1)
    current_patients = Column(Integer, default=0)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    doctor = relationship("Doctor")
    clinic = relationship("Clinic")
    appointments = relationship("Appointment", back_populates="slot")

class Appointment(Base):
    __tablename__ = "appointments"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    clinic_id = Column(Integer, ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False)
    appointment_slot_id = Column(Integer, ForeignKey("appointment_slots.id", ondelete="RESTRICT"), nullable=False)
    
    appointment_date = Column(Date, nullable=False, index=True)
    appointment_time = Column(Time, nullable=False)
    appointment_start = Column(DateTime, nullable=False)
    appointment_end = Column(DateTime, nullable=False)
    
    appointment_type = Column(String(100), nullable=True)
    reason_for_visit = Column(Text, nullable=True)
    appointment_notes = Column(Text, nullable=True)
    
    status = Column(String(50), default="scheduled", index=True)
    is_confirmed = Column(Boolean, default=False)
    confirmed_at = Column(DateTime, nullable=True)
    
    cancellation_reason = Column(Text, nullable=True)
    cancelled_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    
    doctor_notes = Column(Text, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    patient_checked_in_at = Column(DateTime, nullable=True)
    patient_checked_out_at = Column(DateTime, nullable=True)
    
    prescription_id = Column(Integer, ForeignKey("prescriptions.id"), nullable=True)
    
    reminder_sent_at = Column(DateTime, nullable=True)
    second_reminder_sent_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    patient = relationship("Patient")
    doctor = relationship("Doctor")
    clinic = relationship("Clinic")
    slot = relationship("AppointmentSlot", back_populates="appointments")
    prescription = relationship("Prescription", foreign_keys=[prescription_id], uselist=False)
    chat_room = relationship("ChatRoom", uselist=False)

class AppointmentCancellation(Base):
    __tablename__ = "appointment_cancellations"
    
    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=False)
    cancelled_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    cancellation_reason = Column(Text, nullable=True)
    cancellation_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
