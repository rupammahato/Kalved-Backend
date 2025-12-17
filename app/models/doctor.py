from sqlalchemy import Column, Integer, String, Date, Boolean, Text, ARRAY, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship, foreign
from datetime import datetime
from app.core.database import Base


class Doctor(Base):
    __tablename__ = "doctors"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    # License details
    brc_number = Column(String(50), unique=True, index=True, nullable=True)
    brc_issued_date = Column(Date, nullable=True)
    brc_valid_until = Column(Date, nullable=True)
    brc_verification_status = Column(String(50), default="pending", index=True)
    brc_verification_notes = Column(Text, nullable=True)
    
    years_of_experience = Column(Integer, nullable=True)
    specializations = Column(ARRAY(String), nullable=True)
    
    # Admin approval
    admin_approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    admin_approved_at = Column(DateTime, nullable=True)
    admin_approval_notes = Column(Text, nullable=True)
    
    # Consultation fee
    default_consultation_fee = Column(Integer, nullable=True)

    # Ratings
    average_rating = Column(Float, nullable=True)
    total_reviews = Column(Integer, default=0)
    
    # Documents
    clinic_registration_certificate = Column(Text, nullable=True)
    gst_number = Column(String(50), nullable=True)
    
    languages = Column(ARRAY(String), nullable=True)
    
    # Bank details (Phase 2)
    bank_name = Column(String(100), nullable=True)
    bank_account_number = Column(String(50), nullable=True)
    ifsc_code = Column(String(20), nullable=True)
    account_holder_name = Column(String(100), nullable=True)
    
    # Verification
    identity_verified = Column(Boolean, default=False)
    identity_proof_url = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="doctor", foreign_keys=[user_id])
    admin_approver = relationship("User", foreign_keys=[admin_approved_by])
    qualifications = relationship("DoctorQualification", back_populates="doctor", cascade="all, delete-orphan")
    clinics = relationship("Clinic", back_populates="doctor", cascade="all, delete-orphan")
    documents = relationship(
        "VerificationDocument",
        back_populates="doctor",
        primaryjoin="Doctor.user_id==foreign(VerificationDocument.user_id)",
        overlaps="user",
    )

class DoctorQualification(Base):
    __tablename__ = "doctor_qualifications"
    
    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    degree_name = Column(String(100), nullable=True)
    institution = Column(String(200), nullable=True)
    country = Column(String(100), nullable=True)
    year_of_graduation = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    doctor = relationship("Doctor", back_populates="qualifications")

