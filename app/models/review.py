from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, DECIMAL
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class DoctorReview(Base):
    __tablename__ = "doctor_reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=False)
    
    overall_rating = Column(Integer, nullable=False)
    communication_rating = Column(Integer, nullable=True)
    expertise_rating = Column(Integer, nullable=True)
    time_spent_rating = Column(Integer, nullable=True)
    cleanliness_rating = Column(Integer, nullable=True)
    
    review_title = Column(String(200), nullable=True)
    review_text = Column(Text, nullable=True)
    
    is_verified = Column(Boolean, default=True)
    is_approved = Column(Boolean, default=True)
    moderation_notes = Column(Text, nullable=True)
    flagged_for_review = Column(Boolean, default=False)
    
    helpful_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    doctor = relationship("Doctor")
    patient = relationship("Patient")
    appointment = relationship("Appointment")
