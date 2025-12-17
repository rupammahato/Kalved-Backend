# app/models/review.py
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text,
    ForeignKey,
    Boolean,
)
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class DoctorReview(Base):
    __tablename__ = "doctor_reviews"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=False)

    # Ratings: 1–5
    overall_rating = Column(Integer, nullable=False)
    communication_rating = Column(Integer, nullable=True)
    expertise_rating = Column(Integer, nullable=True)
    time_spent_rating = Column(Integer, nullable=True)
    cleanliness_rating = Column(Integer, nullable=True)

    review_title = Column(String(200), nullable=True)
    review_text = Column(Text, nullable=True)

    # Authenticity & moderation
    is_verified = Column(Boolean, default=True)   # from a real appointment
    is_approved = Column(Boolean, default=True)  # hidden if false
    moderation_notes = Column(Text, nullable=True)
    flagged_for_review = Column(Boolean, default=False)

    helpful_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    doctor = relationship("Doctor")
    patient = relationship("Patient")
    appointment = relationship("Appointment")


class ReviewHelpfulVote(Base):
    __tablename__ = "review_helpful_votes"

    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey("doctor_reviews.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    is_helpful = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    review = relationship("DoctorReview")
    user = relationship("User")

    __table_args__ = (
        # One vote per user per review
        {"sqlite_autoincrement": True},
    )


class ClinicReview(Base):
    __tablename__ = "clinic_reviews"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    rating = Column(Integer, nullable=False)  # 1–5 overall

    ambiance_rating = Column(Integer, nullable=True)
    staff_rating = Column(Integer, nullable=True)
    hygiene_rating = Column(Integer, nullable=True)

    review_title = Column(String(200), nullable=True)
    review_text = Column(Text, nullable=True)

    is_verified = Column(Boolean, default=True)
    is_approved = Column(Boolean, default=True)
    moderation_notes = Column(Text, nullable=True)

    helpful_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    clinic = relationship("Clinic")
    user = relationship("User")
