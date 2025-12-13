from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Text, ARRAY, Enum
from sqlalchemy.orm import relationship, validates
from datetime import datetime
from app.core.database import Base
import enum


class UserTypeEnum(str, enum.Enum):
    DOCTOR = "doctor"
    PATIENT = "patient"
    ADMIN = "admin"


class UserStatusEnum(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ACTIVE = "active"
    SUSPENDED = "suspended"


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(20), unique=True, index=True, nullable=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    password_hash = Column(String(255), nullable=True)
    
    # OAuth
    google_id = Column(String(255), unique=True, index=True, nullable=True)
    oauth_provider = Column(String(50), nullable=True)
    
    # Profile
    profile_picture_url = Column(Text, nullable=True)
    bio = Column(Text, nullable=True)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    pincode = Column(String(10), nullable=True)
    country = Column(String(100), nullable=True)
    
    # Email verification
    email_verified = Column(Boolean, default=False)
    email_verified_at = Column(DateTime, nullable=True)
    otp_code = Column(String(6), nullable=True)
    otp_secret = Column(String(64), nullable=True)
    otp_sent_at = Column(DateTime, nullable=True)
    otp_attempts = Column(Integer, default=0)
    otp_expires_at = Column(DateTime, nullable=True)
    
    # Account status
    user_type = Column(String(50), index=True, nullable=False)
    status = Column(String(50), default="pending", index=True)
    status_reason = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # Soft delete
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)
    
    # Relationships
    doctor = relationship(
        "Doctor",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        foreign_keys="Doctor.user_id",
    )
    patient = relationship("Patient", back_populates="user", uselist=False, cascade="all, delete-orphan")
    admin = relationship("Admin", back_populates="user", uselist=False, cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User {self.email}>"

    @validates("phone")
    def normalize_phone(self, key, value):
        return value or None
