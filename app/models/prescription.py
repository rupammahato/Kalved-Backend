from sqlalchemy import Column, Integer, String, DateTime, Date, Boolean, Text, ForeignKey, ARRAY
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Medicine(Base):
    __tablename__ = "medicines"
    
    id = Column(Integer, primary_key=True, index=True)
    medicine_name = Column(String(255), unique=True, nullable=False, index=True)
    generic_name = Column(String(255), nullable=True)
    medicine_type = Column(String(50), nullable=True)
    category = Column(String(100), nullable=True, index=True)
    available_strengths = Column(ARRAY(String), nullable=True)
    unit_type = Column(String(50), nullable=True)
    manufacturer = Column(String(200), nullable=True)
    hsn_code = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    side_effects = Column(Text, nullable=True)
    contraindications = Column(Text, nullable=True)
    image_url = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Pharmacy(Base):
    __tablename__ = "pharmacies"
    
    id = Column(Integer, primary_key=True, index=True)
    pharmacy_name = Column(String(200), nullable=False)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True, index=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    latitude = Column(String(20), nullable=True)
    longitude = Column(String(20), nullable=True)
    opening_time = Column(String(10), nullable=True)
    closing_time = Column(String(10), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Prescription(Base):
    __tablename__ = "prescriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=True)
    
    prescription_number = Column(String(50), unique=True, nullable=False)
    prescription_date = Column(Date, nullable=False, index=True)
    valid_until = Column(Date, nullable=True)
    
    diagnosis = Column(Text, nullable=False)
    clinical_notes = Column(Text, nullable=True)
    precautions = Column(Text, nullable=True)
    overall_instruction = Column(Text, nullable=True)
    
    doctor_signature_url = Column(Text, nullable=True)
    is_signed = Column(Boolean, default=False)
    signed_at = Column(DateTime, nullable=True)
    
    pharmacy_id = Column(Integer, ForeignKey("pharmacies.id"), nullable=True)
    dispensed_at = Column(DateTime, nullable=True)
    dispensed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    status = Column(String(50), default="issued", index=True)
    
    is_acknowledged_by_patient = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    doctor = relationship("Doctor")
    patient = relationship("Patient")
    appointment = relationship("Appointment", foreign_keys=[appointment_id])
    items = relationship("PrescriptionItem", back_populates="prescription")

class PrescriptionItem(Base):
    __tablename__ = "prescription_items"
    
    id = Column(Integer, primary_key=True, index=True)
    prescription_id = Column(Integer, ForeignKey("prescriptions.id", ondelete="CASCADE"), nullable=False)
    medicine_id = Column(Integer, ForeignKey("medicines.id"), nullable=False)
    
    medicine_name = Column(String(200), nullable=False)
    dosage_strength = Column(String(100), nullable=True)
    dosage_unit = Column(String(50), nullable=True)
    dosage_quantity = Column(String(20), nullable=True)
    dosage_frequency = Column(String(100), nullable=True)
    dosage_duration_days = Column(Integer, nullable=True)
    
    special_instructions = Column(Text, nullable=True)
    anupan = Column(Text, nullable=True)
    
    quantity_prescribed = Column(Integer, nullable=False)
    quantity_dispensed = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    prescription = relationship("Prescription", back_populates="items")
    medicine = relationship("Medicine")
