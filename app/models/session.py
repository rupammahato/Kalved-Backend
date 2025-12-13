"""User session model for tracking JWT access/refresh tokens."""
from datetime import datetime
import uuid
from sqlalchemy import Column, String, DateTime, Boolean, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Token identifiers and hashes
    token_jti = Column(String(128), nullable=False, index=True)
    refresh_jti = Column(String(128), nullable=False, index=True)
    refresh_token_hash = Column(String(128), nullable=False)

    # Session metadata
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # access token expiry for reference
    refresh_expires_at = Column(DateTime, nullable=True)

    # Revocation
    is_revoked = Column(Boolean, default=False, index=True)
    revoked_at = Column(DateTime, nullable=True)
    revoked_reason = Column(String(255), nullable=True)

    user = relationship("User", back_populates="sessions")
