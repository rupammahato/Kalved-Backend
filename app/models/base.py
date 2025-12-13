"""Base SQLAlchemy model utilities."""
from sqlalchemy import Column, DateTime, func, Integer
from app.core.database import Base


class TimestampMixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class IDMixin:
    id = Column(Integer, primary_key=True, index=True)
