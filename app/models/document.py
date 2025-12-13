"""Verification document model."""
from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship, foreign
from app.core.database import Base


class VerificationDocument(Base):
    __tablename__ = "verification_documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path = Column(String, nullable=False)
    doc_type = Column(String, nullable=True)
    status = Column(String, nullable=True)

    user = relationship("User", overlaps="documents")
    doctor = relationship(
        "Doctor",
        back_populates="documents",
        primaryjoin="foreign(VerificationDocument.user_id)==Doctor.user_id",
        overlaps="user",
    )
