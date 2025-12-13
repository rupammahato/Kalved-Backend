"""Admin model."""
from sqlalchemy import Column, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    super_admin = Column(Boolean, default=False)

    user = relationship("User", back_populates="admin")
